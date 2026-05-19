"""
Seed data and database initialization
Populates initial data for testing and demonstration
"""

from datetime import datetime, timedelta
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Sample CS2 market items
SAMPLE_ITEMS = [
    {
        'item_id': 'ak47-phantom-mw',
        'name': 'AK-47 | Phantom Disruptor',
        'type': 'skin',
        'release_date': datetime(2020, 5, 1)
    },
    {
        'item_id': 'dragon-lore-factory',
        'name': 'Dragon Lore',
        'type': 'skin',
        'release_date': datetime(2013, 1, 1)
    },
    {
        'item_id': 'cs2-weapon-case',
        'name': 'CS2 Weapon Case',
        'type': 'case',
        'release_date': datetime(2023, 9, 1)
    },
    {
        'item_id': 'sticker-navi',
        'name': 'Navi Sticker',
        'type': 'sticker',
        'release_date': datetime(2022, 5, 15)
    },
    {
        'item_id': 'deagle-crimson-web',
        'name': 'Desert Eagle | Crimson Web',
        'type': 'skin',
        'release_date': datetime(2014, 1, 21)
    },
    {
        'item_id': 'karambit-doppler',
        'name': 'Karambit | Doppler',
        'type': 'skin',
        'release_date': datetime(2015, 1, 6)
    },
    {
        'item_id': 'm4a1-hyper',
        'name': 'M4A1-S | Hyper Beast',
        'type': 'skin',
        'release_date': datetime(2015, 2, 1)
    },
    {
        'item_id': 'awp-dragon-lore',
        'name': 'AWP Dragon Lore',
        'type': 'skin',
        'release_date': datetime(2013, 1, 1)
    },
]

# Sample market events
SAMPLE_EVENTS = [
    {
        'type': 'major',
        'timestamp': datetime.utcnow() - timedelta(days=60),
        'description': 'PGL Major Stockholm 2024'
    },
    {
        'type': 'case_drop',
        'timestamp': datetime.utcnow() - timedelta(days=45),
        'description': 'New weapon case added to drop pool'
    },
    {
        'type': 'operation',
        'timestamp': datetime.utcnow() - timedelta(days=30),
        'description': 'Operation Breakout started'
    },
    {
        'type': 'update',
        'timestamp': datetime.utcnow() - timedelta(days=15),
        'description': 'Major balance update affecting weapon prices'
    },
    {
        'type': 'major',
        'timestamp': datetime.utcnow() - timedelta(days=7),
        'description': 'Intel Extreme Masters World Championship'
    },
]


def generate_sample_price_history(item_id: str, num_days: int = 30) -> List[Dict]:
    """
    Generate sample price history for demonstration
    
    Args:
        item_id: Item identifier
        num_days: Number of days of history to generate
        
    Returns:
        List of price data points
    """
    import random
    
    history = []
    base_price = random.uniform(10, 500)
    
    for i in range(num_days):
        timestamp = datetime.utcnow() - timedelta(days=num_days - i)
        
        # Add slight random walk
        price_change = random.uniform(-0.05, 0.05)
        base_price = base_price * (1 + price_change)
        base_price = max(1, base_price)  # Ensure positive
        
        history.append({
            'item_id': item_id,
            'timestamp': timestamp,
            'price': round(base_price, 2),
            'volume': random.randint(50, 5000),
            'median_price': round(base_price * 0.95, 2)
        })
    
    return history


class DatabaseSeeder:
    """Seeds database with initial data"""
    
    @staticmethod
    def seed_items(session) -> int:
        """
        Seed items table with sample data
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            Number of items seeded
        """
        from database import Item
        
        try:
            # Check if items already exist
            existing_count = session.query(Item).count()
            if existing_count > 0:
                logger.info(f"Items table already has {existing_count} items, skipping seed")
                return 0
            
            items = []
            for item_data in SAMPLE_ITEMS:
                item = Item(**item_data)
                items.append(item)
            
            session.add_all(items)
            session.commit()
            
            logger.info(f"Seeded {len(items)} items")
            return len(items)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding items: {e}")
            return 0
    
    @staticmethod
    def seed_events(session) -> int:
        """
        Seed events table with sample data
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            Number of events seeded
        """
        from database import Event
        
        try:
            # Check if events already exist
            existing_count = session.query(Event).count()
            if existing_count > 0:
                logger.info(f"Events table already has {existing_count} events, skipping seed")
                return 0
            
            events = []
            for event_data in SAMPLE_EVENTS:
                event = Event(**event_data)
                events.append(event)
            
            session.add_all(events)
            session.commit()
            
            logger.info(f"Seeded {len(events)} events")
            return len(events)
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding events: {e}")
            return 0
    
    @staticmethod
    def seed_price_history(session) -> int:
        """
        Seed price history with sample data
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            Number of price history records seeded
        """
        from database import Item, PriceHistory
        
        try:
            # Check if price history exists
            existing_count = session.query(PriceHistory).count()
            if existing_count > 0:
                logger.info(f"PriceHistory table already has {existing_count} records, skipping seed")
                return 0
            
            items = session.query(Item).all()
            total_added = 0
            
            for item in items:
                history_data = generate_sample_price_history(item.item_id)
                
                for record in history_data:
                    price_history = PriceHistory(
                        item_id=item.id,
                        timestamp=record['timestamp'],
                        price=record['price'],
                        volume=record['volume'],
                        median_price=record.get('median_price')
                    )
                    session.add(price_history)
                    total_added += 1
            
            session.commit()
            logger.info(f"Seeded {total_added} price history records")
            return total_added
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding price history: {e}")
            return 0
    
    @staticmethod
    def seed_all(session) -> Dict[str, int]:
        """
        Seed all tables with initial data
        
        Args:
            session: SQLAlchemy session
            
        Returns:
            Dictionary with counts of seeded records
        """
        logger.info("Starting database seeding...")
        
        results = {
            'items': DatabaseSeeder.seed_items(session),
            'events': DatabaseSeeder.seed_events(session),
            'price_history': DatabaseSeeder.seed_price_history(session)
        }
        
        logger.info(f"Database seeding completed: {results}")
        return results
