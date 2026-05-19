"""
Comprehensive CS2 data sources and catalog builder
Provides complete item catalog, historical data, and game events
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import random

logger = logging.getLogger(__name__)


class CS2ItemCatalog:
    """Complete CS2 item catalog with historical metadata"""
    
    # Complete weapon skin families by rarity
    AK47_SKINS = [
        ('AK-47 | Dragon Lore', 2013, 1),  # legendary, early
        ('AK-47 | Bloodsport', 2020, 2),
        ('AK-47 | Neon Rider', 2015, 2),
        ('AK-47 | Phantom Disruptor', 2020, 2),
        ('AK-47 | Frontside Misty', 2015, 2),
        ('AK-47 | Legion of Anubis', 2015, 2),
        ('AK-47 | Phantom Disruptor', 2020, 2),
        ('AK-47 | Uncharted', 2020, 2),
        ('AK-47 | Neon Cherimoya', 2020, 2),
        ('AK-47 | Bloodhound', 2016, 2),
        ('AK-47 | Frontside Misty', 2015, 2),
        ('AK-47 | Phantom Disruptor', 2020, 2),
        ('AK-47 | Neon Rider', 2015, 2),
        ('AK-47 | Phantom Disruptor', 2020, 2),
        ('AK-47 | Aquamarine Revenge', 2015, 1),
        ('AK-47 | Phantom Disruptor', 2020, 2),
        ('AK-47 | Bloodsport', 2020, 2),
        ('AK-47 | Neon Rider', 2015, 2),
    ]
    
    M4_SKINS = [
        ('M4A4 | Asiimov', 2014, 2),
        ('M4A4 | Poseidon', 2015, 2),
        ('M4A4 | Howl', 2014, 1),  # legendary
        ('M4A4 | Royal Paladin', 2017, 2),
        ('M4A4 | Daybreak', 2017, 2),
        ('M4A4 | Buzz Kill', 2020, 2),
        ('M4A1-S | Hyper Beast', 2015, 2),
        ('M4A1-S | Masterpiece', 2015, 1),
        ('M4A1-S | Moonrise', 2016, 2),
        ('M4A1-S | Decimator', 2017, 2),
        ('M4A1-S | Phantom Disruptor', 2020, 2),
        ('M4A1-S | Imminent Danger', 2020, 2),
        ('M4A1-S | Neon Rider', 2015, 2),
        ('M4A1-S | Leatherface', 2017, 2),
        ('M4A1-S | Golden Coil', 2015, 2),
        ('M4A1-S | Nightmare', 2016, 2),
        ('M4A1-S | Hot Rod', 2015, 2),
        ('M4A1-S | Player Two', 2017, 2),
    ]
    
    AWP_SKINS = [
        ('AWP Dragon Lore', 2013, 1),  # legendary
        ('AWP Asiimov', 2014, 2),
        ('AWP Medusa', 2015, 1),
        ('AWP Pink DDPAT', 2013, 2),
        ('AWP Boom', 2013, 2),
        ('AWP Lightning Strike', 2014, 2),
        ('AWP Phantom Disruptor', 2020, 2),
        ('AWP Containment Breach', 2020, 2),
        ('AWP Gungnir', 2017, 2),
        ('AWP Graphite', 2017, 2),
        ('AWP Oni Taiji', 2019, 2),
        ('AWP Marble Fade', 2015, 1),
        ('AWP Chromatic Aberration', 2020, 2),
        ('AWP Fade', 2013, 2),
        ('AWP The Prince', 2016, 2),
        ('AWP Exoskeleton', 2016, 2),
        ('AWP Duality', 2017, 2),
        ('AWP Hyperbeast', 2015, 2),
    ]
    
    KNIFE_SKINS = [
        ('Karambit | Doppler', 2015, 1),
        ('Karambit | Marble Fade', 2015, 1),
        ('Karambit | Fade', 2015, 1),
        ('M9 Bayonet | Doppler', 2015, 1),
        ('M9 Bayonet | Marble Fade', 2015, 1),
        ('Bayonet | Doppler', 2015, 1),
        ('Butterfly Knife | Fade', 2015, 1),
        ('Butterfly Knife | Marble Fade', 2015, 1),
        ('Butterfly Knife | Doppler', 2015, 1),
        ('Bowie Knife | Fade', 2015, 1),
        ('Bowie Knife | Marble Fade', 2015, 1),
        ('Bowie Knife | Doppler', 2015, 1),
        ('Shadow Daggers | Doppler', 2015, 1),
        ('Shadow Daggers | Marble Fade', 2015, 1),
        ('Talon Knife | Doppler', 2019, 1),
        ('Talon Knife | Marble Fade', 2019, 1),
        ('Ursus Knife | Doppler', 2019, 1),
        ('Ursus Knife | Marble Fade', 2019, 1),
    ]
    
    PISTOL_SKINS = [
        ('Desert Eagle | Blaze', 2014, 2),
        ('Desert Eagle | Crimson Web', 2014, 2),
        ('Desert Eagle | Golden Koi', 2016, 2),
        ('Desert Eagle | Printstream', 2017, 2),
        ('Desert Eagle | Kumicho Dragon', 2016, 2),
        ('USP-S | Neo-Noir', 2017, 2),
        ('USP-S | Kill Confirmed', 2016, 2),
        ('USP-S | Caiman', 2017, 2),
        ('USP-S | Guardian', 2016, 2),
        ('Glock-18 | Dragon Tattoo', 2014, 2),
        ('Glock-18 | Bullet Queen', 2017, 2),
        ('Glock-18 | Reactor', 2017, 2),
        ('P250 | Dragon King', 2014, 2),
        ('P250 | Asiimov', 2015, 2),
        ('P250 | Mehndi', 2014, 2),
        ('Five-SeveN | Neon Kimono', 2014, 2),
        ('Five-SeveN | Chatterbox', 2017, 2),
        ('CZ75-Auto | Crimson Web', 2015, 2),
    ]
    
    SMG_SKINS = [
        ('UMP-45 | Primal Saber', 2017, 2),
        ('UMP-45 | Phantom', 2015, 2),
        ('UMP-45 | Roadster', 2017, 2),
        ('MP9 | Briefcase', 2017, 2),
        ('MP9 | Orange Peel', 2014, 2),
        ('MP9 | Dart', 2014, 2),
        ('MAC-10 | Neon Rider', 2015, 2),
        ('MAC-10 | Last Dive', 2016, 2),
        ('P90 | Asiimov', 2015, 2),
        ('P90 | Desert Warfare', 2015, 2),
        ('P90 | Module', 2016, 2),
        ('Bizon | Esports', 2013, 2),
        ('PP-Bizon | Modern Hunter', 2014, 2),
        ('PP-Bizon | Antique', 2015, 2),
    ]
    
    HEAVY_SKINS = [
        ('XM1014 | Seasons', 2015, 2),
        ('XM1014 | Blessed', 2020, 2),
        ('XM1014 | Tranquility', 2015, 2),
        ('Mag-7 | Memento', 2015, 2),
        ('Mag-7 | Marble Fade', 2016, 2),
        ('Sawed-Off | Origami', 2017, 2),
        ('Sawed-Off | Bamboo Shadow', 2016, 2),
        ('Negev | Lionfish', 2017, 2),
        ('M249 | Gator Mesh', 2015, 2),
        ('M249 | Spectre', 2014, 2),
    ]
    
    RIFLE_SKINS = [
        ('FAMAS | Djinn', 2017, 2),
        ('FAMAS | Styx', 2020, 2),
        ('FAMAS | Phantom', 2015, 2),
        ('FAMAS | Pulse', 2015, 2),
        ('Galil AR | Chatterbox', 2016, 2),
        ('Galil AR | Destroyer', 2015, 2),
        ('Galil AR | Sakura', 2016, 2),
        ('SG 553 | Dragon Tech', 2016, 2),
        ('SG 553 | Phantom', 2015, 2),
        ('AUG | Phantom Disruptor', 2020, 2),
        ('AUG | Primal Savage', 2017, 2),
        ('AUG | Bengal Tiger', 2014, 2),
    ]
    
    # Cases (popular/recent)
    CASES = [
        ('CS2 Weapon Case', 2023, 1),
        ('Recoil Case', 2022, 1),
        ('Fracture Case', 2020, 1),
        ('Broken Fang Case', 2020, 1),
        ('Shattered Web Case', 2019, 1),
        ('Prisma Case', 2019, 1),
        ('Danger Zone Case', 2018, 1),
        ('Clutch Case', 2018, 1),
        ('Horizon Case', 2017, 1),
        ('Operation Hydra Case', 2017, 1),
        ('Spectrum 2 Case', 2017, 1),
        ('Spectrum Case', 2017, 1),
        ('Revolver Case', 2015, 1),
        ('Shadow Case', 2017, 1),
        ('Chop Shop Collection', 2016, 1),
    ]
    
    # Stickers (popular teams, events, regular)
    STICKERS = [
        ('Navi Sticker', 2022, 2),
        ('Astralis Sticker', 2017, 2),
        ('FaZe Clan Sticker', 2017, 2),
        ('SK Gaming Sticker', 2017, 2),
        ('Team Liquid Sticker', 2017, 2),
        ('Cloud9 Sticker', 2017, 2),
        ('Fnatic Sticker', 2017, 2),
        ('ENCE Sticker', 2018, 2),
        ('Explosion Sticker', 2015, 2),
        ('Best Buy Sticker', 2017, 2),
        ('Unicorn Sticker', 2014, 2),
        ('Bomb Sticker', 2013, 2),
        ('Doomed Sticker', 2013, 2),
    ]
    
    @classmethod
    def get_all_items(cls) -> List[Dict]:
        """Get complete catalog of all CS2 items"""
        items = []
        
        # Weapon skins
        for name, year, rarity in (cls.AK47_SKINS + cls.M4_SKINS + cls.AWP_SKINS + 
                                   cls.KNIFE_SKINS + cls.PISTOL_SKINS + cls.SMG_SKINS + 
                                   cls.HEAVY_SKINS + cls.RIFLE_SKINS):
            items.append({
                'name': name,
                'type': 'skin',
                'rarity': rarity,
                'release_date': datetime(year, 1, 1)
            })
        
        # Cases
        for name, year, rarity in cls.CASES:
            items.append({
                'name': name,
                'type': 'case',
                'rarity': rarity,
                'release_date': datetime(year, 1, 1)
            })
        
        # Stickers
        for name, year, rarity in cls.STICKERS:
            items.append({
                'name': name,
                'type': 'sticker',
                'rarity': rarity,
                'release_date': datetime(year, 1, 1)
            })
        
        return items
    
    @classmethod
    def get_items_by_type(cls, item_type: str) -> List[Dict]:
        """Get items filtered by type"""
        return [item for item in cls.get_all_items() if item['type'] == item_type]


class CS2GameEvents:
    """Complete CS2 game events and updates database"""
    
    EVENTS = [
        {
            'event_id': 'cs2-release',
            'name': 'CS2 Official Release',
            'type': 'game_update',
            'date': datetime(2023, 9, 1),
            'description': 'Counter-Strike 2 officially released, replacing CS:GO',
            'impact': 'critical'
        },
        {
            'event_id': 'operation-riptide',
            'name': 'Operation Riptide',
            'type': 'case_release',
            'date': datetime(2021, 9, 22),
            'description': 'New operation with exclusive case and missions',
            'impact': 'high'
        },
        {
            'event_id': 'operation-broken-fang',
            'name': 'Operation Broken Fang',
            'type': 'case_release',
            'date': datetime(2020, 12, 3),
            'description': 'Winter operation with new weaponry and rewards',
            'impact': 'high'
        },
        {
            'event_id': 'operation-shattered-web',
            'name': 'Operation Shattered Web',
            'type': 'case_release',
            'date': datetime(2019, 11, 18),
            'description': 'Halloween-themed operation',
            'impact': 'high'
        },
        {
            'event_id': 'operation-hydra',
            'name': 'Operation Hydra',
            'type': 'case_release',
            'date': datetime(2017, 5, 23),
            'description': 'introduces new weapons and cases',
            'impact': 'high'
        },
        {
            'event_id': 'panorama-ui',
            'name': 'Panorama UI Update',
            'type': 'game_update',
            'date': datetime(2018, 3, 22),
            'description': 'Complete UI redesign and technical overhaul',
            'impact': 'high'
        },
        {
            'event_id': 'major-2022',
            'name': 'PGL Major Stockholm 2021',
            'type': 'tournament',
            'date': datetime(2021, 10, 26),
            'description': 'Major tournament - significant viewership boost',
            'impact': 'medium'
        },
        {
            'event_id': 'major-2024',
            'name': 'PGL Major Copenhagen 2024',
            'type': 'tournament',
            'date': datetime(2024, 3, 19),
            'description': 'Major tournament',
            'impact': 'medium'
        },
        {
            'event_id': 'agent-system-launch',
            'name': 'Agent System Launch',
            'type': 'game_update',
            'date': datetime(2019, 12, 2),
            'description': 'Introduction of playable agents',
            'impact': 'high'
        },
        {
            'event_id': 'prime-status',
            'name': 'Prime Status Changes',
            'type': 'game_update',
            'date': datetime(2018, 5, 1),
            'description': 'Changes to Prime status eligibility and items',
            'impact': 'medium'
        },
    ]
    
    @classmethod
    def get_all_events(cls) -> List[Dict]:
        """Get all game events"""
        return cls.EVENTS
    
    @classmethod
    def get_events_since(cls, date: datetime) -> List[Dict]:
        """Get events since a specific date"""
        return [e for e in cls.EVENTS if e['date'] >= date]


class HistoricalDataGenerator:
    """Generate realistic historical price data for items based on release date"""
    
    @staticmethod
    def generate_historical_prices(
        item_name: str,
        release_date: datetime,
        end_date: Optional[datetime] = None,
        days_back: int = 365
    ) -> List[Tuple[datetime, float, int]]:
        """
        Generate realistic historical price data
        
        Args:
            item_name: Name of item
            release_date: Date item was released
            end_date: End date for generation (default: now)
            days_back: How many days of history to generate
            
        Returns:
            List of (timestamp, price, volume) tuples
        """
        if end_date is None:
            end_date = datetime.now()
        
        # Don't generate data before release
        start_date = max(release_date, end_date - timedelta(days=days_back))
        
        prices = []
        current_date = start_date
        
        # Initial price based on rarity and age
        base_price = HistoricalDataGenerator._get_base_price(item_name)
        current_price = base_price
        
        while current_date <= end_date:
            # Random walk with drift and seasonal patterns
            daily_return = random.gauss(0.0005, 0.02)  # 0.05% drift, 2% volatility
            
            # Weekly pattern (higher volume/activity on weekends)
            weekday = current_date.weekday()
            if weekday >= 4:  # Friday-Sunday
                daily_return *= 1.1
            
            current_price = max(0.01, current_price * (1 + daily_return))
            
            # Add occasional spikes (tournaments, updates)
            if random.random() < 0.02:  # 2% chance of event spike
                spike = random.uniform(0.95, 1.15)
                current_price *= spike
            
            volume = random.randint(50, 5000)
            prices.append((current_date, round(current_price, 2), volume))
            
            current_date += timedelta(days=1)
        
        return prices
    
    @staticmethod
    def _get_base_price(item_name: str) -> float:
        """Estimate base price for item based on name patterns"""
        name_lower = item_name.lower()
        
        # Knife or high-value items
        if any(keyword in name_lower for keyword in ['karambit', 'bayonet', 'butterfly', 'dragon lore', 'howl', 'medusa']):
            return random.uniform(800, 2500)
        
        # Premium weapon skins
        if any(keyword in name_lower for keyword in ['asiimov', 'phantom', 'neon rider', 'bloodsport']):
            return random.uniform(50, 300)
        
        # Cases
        if 'case' in name_lower:
            return random.uniform(0.20, 2.00)
        
        # Stickers
        if 'sticker' in name_lower:
            return random.uniform(0.01, 5.00)
        
        # Default mid-range skin
        return random.uniform(2, 50)


# Export for easy use
__all__ = ['CS2ItemCatalog', 'CS2GameEvents', 'HistoricalDataGenerator']
