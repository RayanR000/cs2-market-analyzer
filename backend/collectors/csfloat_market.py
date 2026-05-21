"""
CSFloat market collector.

Uses the public CSFloat listings endpoint to derive current market prices
for CS2 items. The endpoint returns active listings, so the collector uses
the lowest available listing price as the snapshot price and the listing
count as a coarse liquidity signal.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class CSFloatMarketCollector:
    """Collects CS2 price snapshots from CSFloat listings."""

    BASE_URL = "https://csfloat.com/api/v1"

    def __init__(self, chunk_size: int = 10):
        self.chunk_size = chunk_size
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Origin": "https://csfloat.com",
            "Referer": "https://csfloat.com/",
        })

    @staticmethod
    def _normalize_price(price_cents: Optional[int]) -> Optional[float]:
        if price_cents is None:
            return None
        try:
            return round(float(price_cents) / 100.0, 2)
        except (TypeError, ValueError):
            return None

    def _request_listings(self, market_hash_name: str, limit: int = 50) -> List[Dict]:
        params = {
            "market_hash_name": market_hash_name,
            "limit": limit,
            "sort_by": "lowest_price",
        }
        response = self.session.get(f"{self.BASE_URL}/listings", params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else []

    @staticmethod
    def _extract_listing_price(listing: Dict) -> Optional[float]:
        price = listing.get("price")
        if price is None:
            item = listing.get("item") or {}
            price = item.get("scm", {}).get("price")
        return CSFloatMarketCollector._normalize_price(price)

    def collect_batch_items(self, item_names: List[str]) -> Dict[str, Optional[Tuple[float, int, datetime]]]:
        results: Dict[str, Optional[Tuple[float, int, datetime]]] = {name: None for name in item_names}
        if not item_names:
            return results

        for item_name in item_names:
            try:
                listings = self._request_listings(item_name)
                if not listings:
                    continue

                prices = []
                for listing in listings:
                    normalized = self._extract_listing_price(listing)
                    if normalized is not None:
                        prices.append(normalized)

                if not prices:
                    continue

                results[item_name] = (
                    min(prices),
                    len(listings),
                    datetime.utcnow(),
                )
            except Exception as exc:
                logger.warning("CSFloat collection failed for %s: %s", item_name, exc)

        return results
