from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta, timezone

from database import get_db, Item, DailyAnalysis, PriceHistory
from pydantic import BaseModel

router = APIRouter(prefix="/market", tags=["market"])


class MarketItemOut(BaseModel):
    id: int
    item_id: str
    name: str
    type: str
    icon_url: Optional[str] = None
    current_price: Optional[float] = None
    price_change_24h: Optional[float] = None
    volatility: Optional[float] = None
    volume_24h: Optional[int] = None

    class Config:
        from_attributes = True


@router.get("/summary", response_model=list[MarketItemOut])
def market_summary(
    type: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Search query for item name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Item)
    if type:
        query = query.filter(Item.type == type)
    if q:
        query = query.filter(Item.name.ilike(f"%{q}%"))
    items = query.order_by(Item.name).offset(skip).limit(limit).all()
    if not items:
        return []

    item_ids = [i.id for i in items]

    latest_sub = (
        db.query(
            DailyAnalysis.item_id,
            DailyAnalysis.analysis_date,
        )
        .distinct(DailyAnalysis.item_id)
        .order_by(DailyAnalysis.item_id, desc(DailyAnalysis.analysis_date))
        .subquery()
    )
    daily_rows = (
        db.query(DailyAnalysis)
        .join(
            latest_sub,
            (DailyAnalysis.item_id == latest_sub.c.item_id)
            & (DailyAnalysis.analysis_date == latest_sub.c.analysis_date),
        )
        .filter(DailyAnalysis.item_id.in_(item_ids))
        .all()
    )
    daily_map = {d.item_id: d for d in daily_rows}

    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    price_rows = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.item_id.in_(item_ids),
            PriceHistory.timestamp >= cutoff,
        )
        .order_by(PriceHistory.item_id, PriceHistory.timestamp)
        .all()
    )
    prices_by_item: dict[int, list] = {}
    for pr in price_rows:
        prices_by_item.setdefault(pr.item_id, []).append(pr)

    result = []
    for item in items:
        da = daily_map.get(item.id)
        ph_list = prices_by_item.get(item.id, [])

        current_price = None
        price_change_24h = None
        volume_24h = None

        if da and da.current_price:
            current_price = da.current_price
        elif ph_list:
            current_price = ph_list[-1].price

        if len(ph_list) >= 2:
            first = ph_list[0]
            last = ph_list[-1]
            if first.price > 0:
                price_change_24h = round(((last.price - first.price) / first.price) * 100, 2)
            volume_24h = sum((p.volume or 0) for p in ph_list)

        result.append(MarketItemOut(
            id=item.id,
            item_id=item.item_id,
            name=item.name,
            type=item.type,
            icon_url=item.icon_url,
            current_price=current_price,
            price_change_24h=price_change_24h,
            volatility=da.volatility if da else None,
            volume_24h=volume_24h,
        ))

    return result
