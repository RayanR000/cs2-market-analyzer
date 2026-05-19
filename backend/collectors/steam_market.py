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
    
    def get_item_price_history(self, hash_name: str) -> Optional[Tuple[float, int, datetime]]:
        """
        Get current price and volume for an item
        
        Args:
            hash_name: Market hash name of the item (e.g., 'AK-47 | Aquamarine Revenge (Field-Tested)')
            
        Returns:
            Tuple of (price, volume, timestamp) or None if failed
        """
        url = f"{self.BASE_URL}/priceoverview/"
        params = {
            'appid': 730,  # CS2 app ID
            'market_hash_name': hash_name,
            'currency': 1  # USD
        }
        
        try:
            data = self._make_request(url, params)
            if data and data.get('success'):
                price = data.get('lowest_price')
                volume = data.get('volume')
                
                # Parse price string (e.g., "$45.32" -> 45.32)
                if price:
                    price = float(price.replace('$', '').replace(',', ''))
                    volume = int(volume.replace(',', '')) if volume else None
                    
                    return (price, volume, datetime.utcnow())
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting price history for {hash_name}: {e}")
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
