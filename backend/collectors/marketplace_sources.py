"""
Marketplace source collectors for external CS2 market data.

These collectors normalize public marketplace responses into a common
snapshot shape so the rest of the pipeline can store them in PriceHistory.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

CS2_CONDITIONS = [
    "Factory New",
    "Minimal Wear",
    "Field-Tested",
    "Well-Worn",
    "Battle-Scarred",
]


def _chunked(values: List[str], size: int) -> List[List[str]]:
    return [values[i:i + size] for i in range(0, len(values), size)]


def build_marketplace_name_candidates(item_name: str, item_type: Optional[str] = None) -> List[str]:
    """
    Build a list of likely marketplace titles for a catalog item.

    The goal is not to invent data, but to try the common naming shapes used
    by Steam, Skinport, and DMarket so we can match more of the catalog.
    """
    candidates: List[str] = []

    def add(candidate: str) -> None:
        candidate = candidate.strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add(item_name)

    is_skin = (item_type or "").lower() == "skin"
    has_pipe = " | " in item_name

    if is_skin and not has_pipe:
        parts = item_name.split(" ", 1)
        if len(parts) == 2:
            weapon, skin = parts
            pipe_name = f"{weapon} | {skin}"
            add(pipe_name)
            for condition in CS2_CONDITIONS:
                add(f"{pipe_name} ({condition})")
                add(f"{item_name} ({condition})")
    elif is_skin and has_pipe:
        for condition in CS2_CONDITIONS:
            add(f"{item_name} ({condition})")
        weapon, skin = item_name.split(" | ", 1)
        add(f"{weapon} {skin}")

    return candidates


class SkinportMarketCollector:
    """Collects CS2 price snapshots from Skinport public market endpoints."""

    BASE_URL = "https://api.skinport.com/v1"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def __init__(self, currency: str = "USD", app_id: int = 730, chunk_size: int = 10):
        self.currency = currency
        self.app_id = app_id
        self.chunk_size = chunk_size
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def _decode_json(self, response: requests.Response):
        try:
            return response.json()
        except ValueError:
            # Some environments do not have brotli support in requests. Fall back
            # to manual decompression if the response is Brotli encoded.
            if response.headers.get("Content-Encoding") == "br":
                try:
                    import brotli  # type: ignore

                    return json.loads(brotli.decompress(response.content).decode("utf-8"))
                except Exception as exc:
                    logger.error("Unable to decode Brotli Skinport response: %s", exc)
            raise

    def _request_history(self, names: List[str]) -> List[Dict]:
        params = {
            "app_id": self.app_id,
            "currency": self.currency,
            "market_hash_name": ",".join(names),
        }
        response = self.session.get(f"{self.BASE_URL}/sales/history", params=params, timeout=20)
        response.raise_for_status()
        data = self._decode_json(response)
        return data if isinstance(data, list) else []

    @staticmethod
    def _select_price_window(entry: Dict) -> Tuple[Optional[float], Optional[int]]:
        for window_key in ("last_24_hours", "last_7_days", "last_30_days", "last_90_days"):
            window = entry.get(window_key) or {}
            price = window.get("median") or window.get("avg") or window.get("min") or window.get("max")
            volume = window.get("volume")
            if price is not None:
                try:
                    return float(price), int(volume) if volume is not None else None
                except (TypeError, ValueError):
                    continue
        return None, None

    def collect_batch_items(self, item_names: List[str]) -> Dict[str, Optional[Tuple[float, int, datetime]]]:
        results: Dict[str, Optional[Tuple[float, int, datetime]]] = {name: None for name in item_names}
        if not item_names:
            return results

        for chunk in _chunked(item_names, self.chunk_size):
            try:
                payload = self._request_history(chunk)
                by_name = {entry.get("market_hash_name"): entry for entry in payload if entry.get("market_hash_name")}

                for name in chunk:
                    entry = by_name.get(name)
                    if not entry:
                        continue
                    price, volume = self._select_price_window(entry)
                    if price is None:
                        continue
                    results[name] = (price, volume or 0, datetime.utcnow())
            except Exception as exc:
                logger.warning("Skinport batch collection failed for %s: %s", chunk, exc)

        return results


class DMarketCollector:
    """Collects CS2 price snapshots from DMarket aggregated-prices endpoint."""

    BASE_URL = "https://api.dmarket.com"
    GAME_ID = "a8db"

    def __init__(self, currency: str = "USD"):
        self.currency = currency
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    @staticmethod
    def _parse_price(price_payload: Optional[Dict]) -> Optional[float]:
        if not price_payload:
            return None
        amount = price_payload.get("Amount")
        if amount is None:
            return None
        try:
            return float(amount)
        except (TypeError, ValueError):
            return None

    def _request_aggregated_prices(self, titles: List[str]) -> Dict:
        body = {
            "cursor": "",
            "limit": str(max(1, len(titles))),
            "filter": {
                "game": self.GAME_ID,
                "titles": titles,
            },
        }
        response = self.session.post(
            f"{self.BASE_URL}/marketplace-api/v1/aggregated-prices",
            json=body,
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def collect_batch_items(self, item_names: List[str]) -> Dict[str, Optional[Tuple[float, int, datetime]]]:
        results: Dict[str, Optional[Tuple[float, int, datetime]]] = {name: None for name in item_names}
        if not item_names:
            return results

        try:
            payload = self._request_aggregated_prices(item_names)
            aggregated = payload.get("aggregatedPrices", []) if isinstance(payload, dict) else []

            by_title = {entry.get("title"): entry for entry in aggregated if entry.get("title")}
            for name in item_names:
                entry = by_title.get(name)
                if not entry:
                    continue

                offer_price = self._parse_price(entry.get("offerBestPrice"))
                order_price = self._parse_price(entry.get("orderBestPrice"))

                if offer_price is not None and order_price is not None:
                    price = round((offer_price + order_price) / 2.0, 2)
                else:
                    price = offer_price if offer_price is not None else order_price

                if price is None:
                    continue

                offer_count = entry.get("offerCount")
                order_count = entry.get("orderCount")
                try:
                    volume = int(float(offer_count or 0) + float(order_count or 0))
                except (TypeError, ValueError):
                    volume = 0

                results[name] = (float(price), volume, datetime.utcnow())
        except Exception as exc:
            logger.warning("DMarket batch collection failed: %s", exc)

        return results
