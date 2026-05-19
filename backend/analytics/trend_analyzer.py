"""
Trend scoring and analysis engine
Computes market signals and opportunity detection
"""

import statistics
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Analyzes market trends and generates signals"""
    
    # Confidence thresholds
    MIN_DATA_POINTS = 7  # Minimum data points for analysis
    HIGH_CONFIDENCE_THRESHOLD = 0.7
    MEDIUM_CONFIDENCE_THRESHOLD = 0.4
    
    @staticmethod
    def compute_sma(prices: List[float], period: int) -> Optional[float]:
        """
        Compute Simple Moving Average
        
        Args:
            prices: List of prices in chronological order
            period: Number of periods for averaging
            
        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        try:
            return sum(prices[-period:]) / period
        except Exception as e:
            logger.error(f"Error computing SMA: {e}")
            return None
    
    @staticmethod
    def compute_volatility(prices: List[float], period: int = 30) -> Optional[float]:
        """
        Compute price volatility (standard deviation of returns)
        
        Args:
            prices: List of prices in chronological order
            period: Period for volatility calculation
            
        Returns:
            Volatility value (annualized) or None if insufficient data
        """
        if len(prices) < 2:
            return None
        
        try:
            # Calculate daily returns
            returns = []
            for i in range(1, min(period + 1, len(prices))):
                ret = (prices[-i] - prices[-(i+1)]) / prices[-(i+1)] if prices[-(i+1)] != 0 else 0
                returns.append(ret)
            
            if not returns:
                return None
            
            # Standard deviation of returns (daily volatility)
            daily_vol = statistics.stdev(returns) if len(returns) > 1 else 0
            
            # Annualize (252 trading days)
            annual_vol = daily_vol * (252 ** 0.5)
            
            return round(annual_vol, 4)
        
        except Exception as e:
            logger.error(f"Error computing volatility: {e}")
            return None
    
    @staticmethod
    def compute_trend_score(prices: List[float]) -> Optional[float]:
        """
        Compute trend score from -1 (bearish) to 1 (bullish)
        
        Args:
            prices: List of prices in chronological order
            
        Returns:
            Trend score between -1 and 1, or None if insufficient data
        """
        if len(prices) < TrendAnalyzer.MIN_DATA_POINTS:
            return None
        
        try:
            sma_7 = TrendAnalyzer.compute_sma(prices, 7)
            sma_30 = TrendAnalyzer.compute_sma(prices, 30)
            
            current_price = prices[-1]
            
            if not sma_7 or not sma_30:
                return None
            
            # Trend score based on price position relative to averages
            score = 0.0
            
            # Weight current price vs 7-day MA (60% weight)
            if sma_7 != 0:
                score += (current_price - sma_7) / sma_7 * 0.6
            
            # Weight 7-day MA vs 30-day MA (40% weight)
            if sma_30 != 0:
                score += (sma_7 - sma_30) / sma_30 * 0.4
            
            # Clamp score to [-1, 1]
            return max(-1.0, min(1.0, score))
        
        except Exception as e:
            logger.error(f"Error computing trend score: {e}")
            return None
    
    @staticmethod
    def classify_trend(trend_score: Optional[float]) -> Tuple[str, str]:
        """
        Classify trend direction and confidence level
        
        Args:
            trend_score: Trend score from -1 to 1
            
        Returns:
            Tuple of (direction, confidence) where:
                direction: 'bullish', 'neutral', or 'bearish'
                confidence: 'low', 'medium', or 'high'
        """
        if trend_score is None:
            return ('neutral', 'low')
        
        abs_score = abs(trend_score)
        
        # Determine direction
        if trend_score > 0.1:
            direction = 'bullish'
        elif trend_score < -0.1:
            direction = 'bearish'
        else:
            direction = 'neutral'
        
        # Determine confidence
        if abs_score >= TrendAnalyzer.HIGH_CONFIDENCE_THRESHOLD:
            confidence = 'high'
        elif abs_score >= TrendAnalyzer.MEDIUM_CONFIDENCE_THRESHOLD:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        return (direction, confidence)
    
    @staticmethod
    def compute_price_range(prices: List[float], volatility: Optional[float] = None) -> Tuple[float, float]:
        """
        Compute expected short-term price range (7 days)
        
        Args:
            prices: List of prices
            volatility: Computed volatility, or None to compute
            
        Returns:
            Tuple of (low_price, high_price)
        """
        if not prices:
            return (0, 0)
        
        current = prices[-1]
        
        if volatility is None:
            volatility = TrendAnalyzer.compute_volatility(prices) or 0.1
        
        try:
            # Use volatility to estimate short-term range
            # Assuming normal distribution, 2 standard deviations = ~95% confidence
            daily_volatility = volatility / (252 ** 0.5)
            
            # 7-day move (sqrt of time scaling)
            move_magnitude = current * daily_volatility * (7 ** 0.5) * 2
            
            low = max(0.01, current - move_magnitude)
            high = current + move_magnitude
            
            return (round(low, 2), round(high, 2))
        
        except Exception as e:
            logger.error(f"Error computing price range: {e}")
            return (current * 0.95, current * 1.05)


