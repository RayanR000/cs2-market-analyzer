from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db, Event
from api.schemas import EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[EventOut])
def list_events(
    type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Event)
    if type:
        q = q.filter(Event.type == type)
    return q.order_by(desc(Event.timestamp)).offset(skip).limit(limit).all()


@router.get("/recent", response_model=list[EventOut])
def recent_events(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return (
        db.query(Event)
        .order_by(desc(Event.timestamp))
        .limit(limit)
        .all()
    )
