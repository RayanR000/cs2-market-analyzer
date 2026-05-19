"""
Item endpoints
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db, Item
from repositories import ItemRepository, PriceHistoryRepository
from schemas import ItemResponse, PriceHistoryResponse

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/", response_model=dict)
async def list_items(
    type: str = Query(None, description="Filter by type: skin, case, sticker"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all items with optional filtering"""
    if type:
        items = ItemRepository.get_items_by_type(db, type, limit)
    else:
        items = ItemRepository.get_all_items(db, skip, limit)
    
    total = db.query(Item).count()
    
    return {
        "items": [
            {
                "id": item.id,
                "item_id": item.item_id,
                "name": item.name,
                "type": item.type,
                "release_date": item.release_date
            }
            for item in items
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/search", response_model=dict)
async def search_items(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """Search items by name"""
    results = ItemRepository.search_items(db, q)
    return {
        "results": [
            {
                "id": item.id,
                "item_id": item.item_id,
                "name": item.name,
                "type": item.type
            }
            for item in results
        ],
        "total": len(results)
    }

@router.get("/trending", response_model=dict)
async def get_trending(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get trending items"""
    trending = ItemRepository.get_trending_items(db, days, limit)
    return {
        "trending": trending,
        "timestamp": None,
        "period_days": days
    }

@router.get("/{item_id}", response_model=dict)
async def get_item(item_id: str, db: Session = Depends(get_db)):
    """Get item details"""
    item = ItemRepository.get_item_by_id(db, item_id)
    
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "id": item.id,
        "item_id": item.item_id,
        "name": item.name,
        "type": item.type,
        "release_date": item.release_date
    }

@router.get("/{item_id}/price-history", response_model=dict)
async def get_price_history(
    item_id: str,
    days: int = Query(30, ge=1, le=365),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db)
):
    """Get price history for an item"""
    item = ItemRepository.get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    history = PriceHistoryRepository.get_price_history(db, item.id, days, skip, limit)
    
    return {
        "item_id": item_id,
        "history": [
            {
                "id": h.id,
                "timestamp": h.timestamp,
                "price": h.price,
                "volume": h.volume,
                "median_price": h.median_price
            }
            for h in history
        ],
        "total": len(history)
    }

@router.get("/{item_id}/trends", response_model=dict)
async def get_trends(item_id: str, db: Session = Depends(get_db)):
    """Get trend analysis for an item"""
    item = ItemRepository.get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "item_id": item_id,
        "trend_direction": "neutral",
        "confidence": "low",
        "sma_7": None,
        "sma_30": None,
        "volatility": None
    }

@router.get("/{item_id}/prediction", response_model=dict)
async def get_prediction(
    item_id: str,
    period: str = Query("7_days"),
    db: Session = Depends(get_db)
):
    """Get price prediction for an item"""
    item = ItemRepository.get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "item_id": item_id,
        "forecast_low": 0.0,
        "forecast_high": 0.0,
        "period": period,
        "confidence": "low"
    }

@router.get("/{item_id}/events", response_model=dict)
async def get_item_events(
    item_id: str,
    limit: int = Query(20),
    db: Session = Depends(get_db)
):
    """Get market events related to an item"""
    item = ItemRepository.get_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    
    return {
        "item_id": item_id,
        "events": []
    }