class OpportunityDetector:
    """Detects market opportunities"""
    
    # Thresholds
    UNDERVALUED_THRESHOLD = 0.85  # Below 85% of trend
    OVERHEATED_THRESHOLD = 1.20  # Above 120% of trend
    MOMENTUM_MIN_CHANGE = 0.05    # 5% change minimum
    
    @staticmethod
    def compute_baseline_trend(prices: List[float], window: int = 30) -> Optional[float]:
        """
        Compute baseline trend price using linear regression
        
        Args:
            prices: List of prices
            window: Number of periods to use
            
        Returns:
            Baseline trend price or None if insufficient data
        """
        if len(prices) < window:
            return None
        
        try:
            # Simple linear regression on log prices
            recent_prices = prices[-window:]
            n = len(recent_prices)
            
            x_values = list(range(n))
            y_values = [p for p in recent_prices]
            
            x_mean = sum(x_values) / n
            y_mean = sum(y_values) / n
            
            numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
            denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
            
            if denominator == 0:
                return y_mean
            
            slope = numerator / denominator
            intercept = y_mean - slope * x_mean
            
            # Estimate baseline at current point
            baseline = slope * (n - 1) + intercept
            
            return max(0.01, baseline)
        
        except Exception as e:
            logger.error(f"Error computing baseline trend: {e}")
            return None
    
    @staticmethod
    def detect_undervalued(current_price: float, baseline_trend: Optional[float]) -> Tuple[bool, float]:
        """
        Detect if item is undervalued
        
        Args:
            current_price: Current market price
            baseline_trend: Baseline trend price
            
        Returns:
            Tuple of (is_undervalued, discount_percent)
        """
        if not baseline_trend or baseline_trend == 0:
            return (False, 0.0)
        
        ratio = current_price / baseline_trend
        discount = max(0, (1 - ratio)) * 100
        
        is_undervalued = ratio < OpportunityDetector.UNDERVALUED_THRESHOLD
        
        return (is_undervalued, round(discount, 2))
    
    @staticmethod
    def detect_overheated(current_price: float, baseline_trend: Optional[float]) -> Tuple[bool, float]:
        """
        Detect if item is overheated
        
        Args:
            current_price: Current market price
            baseline_trend: Baseline trend price
            
        Returns:
            Tuple of (is_overheated, premium_percent)
        """
        if not baseline_trend or baseline_trend == 0:
            return (False, 0.0)
        
        ratio = current_price / baseline_trend
        premium = max(0, (ratio - 1)) * 100
        
        is_overheated = ratio > OpportunityDetector.OVERHEATED_THRESHOLD
        
        return (is_overheated, round(premium, 2))
    
    @staticmethod
    def detect_momentum(prices: List[float]) -> Tuple[bool, float, str]:
        """
        Detect momentum in price movement
        
        Args:
            prices: List of prices
            
        Returns:
            Tuple of (has_momentum, change_percent, direction)
        """
        if len(prices) < 2:
            return (False, 0.0, 'neutral')
        
        try:
            # 7-day momentum
            if len(prices) >= 8:
                price_7d_ago = prices[-8]
                current = prices[-1]
            else:
                price_7d_ago = prices[0]
                current = prices[-1]
            
            if price_7d_ago == 0:
                return (False, 0.0, 'neutral')
            
            change = ((current - price_7d_ago) / price_7d_ago) * 100
            direction = 'up' if change > 0 else 'down' if change < 0 else 'neutral'
            
            has_momentum = abs(change) >= OpportunityDetector.MOMENTUM_MIN_CHANGE
            
            return (has_momentum, round(abs(change), 2), direction)
        
        except Exception as e:
            logger.error(f"Error detecting momentum: {e}")
            return (False, 0.0, 'neutral')
