"""
Portfolio router for managing user inventories
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import requests
import logging
from typing import List, Dict

from database import get_db
from repositories import ItemRepository, PriceHistoryRepository
from schemas import InventoryResponse, InventoryItem

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/portfolio",
    tags=["portfolio"]
)

STEAM_INVENTORY_URL = "https://steamcommunity.com/inventory/{steam_id}/730/2?l=english&count=5000"

@router.get("/inventory", response_model=InventoryResponse)
async def get_user_inventory(request: Request, db: Session = Depends(get_db)):
    """Fetch the logged-in user's Steam inventory"""
    steam_id = request.session.get("user_id")
    if not steam_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        url = STEAM_INVENTORY_URL.format(steam_id=steam_id)
        response = requests.get(url)
        
        if response.status_code == 403:
            raise HTTPException(status_code=403, detail="Inventory is private or Steam API rate limited")
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch inventory from Steam")
        
        data = response.json()
        
        assets = data.get("assets", [])
        descriptions = data.get("descriptions", [])
        
        # Create a map for descriptions for easy lookup
        desc_map = {f"{d['classid']}_{d['instanceid']}": d for d in descriptions}
        
        inventory_items = []
        total_value = 0.0
        
        # We'll group identical items to count them
        item_counts = {}
        
        for asset in assets:
            key = f"{asset['classid']}_{asset['instanceid']}"
            if key in desc_map:
                desc = desc_map[key]
                market_hash_name = desc.get("market_hash_name")
                
                if market_hash_name not in item_counts:
                    # Slugify name to match item_id format in DB
                    item_id = market_hash_name.lower().replace(' | ', '-').replace(' ', '-')
                    item_id = ''.join(c if c.isalnum() or c == '-' else '' for c in item_id)
                    
                    # Fetch current price from our DB
                    item_db = ItemRepository.get_item_by_id(db, item_id)
                    current_price = None
                    if item_db:
                        latest_price_rec = PriceHistoryRepository.get_latest_price(db, item_db.id)
                        if latest_price_rec:
                            current_price = latest_price_rec.price
                    
                    item_counts[market_hash_name] = {
                        "id": asset["assetid"],
                        "name": desc.get("name"),
                        "market_hash_name": market_hash_name,
                        "quantity": 1,
                        "current_price": current_price,
                        "image_url": f"https://community.cloudflare.steamstatic.com/economy/image/{desc.get('icon_url')}",
                        "type": desc.get("type", "Item")
                    }
                else:
                    item_counts[market_hash_name]["quantity"] += 1
        
        for item in item_counts.values():
            inventory_items.append(InventoryItem(**item))
            if item["current_price"]:
                total_value += item["current_price"] * item["quantity"]
        
        return InventoryResponse(
            items=inventory_items,
            total_value=total_value,
            user_id=steam_id
        )
        
    except Exception as e:
        logger.error(f"Error fetching inventory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
