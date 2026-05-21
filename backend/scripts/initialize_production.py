import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, SessionLocal
from collectors.csgotrader_aggregator import CSGOTraderAggregator
from database import Item
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing database schema...")
    init_db()
    
    db = SessionLocal()
    aggregator = CSGOTraderAggregator()
    
    logger.info("Fetching complete market catalog...")
    prices = aggregator.fetch_all_prices()
    
    logger.info(f"Loaded {len(prices)} items from API. Updating catalog...")
    
    # Insert items individually to gracefully skip duplicates
    count = 0
    for name in prices.keys():
        import re
        item_id = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        
        try:
            # Check existence first
            existing = db.query(Item).filter_by(item_id=item_id).first()
            if not existing:
                item = Item(item_id=item_id, name=name, type="skin")
                db.add(item)
                db.commit() # Immediate commit
                count += 1
        except Exception:
            db.rollback()
            continue
            
    logger.info(f"Updated/Added {count} items in catalog.")
    db.close()

if __name__ == "__main__":
    main()
