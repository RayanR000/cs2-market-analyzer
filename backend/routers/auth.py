"""
Authentication router for Steam OpenID
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import requests
import re
from typing import Optional
import logging

from database import get_db
from repositories import UserRepository
from config import settings
from schemas import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"

@router.get("/steam/login")
async def steam_login(request: Request):
    """Redirect to Steam for OpenID login"""
    # Build the return URL
    return_to = str(request.url_for("steam_callback"))
    
    # OpenID 2.0 parameters for Steam
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": f"{request.url.scheme}://{request.url.netloc}",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select"
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return RedirectResponse(f"{STEAM_OPENID_URL}?{query_string}")

@router.get("/steam/callback")
async def steam_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Steam OpenID callback"""
    params = dict(request.query_params)
    
    # 1. Verify the assertion with Steam
    verify_params = params.copy()
    verify_params["openid.mode"] = "check_authentication"
    
    response = requests.post(STEAM_OPENID_URL, data=verify_params)
    
    if "is_valid:true" not in response.text:
        raise HTTPException(status_code=401, detail="Steam authentication failed")
    
    # 2. Extract Steam ID from claimed_id
    # Example: https://steamcommunity.com/openid/id/76561197960435530
    claimed_id = params.get("openid.claimed_id", "")
    match = re.search(r"id/(\d+)", claimed_id)
    if not match:
        raise HTTPException(status_code=400, detail="Could not extract Steam ID")
    
    steam_id = match.group(1)
    
    # 3. Fetch user profile from Steam API (optional but recommended)
    username = None
    avatar_url = None
    
    if settings.steam_api_key:
        try:
            profile_url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={settings.steam_api_key}&steamids={steam_id}"
            profile_response = requests.get(profile_url).json()
            players = profile_response.get("response", {}).get("players", [])
            if players:
                player = players[0]
                username = player.get("personaname")
                avatar_url = player.get("avatarfull")
        except Exception as e:
            logger.error(f"Error fetching Steam profile: {e}")
    
    # 4. Create or update user in database
    user = UserRepository.get_user_by_steam_id(db, steam_id)
    if user:
        user = UserRepository.update_user(db, steam_id, username, avatar_url)
    else:
        user = UserRepository.create_user(db, steam_id, username, avatar_url)
    
    # 5. Set user in session
    request.session["user_id"] = user.steam_id
    
    # 6. Redirect to frontend
    return RedirectResponse(f"{settings.frontend_url}/portfolio")

@router.get("/me", response_model=Optional[UserResponse])
async def get_me(request: Request, db: Session = Depends(get_db)):
    """Get current logged-in user"""
    steam_id = request.session.get("user_id")
    if not steam_id:
        return None
    
    user = UserRepository.get_user_by_steam_id(db, steam_id)
    return user

@router.post("/logout")
async def logout(request: Request):
    """Log out the current user"""
    request.session.clear()
    return {"message": "Logged out successfully"}
