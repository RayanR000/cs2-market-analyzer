import re
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func, case
from datetime import datetime, timedelta, timezone
from collections import defaultdict

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


class QualityVariantOut(BaseModel):
    item_id: str
    name: str
    quality: str
    current_price: Optional[float] = None
    price_change_24h: Optional[float] = None
    volume_24h: Optional[int] = None


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


def _normalize(s: str) -> str:
    """Strip non-alphanumeric characters and lowercase for fuzzy matching."""
    return re.sub(r'[^a-zA-Z0-9]', '', s).lower()


def _parse_item_name(name: str):
    """Extract base name and quality from a full item name.

    Examples:
        'AK-47 | Redline (Field-Tested)' -> ('AK-47 | Redline', 'Field-Tested')
        'StatTrak™ M4A4 | Desolate (FN)' -> ('StatTrak™ M4A4 | Desolate', 'FN')
        'Sticker | Dragon' -> ('Sticker | Dragon', None)
    """
    match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return name, None


@router.get("/summary", response_model=list[GroupedMarketItemOut])
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
        normalized = _normalize(q)
        name_norm = func.regexp_replace(func.lower(Item.name), '[^a-zA-Z0-9]', '', 'g')

        direct = Item.name.ilike(f"%{q}%")
        norm_match = name_norm.ilike(f"%{normalized}%")

        conditions = [direct, norm_match]
        if len(q) >= 3:
            fuzzy = func.similarity(Item.name, q) > 0.12
            conditions.append(fuzzy)

        query = query.filter(or_(*conditions))
        query = query.order_by(
            case((direct, 0), else_=1),
            case((norm_match, 0), else_=1),
            func.similarity(Item.name, q).desc(),
            Item.name,
        )
    else:
        query = query.order_by(Item.name)

    items = query.all()
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

    per_item = {}
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

        base_name, quality = _parse_item_name(item.name)

        per_item[item.item_id] = {
            "base_name": base_name,
            "quality": quality,
            "item": item,
            "da": da,
            "current_price": current_price,
            "price_change_24h": price_change_24h,
            "volume_24h": volume_24h,
        }

    groups: dict[str, list] = defaultdict(list)
    for data in per_item.values():
        groups[data["base_name"]].append(data)

    result = []
    for base_name, variants in groups.items():
        deduped: dict[str, dict] = {}
        for v in variants:
            q = v["quality"] or "Standard"
            if q not in deduped or (v["current_price"] is not None and deduped[q].get("current_price") is None):
                deduped[q] = v
        variants = list(deduped.values())

        prices = [v["current_price"] for v in variants if v["current_price"] is not None]
        volumes = [v["volume_24h"] for v in variants if v["volume_24h"] is not None]
        changes = [v["price_change_24h"] for v in variants if v["price_change_24h"] is not None]
        volatilities = [v["da"].volatility for v in variants if v["da"] and v["da"].volatility is not None]

        first_variant = variants[0]
        item = first_variant["item"]

        price_avg = round(sum(prices) / len(prices), 2) if prices else None
        price_min = round(min(prices), 2) if prices else None
        price_max = round(max(prices), 2) if prices else None
        avg_change = round(sum(changes) / len(changes), 2) if changes else None
        avg_volatility = round(sum(volatilities) / len(volatilities), 2) if volatilities else None
        total_volume = sum(volumes) if volumes else None

        quality_list = []
        for v in variants:
            quality_list.append(QualityVariantOut(
                item_id=v["item"].item_id,
                name=v["item"].name,
                quality=v["quality"] or "Standard",
                current_price=v["current_price"],
                price_change_24h=v["price_change_24h"],
                volume_24h=v["volume_24h"],
            ))

        quality_list.sort(key=lambda x: x.quality)

        result.append(GroupedMarketItemOut(
            base_name=base_name,
            type=item.type,
            icon_url=item.icon_url,
            price_avg=price_avg,
            price_min=price_min,
            price_max=price_max,
            price_change_24h=avg_change,
            volatility=avg_volatility,
            volume_24h=total_volume,
            quality_count=len(variants),
            qualities=quality_list,
        ))

    return result
