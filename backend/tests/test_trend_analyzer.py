"""
Tests for trend analysis and analytics module
"""

import pytest
from analytics.trend_analyzer import TrendAnalyzer, OpportunityDetector


class TestTrendAnalyzer:
    """Test trend analyzer functions"""
    
    def test_compute_sma_sufficient_data(self):
        """Test SMA with sufficient data"""
        prices = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        sma = TrendAnalyzer.compute_sma(prices, 7)
        
        assert sma is not None
        assert 16 < sma < 18
    
    def test_compute_sma_insufficient_data(self):
        """Test SMA with insufficient data"""
        prices = [10, 11, 12]
        sma = TrendAnalyzer.compute_sma(prices, 7)
        
        assert sma is None
    
    def test_compute_sma_exact_period(self):
        """Test SMA with exact data points"""
        prices = [10.0, 20.0, 30.0]
        sma = TrendAnalyzer.compute_sma(prices, 3)
        
        assert sma == 20.0
    
    def test_compute_volatility_basic(self):
        """Test volatility computation"""
        prices = [100, 102, 101, 103, 99, 101, 102, 100, 104, 98]
        vol = TrendAnalyzer.compute_volatility(prices, 10)
        
        assert vol is not None
        assert vol > 0
        assert vol < 1  # Should be reasonable
    
    def test_compute_trend_score_bullish(self):
        """Test trend score for bullish trend"""
        # Prices trending upward
        prices = list(range(10, 40))
        score = TrendAnalyzer.compute_trend_score(prices)
        
        assert score is not None
        assert score > 0  # Should be positive for uptrend
    
    def test_compute_trend_score_bearish(self):
        """Test trend score for bearish trend"""
        # Prices trending downward
        prices = list(range(40, 10, -1))
        score = TrendAnalyzer.compute_trend_score(prices)
        
        assert score is not None
        assert score < 0  # Should be negative for downtrend
    
    def test_classify_trend_bullish(self):
        """Test trend classification - bullish"""
        direction, confidence = TrendAnalyzer.classify_trend(0.8)
        
        assert direction == 'bullish'
        assert confidence == 'high'
    
    def test_classify_trend_bearish(self):
        """Test trend classification - bearish"""
        direction, confidence = TrendAnalyzer.classify_trend(-0.6)
        
        assert direction == 'bearish'
        assert confidence == 'medium'
    
    def test_classify_trend_neutral(self):
        """Test trend classification - neutral"""
        direction, confidence = TrendAnalyzer.classify_trend(0.02)
        
        assert direction == 'neutral'
    
    def test_classify_trend_none(self):
        """Test trend classification with None"""
        direction, confidence = TrendAnalyzer.classify_trend(None)
        
        assert direction == 'neutral'
        assert confidence == 'low'
    
    def test_compute_price_range_basic(self):
        """Test price range computation"""
        prices = [100.0] * 30
        low, high = TrendAnalyzer.compute_price_range(prices)
        
        assert low > 0
        assert high > low
        assert low < 100 < high
    
    def test_compute_price_range_empty(self):
        """Test price range with empty list"""
        low, high = TrendAnalyzer.compute_price_range([])
        
        assert low == 0
        assert high == 0


class TestOpportunityDetector:
    """Test opportunity detection functions"""
    
    def test_compute_baseline_trend_sufficient_data(self):
        """Test baseline trend with sufficient data"""
        prices = list(range(1, 51))  # 1 to 50
        baseline = OpportunityDetector.compute_baseline_trend(prices, 30)
        
        assert baseline is not None
        assert baseline > 0
    
    def test_compute_baseline_trend_insufficient_data(self):
        """Test baseline trend with insufficient data"""
        prices = [10, 11, 12]
        baseline = OpportunityDetector.compute_baseline_trend(prices, 30)
        
        assert baseline is None
    
    def test_detect_undervalued_true(self):
        """Test undervalued detection when item is undervalued"""
        is_undervalued, discount = OpportunityDetector.detect_undervalued(75, 100)
        
        assert is_undervalued is True
        assert discount > 0
        assert discount > 15
    
    def test_detect_undervalued_false(self):
        """Test undervalued detection when item is not undervalued"""
        is_undervalued, discount = OpportunityDetector.detect_undervalued(100, 100)
        
        assert is_undervalued is False
        assert discount == 0
    
    def test_detect_overheated_true(self):
        """Test overheated detection when item is overheated"""
        is_overheated, premium = OpportunityDetector.detect_overheated(130, 100)
        
        assert is_overheated is True
        assert premium > 0
    
    def test_detect_overheated_false(self):
        """Test overheated detection when item is not overheated"""
        is_overheated, premium = OpportunityDetector.detect_overheated(100, 100)
        
        assert is_overheated is False
        assert premium == 0
    
    def test_detect_momentum_upward(self):
        """Test momentum detection - upward"""
        prices = list(range(10, 50))  # Increasing prices
        has_momentum, change, direction = OpportunityDetector.detect_momentum(prices)
        
        assert has_momentum is True
        assert change > 0
        assert direction == 'up'
    
    def test_detect_momentum_downward(self):
        """Test momentum detection - downward"""
        prices = list(range(50, 10, -1))  # Decreasing prices
        has_momentum, change, direction = OpportunityDetector.detect_momentum(prices)
        
        assert has_momentum is True
        assert change > 0
        assert direction == 'down'
    
    def test_detect_momentum_none(self):
        """Test momentum detection with minimal price change"""
        prices = [100] * 8
        has_momentum, change, direction = OpportunityDetector.detect_momentum(prices)
        
        assert has_momentum is False
        assert change == 0
        assert direction == 'neutral'
    
    def test_detect_momentum_short_list(self):
        """Test momentum detection with short price list"""
        has_momentum, change, direction = OpportunityDetector.detect_momentum([100])
        
        assert has_momentum is False
        assert change == 0
