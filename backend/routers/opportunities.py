"""
Opportunities endpoints
"""

from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db, Item
from repositories import ItemRepository
from analytics.trend_analyzer import OpportunityDetector, TrendAnalyzer

router = APIRouter(prefix="/opportunities", tags=["opportunities"])

@router.get("/")
async def get_opportunities(
    type: str = Query(None, description="Filter by type: undervalued, overheated, momentum"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get top opportunity items across all types"""
    items = ItemRepository.get_all_items(db, skip=0, limit=1000)
    opportunities = []
    
    for item in items:
        price_history = sorted(item.price_histories[-90:], key=lambda h: h.timestamp)
        prices = [h.price for h in price_history]
        
        if len(prices) < 7:
            continue
        
        current_price = prices[-1]
        baseline = OpportunityDetector.compute_baseline_trend(prices)
        
        if not baseline:
            continue
        
        is_undervalued, discount = OpportunityDetector.detect_undervalued(current_price, baseline)
        is_overheated, premium = OpportunityDetector.detect_overheated(current_price, baseline)
        has_momentum, change_pct, momentum_dir = OpportunityDetector.detect_momentum(prices)
        
        volatility = TrendAnalyzer.compute_volatility(prices)
        trend_score = TrendAnalyzer.compute_trend_score(prices)
        direction, confidence = TrendAnalyzer.classify_trend(trend_score)
        
        opportunity_type = None
        score = 0
        reason = ""
        
        if is_undervalued:
            opportunity_type = "undervalued"
            score = discount * 1.5
            reason = f"Trading {discount:.1f}% below 90-day trend"
        elif is_overheated:
            opportunity_type = "overheated"
            score = premium
            reason = f"Trading {premium:.1f}% above 90-day trend"
        elif has_momentum:
            opportunity_type = "momentum"
            score = change_pct * 0.8
            reason = f"{change_pct:.1f}% {momentum_dir} movement"
        
        if opportunity_type:
            opportunities.append({
                "item_id": item.item_id,
                "item_name": item.name,
                "item_type": item.type,
                "current_price": round(current_price, 2),
                "opportunity_type": opportunity_type,
                "opportunity_score": round(min(score, 100), 1),
                "reason": reason,
                "trend": direction,
                "confidence": confidence,
                "volatility": round(volatility, 4) if volatility else None
            })
    
    # Filter by type if specified
    if type:
        opportunities = [o for o in opportunities if o["opportunity_type"] == type]
    
    # Sort by score descending
    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
    
    return {
        "opportunities": opportunities[:limit],
        "total": len(opportunities),
        "filtered_type": type
    }

@router.get("/undervalued")
async def get_undervalued(
    limit: int = Query(10, ge=1, le=50),
    min_discount: float = Query(5.0, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """Get undervalued items (below historical trend)"""
    items = ItemRepository.get_all_items(db, skip=0, limit=1000)
    undervalued = []
    
    for item in items:
        price_history = sorted(item.price_histories[-90:], key=lambda h: h.timestamp)
        prices = [h.price for h in price_history]
        
        if len(prices) < 7:
            continue
        
        current_price = prices[-1]
        baseline = OpportunityDetector.compute_baseline_trend(prices)
        
        if not baseline:
            continue
        
        is_undervalued, discount = OpportunityDetector.detect_undervalued(current_price, baseline)
        
        if is_undervalued and discount >= min_discount:
            volatility = TrendAnalyzer.compute_volatility(prices)
            trend_score = TrendAnalyzer.compute_trend_score(prices)
            direction, confidence = TrendAnalyzer.classify_trend(trend_score)
            
            undervalued.append({
                "item_id": item.item_id,
                "item_name": item.name,
                "item_type": item.type,
                "current_price": round(current_price, 2),
                "baseline_price": round(baseline, 2),
                "discount_percent": round(discount, 1),
                "trend": direction,
                "confidence": confidence,
                "volatility": round(volatility, 4) if volatility else None,
                "opportunity_score": round(discount * 1.5, 1)
            })
    
    undervalued.sort(key=lambda x: x["opportunity_score"], reverse=True)
    
    return {
        "items": undervalued[:limit],
        "total": len(undervalued),
        "min_discount_filter": min_discount
    }

@router.get("/overheated")
async def get_overheated(
    limit: int = Query(10, ge=1, le=50),
    min_premium: float = Query(10.0, ge=0, le=500),
    db: Session = Depends(get_db)
):
    """Get overheated items (rapid unsustainable growth)"""
    items = ItemRepository.get_all_items(db, skip=0, limit=1000)
    overheated = []
    
    for item in items:
        price_history = sorted(item.price_histories[-90:], key=lambda h: h.timestamp)
        prices = [h.price for h in price_history]
        
        if len(prices) < 7:
            continue
        
        current_price = prices[-1]
        baseline = OpportunityDetector.compute_baseline_trend(prices)
        
        if not baseline:
            continue
        
        is_overheated, premium = OpportunityDetector.detect_overheated(current_price, baseline)
        
        if is_overheated and premium >= min_premium:
            volatility = TrendAnalyzer.compute_volatility(prices)
            trend_score = TrendAnalyzer.compute_trend_score(prices)
            direction, confidence = TrendAnalyzer.classify_trend(trend_score)
            
            overheated.append({
                "item_id": item.item_id,
                "item_name": item.name,
                "item_type": item.type,
                "current_price": round(current_price, 2),
                "baseline_price": round(baseline, 2),
                "premium_percent": round(premium, 1),
                "trend": direction,
                "confidence": confidence,
                "volatility": round(volatility, 4) if volatility else None,
                "risk_score": round(premium * 0.8, 1)
            })
    
    overheated.sort(key=lambda x: x["risk_score"], reverse=True)
    
    return {
        "items": overheated[:limit],
        "total": len(overheated),
        "min_premium_filter": min_premium
    }

@router.get("/momentum")
async def get_momentum(
    limit: int = Query(10, ge=1, le=50),
    min_change: float = Query(5.0, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """Get momentum items (strong directional movement)"""
    items = ItemRepository.get_all_items(db, skip=0, limit=1000)
    momentum_items = []
    
    for item in items:
        price_history = sorted(item.price_histories[-90:], key=lambda h: h.timestamp)
        prices = [h.price for h in price_history]
        
        if len(prices) < 7:
            continue
        
        current_price = prices[-1]
        has_momentum, change_pct, momentum_dir = OpportunityDetector.detect_momentum(prices)
        
        if has_momentum and change_pct >= min_change:
            volatility = TrendAnalyzer.compute_volatility(prices)
            trend_score = TrendAnalyzer.compute_trend_score(prices)
            direction, confidence = TrendAnalyzer.classify_trend(trend_score)
            
            momentum_items.append({
                "item_id": item.item_id,
                "item_name": item.name,
                "item_type": item.type,
                "current_price": round(current_price, 2),
                "change_percent_7d": round(change_pct, 1),
                "direction": momentum_dir,
                "trend": direction,
                "confidence": confidence,
                "volatility": round(volatility, 4) if volatility else None,
                "momentum_score": round(change_pct * 0.8, 1)
            })
    
    momentum_items.sort(key=lambda x: x["momentum_score"], reverse=True)
    
    return {
        "items": momentum_items[:limit],
        "total": len(momentum_items),
        "min_change_filter": min_change
    }
