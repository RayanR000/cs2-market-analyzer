"""
Skinport market collector.
Fetches item prices from Skinport's public API.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests

logger = logging.getLogger(__name__)

class SkinportMarketCollector:
    """Collects price data from Skinport's public API."""
    
    BASE_URL = "https://api.skinport.com/v1"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Encoding": "br, gzip, deflate",
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._cache = {}

    def _fetch_items(self) -> List[Dict]:
        """Fetch all items from Skinport's items endpoint."""
        try:
            url = f"{self.BASE_URL}/items?app_id=730"
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Skinport API fetch failed: {e}")
            return []

    def collect_batch_items(self, item_names: List[str]) -> Dict[str, Optional[Tuple[float, int, datetime]]]:
        """Fetch prices for a list of items."""
        results = {name: None for name in item_names}
        
        # Skinport returns a flat list; cache it once per batch run
        items = self._fetch_items()
        if not items:
            return results

        # Create a lookup map
        items_map = {item["market_hash_name"]: item for item in items}

        for item_name in item_names:
            # Skinport typically uses market_hash_name as the identifier
            # We try a few variations if an exact match isn't found
            target = items_map.get(item_name)
            if not target:
                # Try a case-insensitive search if direct match fails
                for hash_name, item_data in items_map.items():
                    if hash_name.lower() == item_name.lower():
                        target = item_data
                        break
            
            if target:
                # Skinport offers min_price (non-stattrak) and min_price_stattrak
                # We prioritize non-Stattrak if available, otherwise just use min_price
                price = target.get("min_price") or target.get("min_price_stattrak")
                if price:
                    results[item_name] = (float(price), 0, datetime.utcnow())
        
        return results
