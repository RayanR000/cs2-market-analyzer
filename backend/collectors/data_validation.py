"""
Data validation and cleaning pipeline
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates and cleans market data"""
    
    @staticmethod
    def validate_price(price: float, min_price: float = 0.01, max_price: float = 100000.0) -> bool:
        """
        Validate price is within reasonable range
        
        Args:
            price: Price to validate
            min_price: Minimum acceptable price
            max_price: Maximum acceptable price
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(price, (int, float)):
            return False
        if price < min_price or price > max_price:
            logger.warning(f"Price {price} outside acceptable range [{min_price}, {max_price}]")
            return False
        return True
    
    @staticmethod
    def validate_volume(volume: Optional[int]) -> bool:
        """
        Validate volume is reasonable
        
        Args:
            volume: Volume to validate
            
        Returns:
            True if valid or None, False if invalid
        """
        if volume is None:
            return True
        if not isinstance(volume, int):
            return False
        if volume < 0 or volume > 1000000:
            logger.warning(f"Volume {volume} outside acceptable range [0, 1000000]")
            return False
        return True
    
    @staticmethod
    def validate_item_name(name: str) -> bool:
        """
        Validate item name format
        
        Args:
            name: Item name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(name, str):
            return False
        if len(name) < 1 or len(name) > 500:
            return False
        return True
    
    @staticmethod
    def validate_item_type(item_type: str) -> bool:
        """
        Validate item type
        
        Args:
            item_type: Type to validate
            
        Returns:
            True if valid, False otherwise
        """
        valid_types = {'skin', 'case', 'sticker', 'agent', 'glove', 'graffiti', 'patch', 'other'}
        return item_type.lower() in valid_types
    
    @staticmethod
    def parse_item_name(market_hash_name: str) -> Tuple[str, Optional[str]]:
        """
        Parse market hash name into item name and rarity/condition
        
        Example: 'AK-47 | Aquamarine Revenge (Field-Tested)' 
        -> ('AK-47 | Aquamarine Revenge', 'Field-Tested')
        
        Args:
            market_hash_name: Full market hash name
            
        Returns:
            Tuple of (item_name, condition) or (market_hash_name, None) if unparseable
        """
        try:
            # Try to extract condition in parentheses
            match = re.match(r'(.+?)\s*\(([^)]+)\)$', market_hash_name)
            if match:
                return (match.group(1).strip(), match.group(2).strip())
            return (market_hash_name, None)
        except Exception as e:
            logger.error(f"Error parsing item name {market_hash_name}: {e}")
            return (market_hash_name, None)
    
    @staticmethod
    def detect_item_type(name: str) -> str:
        """
        Attempt to detect item type from name
        
        Args:
            name: Item name
            
        Returns:
            Detected type or 'other'
        """
        name_lower = name.lower()
        
        if 'case' in name_lower:
            return 'case'
        elif 'agent' in name_lower:
            return 'agent'
        elif 'glove' in name_lower:
            return 'glove'
        elif 'graffiti' in name_lower:
            return 'graffiti'
        elif 'patch' in name_lower:
            return 'patch'
        else:
            # Default to skin if contains condition keywords
            if any(cond in name_lower for cond in ['factory new', 'minimal wear', 'field-tested', 'well-worn', 'battle-scarred']):
                return 'skin'
        
        return 'other'


class DataCleaner:
    """Cleans and normalizes market data"""
    
    @staticmethod
    def clean_price_data(price: float) -> float:
        """Clean and normalize price data"""
        return round(float(price), 2)
    
    @staticmethod
    def clean_volume_data(volume: Optional[int]) -> Optional[int]:
        """Clean and normalize volume data"""
        if volume is None:
            return None
        return max(0, int(volume))
    
    @staticmethod
    def clean_item_name(name: str) -> str:
        """Clean item name (strip whitespace, normalize unicode)"""
        if not name:
            return ''
        # Normalize unicode and strip whitespace
        import unicodedata
        name = unicodedata.normalize('NFKD', name)
        return name.strip()
    
    @staticmethod
    def deduplicate_items(items: List[Dict]) -> List[Dict]:
        """
        Remove duplicate items by name
        
        Args:
            items: List of item dictionaries
            
        Returns:
            Deduplicated list (keeps first occurrence)
        """
        seen = set()
        result = []
        for item in items:
            name = item.get('name', '')
            if name not in seen:
                seen.add(name)
                result.append(item)
        return result
    
    @staticmethod
    def filter_outliers(prices: List[float], threshold: float = 3.0) -> List[float]:
        """
        Filter price outliers using z-score
        
        Args:
            prices: List of prices
            threshold: Z-score threshold (default: 3.0 = 99.7% of data)
            
        Returns:
            Filtered list without outliers
        """
        if len(prices) < 2:
            return prices
        
        import statistics
        try:
            mean = statistics.mean(prices)
            stdev = statistics.stdev(prices)
            
            if stdev == 0:
                return prices
            
            return [p for p in prices if abs((p - mean) / stdev) <= threshold]
        except Exception as e:
            logger.error(f"Error filtering outliers: {e}")
            return prices
