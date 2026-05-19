"""
Steam Community Market data collector
Handles scraping and API calls to gather CS2 market data
"""

import requests
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class SteamMarketCollector:
    """Collects price data from Steam Community Market"""
    
    BASE_URL = "https://steamcommunity.com/market"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Rate limiting
    REQUEST_DELAY = 1.0  # seconds between requests
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2.0
    
    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize the Steam Market Collector

        Args:
            rate_limit_delay: Seconds to wait between requests (default: 1.0)
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.last_request_time = 0
        self.hash_name_cache = {}  # Maps item_name -> market_hash_name
    
    def _rate_limit(self):
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Optional[Dict] = None, timeout: int = 10) -> Optional[Dict]:
        """
        Make HTTP request with retry logic
        
        Args:
            url: URL to request
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response JSON or None if failed
        """
        self._rate_limit()
        
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                response = self.session.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                
                # Avoid parsing empty responses
                if response.text:
                    return response.json()
                return None
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.RETRY_ATTEMPTS}): {e}")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    time.sleep(self.RETRY_DELAY)
                else:
                    logger.error(f"All retry attempts failed for {url}")
                    return None

    def resolve_hash_name(self, item_name: str) -> Optional[str]:
        """
        Resolve item name to Steam market hash name.
        Uses Steam's market search endpoint to find the exact hash.
        Results are cached to avoid repeated lookups.
        """
        # Check cache first
        if item_name in self.hash_name_cache:
            return self.hash_name_cache[item_name]

        # Query Steam market search endpoint
        url = "https://steamcommunity.com/market/search/render/"
        params = {
            'query': item_name,
            'start': 0,
            'count': 10,
            'search_descriptions': 0,
            'sort_column': 'name',
            'sort_dir': 'asc'
        }

        data = self._make_request(url, params)
        if not data or 'results' not in data or not data['results']:
            logger.warning(f"No market hash found for: {item_name}")
            return None

        # Extract hash name from first result
        first_result = data['results'][0]
        hash_name = first_result.get('hash_name')

        if hash_name:
            # Cache it
            self.hash_name_cache[item_name] = hash_name
            logger.debug(f"Resolved {item_name} -> {hash_name}")
            return hash_name

        logger.warning(f"Could not extract hash_name from result for: {item_name}")
        return None

    def get_item_price_history(self, item_name_or_hash: str) -> Optional[Tuple[float, int, datetime]]:
        """
        Get current price and volume for an item.
        Accepts either item name or market hash name.
        """
        # If it doesn't look like a hash name, resolve it first
        if '%' not in item_name_or_hash:
            hash_name = self.resolve_hash_name(item_name_or_hash)
            if not hash_name:
                return None
        else:
            hash_name = item_name_or_hash

        # Query price history endpoint
        url = "https://steamcommunity.com/market/pricehistory/"
        params = {
            'country': 'US',
            'currency': 1,  # USD
            'appid': 730,  # CS2
            'market_hash_name': hash_name
        }

        data = self._make_request(url, params)
        if not data or 'prices' not in data or not data['prices']:
            logger.warning(f"No price data for: {hash_name}")
            return None

        # Get most recent price point (last in list)
        prices = data['prices']
        last_price_point = prices[-1]  # [timestamp_str, price_str, volume_str]

        try:
            price = float(last_price_point[1])
            volume = int(last_price_point[2])
            return (price, volume, datetime.now())
        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing price data: {e}")
            return None
    
    def get_market_listings(self, start: int = 0, count: int = 100) -> Optional[Dict]:
        """
        Get market listings
        
        Args:
            start: Starting index
            count: Number of items to fetch
            
        Returns:
            Market listings data or None if failed
        """
        url = f"{self.BASE_URL}/search/render/"
        params = {
            'appid': 730,
            'search_descriptions': 0,
            'sort_column': 'price',
            'sort_dir': 'asc',
            'start': start,
            'count': count,
            'norender': 1
        }
        
        return self._make_request(url, params)
    
    def get_item_name_id(self, item_name: str) -> Optional[int]:
        """
        Get the nameid for an item (used for historical data)
        
        Args:
            item_name: Item name to search for
            
        Returns:
            Item nameid or None if not found
        """
        try:
            data = self.get_market_listings(count=1)
            if data and 'results' in data:
                for result in data['results']:
                    if result.get('hash_name', '').lower() == item_name.lower():
                        return result.get('name_id')
            return None
        except Exception as e:
            logger.error(f"Error getting nameid for {item_name}: {e}")
            return None
    
    def collect_batch_items(self, item_names: List[str]) -> Dict[str, Optional[Tuple[float, int, datetime]]]:
        """
        Collect price data for multiple items
        
        Args:
            item_names: List of item market hash names
            
        Returns:
            Dictionary mapping item names to (price, volume, timestamp) tuples
        """
        results = {}
        successful_items = 0
        failed_items = 0
        
        for item_name in item_names:
            try:
                result = self.get_item_price_history(item_name)
                if result:
                    results[item_name] = result
                    successful_items += 1
                    logger.info(f"Successfully collected price for: {item_name}")
                else:
                    results[item_name] = None
                    failed_items += 1
                    logger.warning(f"Failed to collect price for: {item_name}")
            except Exception as e:
                results[item_name] = None
                failed_items += 1
                logger.error(f"Error collecting {item_name}: {e}")
        
        logger.info(f"Batch collection completed: {successful_items} successful, {failed_items} failed out of {len(item_names)}")
        return results
    
    def get_price_trend(self, item_name: str) -> Optional[Dict]:
        """
        Get price trend data (low/high) for an item
        
        Args:
            item_name: Item market hash name
            
        Returns:
            Dictionary with low, high, volume trend or None if failed
        """
        url = f"{self.BASE_URL}/priceoverview/"
        params = {
            'appid': 730,
            'market_hash_name': item_name,
            'currency': 1
        }
        
        try:
            data = self._make_request(url, params)
            if data and data.get('success'):
                return {
                    'lowest_price': float(data.get('lowest_price', '0').replace('$', '').replace(',', '')) or None,
                    'highest_price': float(data.get('median_price', '0').replace('$', '').replace(',', '')) or None,
                    'volume': data.get('volume'),
                    'timestamp': datetime.utcnow()
                }
            return None
        except Exception as e:
            logger.error(f"Error getting price trend for {item_name}: {e}")
            return None


class MockSteamMarketCollector(SteamMarketCollector):
    """Mock collector for testing without hitting Steam API"""
    
    def get_item_price_history(self, hash_name: str) -> Optional[Tuple[float, int, datetime]]:
        """Return mock data for testing"""
        import random
        price = random.uniform(10, 500)
        volume = random.randint(100, 10000)
        return (price, volume, datetime.utcnow())
    
    def get_market_listings(self, start: int = 0, count: int = 100) -> Optional[Dict]:
        """Return mock listings"""
        return {
            'success': True,
            'results_html': '<div>mock</div>',
            'results': []
        }
