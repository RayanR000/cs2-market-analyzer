from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from database import get_db, User, Item
from api.schemas import ItemOut
from itsdangerous import URLSafeTimedSerializer
from config import settings

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _get_current_user(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get("session")
    if not token:
        return None
    s = URLSafeTimedSerializer(settings.secret_key, salt="session")
    try:
        data = s.loads(token, max_age=86400 * 7)
        return db.query(User).filter(User.id == data["user_id"]).first()
    except Exception:
        return None


@router.get("/inventory")
def get_inventory(request: Request, db: Session = Depends(get_db)):
    user = _get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # TODO: Integrate with Steam Inventory API
    # For now, return an empty inventory
    return {
        "steam_id": user.steam_id,
        "username": user.username,
        "items": [],
    }
