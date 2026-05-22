#!/usr/bin/env python3
"""
Scrape historical Steam Community Market prices from Wayback Machine.
Collects snapshots of market listings from archive.org.

This script:
1. Finds available snapshots for CS:GO items on Wayback Machine
2. Extracts price/volume data from each snapshot
3. Exports to CSV format for import

Usage:
    python scripts/scrape_wayback_machine.py --item "AK-47 | Phantom Disruptor" --output data/wayback_prices.csv
    python scripts/scrape_wayback_machine.py --items-file items.txt --start-year 2018 --end-year 2023
"""

import sys
import json
import csv
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WAYBACK_API = "https://archive.org/wayback/available"
STEAM_MARKET_URL = "https://steamcommunity.com/market/listings/730"


def get_wayback_snapshots(item_name: str, start_year: int = 2015, end_year: int = 2023) -> List[Dict]:
    """
    Get available Wayback Machine snapshots for a Steam market item.

    Args:
        item_name: CS:GO item name (e.g., "AK-47 | Phantom Disruptor")
        start_year: Start year for snapshots
        end_year: End year for snapshots

    Returns:
        List of snapshot metadata with timestamps and URLs
    """
    # URL encode the item name for Steam market
    encoded_name = quote(item_name)
    url = f"{STEAM_MARKET_URL}/{encoded_name}"

    try:
        # Query Wayback Machine API
        response = requests.get(
            WAYBACK_API,
            params={
                'url': url,
                'output': 'json',
                'matchType': 'prefix'
            },
            timeout=10
        )

        data = response.json()

        if 'archived_snapshots' not in data or not data['archived_snapshots']:
            logger.warning(f"No snapshots found for: {item_name}")
            return []

        snapshots = []
        for snapshot in data['archived_snapshots'].get('snapshots', []):
            timestamp = snapshot['timestamp']
            year = int(timestamp[:4])

            if start_year <= year <= end_year:
                snapshots.append({
                    'timestamp': timestamp,
                    'url': snapshot['status'],
                    'datetime': datetime.strptime(timestamp, '%Y%m%d%H%M%S')
                })

        logger.info(f"Found {len(snapshots)} snapshots for: {item_name}")
        return sorted(snapshots, key=lambda x: x['datetime'])

    except Exception as e:
        logger.error(f"Error fetching snapshots for {item_name}: {e}")
        return []


def extract_price_from_snapshot(item_name: str, timestamp: str) -> Optional[Dict]:
    """
    Extract price and volume from a Wayback Machine snapshot.

    Note: This is a simplified extraction. Full HTML parsing may be needed
    for production use.

    Args:
        item_name: Item name
        timestamp: Wayback timestamp (YYYYMMDDhhmmss format)

    Returns:
        Dict with price, volume, and timestamp, or None if extraction fails
    """
    try:
        encoded_name = quote(item_name)
        url = f"{STEAM_MARKET_URL}/{encoded_name}"

        # Wayback Machine URL format
        wayback_url = f"https://web.archive.org/web/{timestamp}/{url}"

        # Note: Full implementation would use BeautifulSoup to parse HTML
        # This is a placeholder for the concept
        logger.debug(f"Would extract from: {wayback_url}")

        return {
            'item_name': item_name,
            'timestamp': datetime.strptime(timestamp, '%Y%m%d%H%M%S').isoformat(),
            'price': None,  # Would be extracted from HTML
            'volume': None,
            'source': 'wayback_machine'
        }

    except Exception as e:
        logger.error(f"Error extracting price: {e}")
        return None


def get_popular_items() -> List[str]:
    """Return list of popular CS:GO items to sample."""
    return [
        # Weapons
        "AK-47 | Phantom Disruptor",
        "M4A4 | Uncharted",
        "AWP Dragon Lore",
        "Desert Eagle | Blaze",
        "USP-S | Orion",
        "Glock-18 | Fade",
        "Karambit | Fade",
        "M9 Bayonet | Marble Fade",
        # Stickers
        "Sticker | Natus Vincere | Katowice 2014",
        "Sticker | Team Liquid | Boston 2018",
        # Cases
        "Operation Breakout Case",
        "Chroma Case",
        "Spectrum Case"
    ]


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Scrape historical prices from Wayback Machine')
    parser.add_argument('--item', help='Single item name to scrape')
    parser.add_argument('--items-file', help='File with item names (one per line)')
    parser.add_argument('--start-year', type=int, default=2015, help='Start year for snapshots')
    parser.add_argument('--end-year', type=int, default=2023, help='End year for snapshots')
    parser.add_argument('--output', default='data/wayback_prices.csv', help='Output CSV file')
    parser.add_argument('--sample', action='store_true', help='Scrape popular items (sample)')

    args = parser.parse_args()

    # Determine items to scrape
    items = []
    if args.item:
        items = [args.item]
    elif args.items_file:
        with open(args.items_file, 'r') as f:
            items = [line.strip() for line in f if line.strip()]
    elif args.sample:
        items = get_popular_items()
    else:
        parser.print_help()
        return 1

    logger.info(f"Scraping {len(items)} items from Wayback Machine...")
    logger.info(f"Year range: {args.start_year}-{args.end_year}")

    all_snapshots = []
    for item in items:
        logger.info(f"\nProcessing: {item}")
        snapshots = get_wayback_snapshots(item, args.start_year, args.end_year)
        all_snapshots.extend(snapshots)

    if not all_snapshots:
        logger.warning("No snapshots found. Try different items or year range.")
        return 1

    # Export to CSV
    logger.info(f"\nExporting {len(all_snapshots)} snapshots to {args.output}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['item_name', 'timestamp', 'url', 'wayback_url'])
        writer.writeheader()

        for snapshot in all_snapshots:
            encoded_name = quote(snapshot.get('item_name', 'Unknown'))
            wayback_url = f"https://web.archive.org/web/{snapshot['timestamp']}/{STEAM_MARKET_URL}/{encoded_name}"

            writer.writerow({
                'item_name': snapshot.get('item_name'),
                'timestamp': snapshot['datetime'].isoformat(),
                'url': snapshot['url'],
                'wayback_url': wayback_url
            })

    logger.info(f"\n✓ Saved to: {output_path}")
    logger.info(f"\nNext steps:")
    logger.info(f"1. Review the wayback_urls in the CSV file")
    logger.info(f"2. Manually extract prices from snapshots or use web scraping")
    logger.info(f"3. Format into CSV with columns: item_name, timestamp, price, volume, source")
    logger.info(f"4. Run: python scripts/import_historical_prices.py --source csv --file data/prices.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())
