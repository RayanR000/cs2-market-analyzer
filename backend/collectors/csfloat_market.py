"""
CSFloat market collector.
Fetches public listing data from CSFloat endpoints.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class CSFloatMarketCollector:
    """Collector for CSFloat public listing data."""

    BASE_URL = "https://csfloat.com/api/v1"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; CS2Analyzer/1.0)"}
        )
        self._listing_cache: Dict[str, Tuple[float, int, datetime]] = {}

    def _parse_price_cents(self, value) -> float:
        """Convert integer/float cents to dollars."""
        try:
            return float(value) / 100.0
        except (TypeError, ValueError):
            return 0.0

    def get_listings(self, market_hash_name: str) -> List[Dict]:
        """
        Fetch listings for a single market hash name.

        The tests monkeypatch `session.get`, so keep the request shape simple.
        """
        url = f"{self.BASE_URL}/listings"
        params = {"market_hash_name": market_hash_name}

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], list):
                return payload["data"]
            if "results" in payload and isinstance(payload["results"], list):
                return payload["results"]

        if isinstance(payload, list):
            return payload

        return []

    def get_item_price_history(
        self, market_hash_name: str
    ) -> Optional[Tuple[float, int, datetime]]:
        """Return a best-effort price snapshot for a market hash name."""
        listings = self.get_listings(market_hash_name)
        if not listings:
            return None

        prices = []
        for listing in listings:
            price = listing.get("price") if isinstance(listing, dict) else None
            if price is None:
                continue
            parsed_price = self._parse_price_cents(price)
            if parsed_price > 0:
                prices.append(parsed_price)

        if not prices:
            return None

        # Use the lowest observed listing price as the market snapshot.
        return (min(prices), len(prices), datetime.now(timezone.utc))

    def collect_batch_items(
        self, item_names: List[str]
    ) -> Dict[str, Optional[Tuple[float, int, datetime]]]:
        """Collect price data for multiple items."""
        results = {}

        for item_name in item_names:
            try:
                result = self.get_item_price_history(item_name)
                results[item_name] = result
            except Exception as e:
                logger.error("Error collecting %s: %s", item_name, e)
                results[item_name] = None

        return results
