from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from datetime import datetime, timedelta, timezone
import math

from database import get_db, Item, PriceHistory, TrendIndicator, DailyAnalysis, ItemForecast, Event, EventImpact
from api.schemas import (
    ItemOut, PricePointOut, TrendAnalysisOut, PredictionOut,
    SourcePriceOut, MultiSourcePricesOut, EventOut, TrendingItemOut
)

router = APIRouter(prefix="/items", tags=["items"])


def _resolve_item(item_id: str, db: Session) -> Item:
    item = db.query(Item).filter(Item.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/", response_model=list[ItemOut])
def list_items(
    type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Item)
    if type:
        q = q.filter(Item.type == type)
    return q.order_by(Item.name).offset(skip).limit(limit).all()


@router.get("/search", response_model=list[ItemOut])
def search_items(
    q: str = Query(min_length=1),
    db: Session = Depends(get_db),
):
    return (
        db.query(Item)
        .filter(Item.name.ilike(f"%{q}%"))
        .order_by(Item.name)
        .limit(50)
        .all()
    )


@router.get("/trending", response_model=list[TrendingItemOut])
def trending_items(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = (
        db.query(Item)
        .order_by(desc(Item.updated_at))
        .limit(limit)
        .all()
    )
    item_ids = [i.id for i in items]

    latest_prices = {}
    for item_id in item_ids:
        latest = (
            db.query(PriceHistory)
            .filter(PriceHistory.item_id == item_id)
            .order_by(desc(PriceHistory.timestamp))
            .first()
        )
        if latest:
            latest_prices[item_id] = latest.price

    return [
        TrendingItemOut(
            id=item.id,
            item_id=item.item_id,
            name=item.name,
            type=item.type,
            icon_url=item.icon_url,
            latest_price=latest_prices.get(item.id, 0.0),
        )
        for item in items
    ]


@router.get("/{item_id}", response_model=ItemOut)
def get_item(item_id: str, db: Session = Depends(get_db)):
    return _resolve_item(item_id, db)


@router.get("/{item_id}/price-history", response_model=list[PricePointOut])
def get_price_history(
    item_id: str,
    days: int = Query(30, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    item = _resolve_item(item_id, db)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.item_id == item.id,
            PriceHistory.timestamp >= cutoff,
        )
        .order_by(PriceHistory.timestamp)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        PricePointOut(
            timestamp=r.timestamp,
            price=r.price,
            volume=r.volume,
            median_price=r.median_price,
        )
        for r in records
    ]


@router.get("/{item_id}/trends", response_model=TrendAnalysisOut)
def get_item_trends(item_id: str, db: Session = Depends(get_db)):
    item = _resolve_item(item_id, db)
    latest_analysis = (
        db.query(DailyAnalysis)
        .filter(DailyAnalysis.item_id == item.id)
        .order_by(desc(DailyAnalysis.analysis_date))
        .first()
    )
    latest_ti = (
        db.query(TrendIndicator)
        .filter(TrendIndicator.item_id == item.id)
        .order_by(desc(TrendIndicator.timestamp))
        .first()
    )
    latest_price = (
        db.query(PriceHistory)
        .filter(PriceHistory.item_id == item.id)
        .order_by(desc(PriceHistory.timestamp))
        .first()
    )

    current_price = latest_price.price if latest_price else 0.0
    trend_dir = "neutral"
    confidence = "low"
    sma_7 = None
    sma_30 = None
    volatility = None
    trend_score = None

    if latest_ti:
        trend_dir = latest_ti.trend_direction or "neutral"
        confidence = latest_ti.confidence or "low"
        sma_7 = latest_ti.sma_7
        sma_30 = latest_ti.sma_30
        volatility = latest_ti.volatility
        trend_score = latest_ti.trend_score
    elif latest_analysis:
        trend_dir = latest_analysis.trend_direction or "neutral"
        confidence = "medium" if latest_analysis.opportunity_score else "low"
        sma_7 = latest_analysis.ma_7day
        sma_30 = latest_analysis.ma_30day
        volatility = latest_analysis.volatility
        trend_score = latest_analysis.momentum_score

    explanation = _build_trend_explanation(trend_dir, confidence, sma_7, current_price)
    return TrendAnalysisOut(
        item_id=item.id,
        item_name=item.name,
        current_price=current_price,
        trend_direction=trend_dir,
        confidence=confidence,
        sma_7=sma_7,
        sma_30=sma_30,
        volatility=volatility,
        trend_score=trend_score,
        explanation=explanation,
    )


def _build_trend_explanation(direction: str, confidence: str, sma_7, current_price) -> str:
    if direction == "bullish":
        return f"Price momentum is strong. Confidence is {confidence}."
    elif direction == "bearish":
        return f"Price showing downward momentum. Confidence is {confidence}."
    return f"Price is relatively stable. Confidence is {confidence}."


@router.get("/{item_id}/prediction", response_model=PredictionOut)
def get_item_prediction(
    item_id: str,
    period: str = Query("7_days", pattern="^(7_days|30_days)$"),
    db: Session = Depends(get_db),
):
    item = _resolve_item(item_id, db)
    horizon = 7 if period == "7_days" else 30

    forecast = (
        db.query(ItemForecast)
        .filter(
            ItemForecast.item_id == item.id,
            ItemForecast.horizon_days == horizon,
        )
        .order_by(desc(ItemForecast.forecast_date))
        .first()
    )

    latest_price = (
        db.query(PriceHistory)
        .filter(PriceHistory.item_id == item.id)
        .order_by(desc(PriceHistory.timestamp))
        .first()
    )
    current_price = latest_price.price if latest_price else 0.0

    if forecast:
        fl = forecast.price_low or current_price * 0.9
        fh = forecast.price_high or current_price * 1.1
        fm = forecast.price_mid or (fl + fh) / 2
        return PredictionOut(
            item_id=item.id,
            item_name=item.name,
            current_price=forecast.current_price or current_price,
            forecast_low=fl,
            forecast_mid=fm,
            forecast_high=fh,
            forecast_period=period,
            trend_direction=forecast.direction or "neutral",
            confidence=forecast.confidence or "low",
        )

    fl = current_price * 0.9
    fh = current_price * 1.1
    return PredictionOut(
        item_id=item.id,
        item_name=item.name,
        current_price=current_price,
        forecast_low=fl,
        forecast_mid=(fl + fh) / 2,
        forecast_high=fh,
        forecast_period=period,
        trend_direction="neutral",
        confidence="low",
    )


@router.get("/{item_id}/events", response_model=list[EventOut])
def get_item_events(
    item_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    item = _resolve_item(item_id, db)
    event_ids = (
        db.query(EventImpact.event_id)
        .filter(EventImpact.item_id == item.id)
        .subquery()
    )
    events = (
        db.query(Event)
        .filter(Event.id.in_(event_ids))
        .order_by(desc(Event.timestamp))
        .limit(limit)
        .all()
    )
    return events


@router.get("/{item_id}/prices", response_model=MultiSourcePricesOut)
def get_multi_source_prices(
    item_id: str,
    source: str = Query("steam", description="Comma-separated sources"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    item = _resolve_item(item_id, db)
    sources = [s.strip() for s in source.split(",")]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    data: dict[str, list[SourcePriceOut]] = {}
    for src in sources:
        records = (
            db.query(PriceHistory)
            .filter(
                PriceHistory.item_id == item.id,
                PriceHistory.source == src,
                PriceHistory.timestamp >= cutoff,
            )
            .order_by(PriceHistory.timestamp)
            .all()
        )
        data[src] = [
            SourcePriceOut(
                timestamp=r.timestamp,
                price=r.price,
                volume=r.volume,
                median_price=r.median_price,
            )
            for r in records
        ]

    return MultiSourcePricesOut(
        item_id=item.item_id,
        name=item.name,
        sources=sources,
        data=data,
    )
