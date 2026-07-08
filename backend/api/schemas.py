from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, date


class ItemOut(BaseModel):
    id: int
    item_id: str
    name: str
    type: str
    icon_url: Optional[str] = None
    release_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrendingItemOut(BaseModel):
    id: int
    item_id: str
    name: str
    type: str
    icon_url: Optional[str] = None
    latest_price: float

    class Config:
        from_attributes = True


class PricePointOut(BaseModel):
    timestamp: datetime
    price: float
    volume: Optional[int] = None
    median_price: Optional[float] = None
    sma_7: Optional[float] = None
    sma_30: Optional[float] = None

    class Config:
        from_attributes = True


class TrendAnalysisOut(BaseModel):
    item_id: int
    item_name: str
    current_price: float
    trend_direction: str
    confidence: str
    sma_7: Optional[float] = None
    sma_30: Optional[float] = None
    volatility: Optional[float] = None
    trend_score: Optional[float] = None
    explanation: str
    rsi: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    support: Optional[float] = None
    resistance: Optional[float] = None
    factors: List[str] = []

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    item_id: int
    item_name: str
    current_price: float
    forecast_low: float
    forecast_mid: float
    forecast_high: float
    forecast_period: str
    trend_direction: str
    confidence: str


class OpportunityOut(BaseModel):
    item_id: int
    item_name: str
    current_price: float
    opportunity_type: str
    opportunity_score: float
    reason: str
    current_trend: str
    volatility: Optional[float] = None

    class Config:
        from_attributes = True


class SourcePriceOut(BaseModel):
    timestamp: datetime
    price: float
    volume: Optional[int] = None
    median_price: Optional[float] = None

    class Config:
        from_attributes = True


class MultiSourcePricesOut(BaseModel):
    item_id: str
    name: str
    sources: List[str]
    data: Dict[str, List[SourcePriceOut]]


class EventOut(BaseModel):
    id: int
    type: str
    timestamp: datetime
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class QualityVariantOut(BaseModel):
    item_id: str
    name: str
    quality: str
    current_price: Optional[float] = None
    price_change_24h: Optional[float] = None
    volume_24h: Optional[int] = None

    class Config:
        from_attributes = True


class GroupedMarketItemOut(BaseModel):
    base_name: str
    type: str
    icon_url: Optional[str] = None
    price_avg: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    price_change_24h: Optional[float] = None
    volatility: Optional[float] = None
    volume_24h: Optional[int] = None
    quality_count: int = 1
    qualities: List[QualityVariantOut] = []


class UserOut(BaseModel):
    id: int
    steam_id: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class HealthOut(BaseModel):
    status: str
    version: str
    environment: str
