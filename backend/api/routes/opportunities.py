from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db, DailyAnalysis, Item
from api.schemas import OpportunityOut

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _build_opportunity(item: Item, analysis: DailyAnalysis, opp_type: str) -> OpportunityOut:
    return OpportunityOut(
        item_id=item.id,
        item_name=item.name,
        current_price=analysis.current_price or 0.0,
        opportunity_type=opp_type,
        opportunity_score=analysis.opportunity_score or 0.0,
        reason=_reason_for_type(opp_type, analysis),
        current_trend=analysis.trend_direction or "neutral",
        volatility=analysis.volatility,
    )


def _reason_for_type(opp_type: str, a: DailyAnalysis) -> str:
    if opp_type == "undervalued":
        return "Price is below moving averages with potential for reversion."
    if opp_type == "overheated":
        return "Price has risen sharply above moving averages."
    return "Strong upward momentum with increasing volume."


def _load_items(item_ids: list[int], db: Session) -> dict[int, Item]:
    if not item_ids:
        return {}
    items = db.query(Item).filter(Item.id.in_(item_ids)).all()
    return {i.id: i for i in items}


def _latest_analyses(db: Session):
    subq = (
        db.query(
            DailyAnalysis.item_id,
            DailyAnalysis.analysis_date,
        )
        .distinct(DailyAnalysis.item_id)
        .order_by(
            DailyAnalysis.item_id,
            desc(DailyAnalysis.analysis_date),
        )
        .subquery()
    )
    return (
        db.query(DailyAnalysis)
        .join(subq, (DailyAnalysis.item_id == subq.c.item_id) & (DailyAnalysis.analysis_date == subq.c.analysis_date))
        .all()
    )


@router.get("/", response_model=list[OpportunityOut])
def get_opportunities(
    type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    analyses = _latest_analyses(db)
    item_ids = [a.item_id for a in analyses if a.opportunity_score is not None]
    items_map = _load_items(item_ids, db)

    results = []
    for a in analyses:
        if a.opportunity_score is None:
            continue
        item = items_map.get(a.item_id)
        if not item:
            continue

        if a.opportunity_score > 0.6:
            opp_type = "undervalued"
        elif a.opportunity_score < -0.4:
            opp_type = "overheated"
        else:
            opp_type = "momentum"

        if type and opp_type != type:
            continue

        results.append(_build_opportunity(item, a, opp_type))

    results.sort(key=lambda x: abs(x.opportunity_score), reverse=True)
    return results[:limit]


@router.get("/undervalued", response_model=list[OpportunityOut])
def get_undervalued(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    analyses = (
        db.query(DailyAnalysis)
        .filter(DailyAnalysis.opportunity_score > 0.5)
        .order_by(desc(DailyAnalysis.opportunity_score))
        .limit(limit)
        .all()
    )
    items_map = _load_items([a.item_id for a in analyses], db)
    results = []
    for a in analyses:
        item = items_map.get(a.item_id)
        if not item:
            continue
        results.append(_build_opportunity(item, a, "undervalued"))
    return results


@router.get("/overheated", response_model=list[OpportunityOut])
def get_overheated(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    analyses = (
        db.query(DailyAnalysis)
        .filter(DailyAnalysis.opportunity_score < -0.3)
        .order_by(DailyAnalysis.opportunity_score)
        .limit(limit)
        .all()
    )
    items_map = _load_items([a.item_id for a in analyses], db)
    results = []
    for a in analyses:
        item = items_map.get(a.item_id)
        if not item:
            continue
        results.append(_build_opportunity(item, a, "overheated"))
    return results


@router.get("/momentum", response_model=list[OpportunityOut])
def get_momentum(
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    analyses = (
        db.query(DailyAnalysis)
        .filter(DailyAnalysis.momentum_score > 0.3)
        .order_by(desc(DailyAnalysis.momentum_score))
        .limit(limit)
        .all()
    )
    items_map = _load_items([a.item_id for a in analyses], db)
    results = []
    for a in analyses:
        item = items_map.get(a.item_id)
        if not item:
            continue
        results.append(_build_opportunity(item, a, "momentum"))
    return results
