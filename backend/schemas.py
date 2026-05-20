"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

# Item schemas
class ItemBase(BaseModel):
    name: str
    type: str  # skin, case, sticker
    release_date: Optional[datetime] = None

class ItemCreate(ItemBase):
    item_id: str

class ItemResponse(ItemBase):
    id: int
    item_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Price history schemas
class PriceHistoryBase(BaseModel):
    price: float
    volume: Optional[int] = None
    median_price: Optional[float] = None
    source: str = "steam"  # steam, csfloat, synthetic_demo, cs2sh_archive
    timestamp: datetime

class PriceHistoryCreate(PriceHistoryBase):
    item_id: int

class PriceHistoryResponse(PriceHistoryBase):
    id: int
    item_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChartDataPoint(BaseModel):
    timestamp: datetime
    price: float
    volume: Optional[int] = None
    sma_7: Optional[float] = None
    sma_30: Optional[float] = None

# Event schemas
class EventBase(BaseModel):
    type: str  # major, update, case_drop, operation
    timestamp: datetime
    description: str

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Trend indicator schemas
class TrendIndicatorBase(BaseModel):
    sma_7: Optional[float] = None
    sma_30: Optional[float] = None
    volatility: Optional[float] = None
    trend_score: Optional[float] = None
    trend_direction: Optional[str] = None
    confidence: Optional[str] = None

class TrendResponse(TrendIndicatorBase):
    id: int
    item_id: int
    timestamp: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True

# Trend analysis response
class TrendAnalysisResponse(BaseModel):
    item_id: int
    item_name: str
    current_price: float
    trend_direction: str  # bullish, neutral, bearish
    confidence: str  # low, medium, high
    sma_7: Optional[float] = None
    sma_30: Optional[float] = None
    volatility: Optional[float] = None
    trend_score: Optional[float] = None
    explanation: str

# Prediction response
class PredictionResponse(BaseModel):
    item_id: int
    item_name: str
    current_price: float
    forecast_low: float
    forecast_high: float
    forecast_period: str  # "7_days", "30_days"
    trend_direction: str
    confidence: str
    methodology: str = "Moving average + linear regression"

# Opportunity response
class OpportunityResponse(BaseModel):
    item_id: int
    item_name: str
    current_price: float
    opportunity_type: str  # undervalued, overheated, momentum
    opportunity_score: float  # 0-100
    reason: str
    current_trend: str
    volatility: Optional[float] = None

# Search response
class SearchResultItem(BaseModel):
    item_id: str
    name: str
    type: str
    current_price: Optional[float] = None
    price_change_7d: Optional[float] = None

class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int

# User schemas
class UserBase(BaseModel):
    steam_id: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    last_login: datetime

    class Config:
        from_attributes = True

# Portfolio inventory schemas
class InventoryItem(BaseModel):
    id: str  # asset_id from steam
    name: str
    market_hash_name: str
    quantity: int = 1
    current_price: Optional[float] = None
    image_url: Optional[str] = None
    type: str

class InventoryResponse(BaseModel):
    items: List[InventoryItem]
    total_value: float
    user_id: str
