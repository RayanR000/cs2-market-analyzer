#!/usr/bin/env python3
"""
Consolidate Kaggle CS:GO price data into importable format.

The downloaded Kaggle dataset has individual CSV files for each item.
This script combines them into a single CSV for import.

Usage:
    python scripts/consolidate_kaggle_prices.py --source data/items --output data/consolidated_prices.csv
"""

import sys
import csv
import logging
from pathlib import Path
from urllib.parse import unquote
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def consolidate_prices(source_dir: str, output_file: str, limit: int = None) -> int:
    """
    Consolidate individual item price CSVs into single file.

    Args:
        source_dir: Directory containing item CSV files
        output_file: Output CSV file path
        limit: Limit number of records (None = unlimited)

    Returns:
        Number of records consolidated
    """
    source_path = Path(source_dir)
    if not source_path.exists():
        logger.error(f"Source directory not found: {source_path}")
        return 0

    # Get all CSV files
    csv_files = list(source_path.glob("*.csv"))
    logger.info(f"Found {len(csv_files)} item files")

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_records = 0
    skipped_items = 0
    skipped_records = 0

    with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=['item_name', 'timestamp', 'price', 'volume', 'source']
        )
        writer.writeheader()

        for i, csv_file in enumerate(csv_files, 1):
            try:
                # Decode item name from filename
                item_name = unquote(csv_file.stem)

                # Skip if item name doesn't exist in database
                # (This check would be done properly in the import script)
                if not item_name or item_name.startswith('_'):
                    skipped_items += 1
                    continue

                logger.debug(f"Processing {i}/{len(csv_files)}: {item_name}")

                # Read item's price history
                with open(csv_file, 'r', encoding='utf-8') as infile:
                    reader = csv.DictReader(infile)

                    for row in reader:
                        try:
                            # Parse Unix timestamp
                            unix_ts = int(row.get('unix timestamp', 0))
                            if unix_ts == 0:
                                continue

                            timestamp = datetime.fromtimestamp(unix_ts).isoformat()

                            # Extract price and volume
                            price = float(row.get('price', 0))
                            volume = int(float(row.get('quantity', 0)))

                            if price <= 0:
                                skipped_records += 1
                                continue

                            # Write record
                            writer.writerow({
                                'item_name': item_name,
                                'timestamp': timestamp,
                                'price': price,
                                'volume': volume,
                                'source': 'kaggle_csgo'
                            })

                            total_records += 1

                            if limit and total_records >= limit:
                                logger.info(f"Reached limit: {limit} records")
                                break

                        except Exception as e:
                            skipped_records += 1
                            logger.debug(f"Skipped record in {item_name}: {e}")

                if limit and total_records >= limit:
                    break

                if i % 100 == 0:
                    logger.info(f"  → {i}/{len(csv_files)} items processed, {total_records} records")

            except Exception as e:
                logger.error(f"Error processing {csv_file.name}: {e}")
                skipped_items += 1

    logger.info("\n" + "="*60)
    logger.info("CONSOLIDATION COMPLETE")
    logger.info("="*60)
    logger.info(f"✓ Records consolidated: {total_records}")
    logger.info(f"⊘ Records skipped: {skipped_records}")
    logger.info(f"⊘ Items skipped: {skipped_items}")
    logger.info(f"Output: {output_path}")
    logger.info(f"\nNext: python scripts/import_historical_prices.py --source csv --file {output_file}")

    return total_records


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Consolidate Kaggle CS:GO prices')
    parser.add_argument('--source', default='data/items', help='Source directory with item CSVs')
    parser.add_argument('--output', default='data/consolidated_prices.csv', help='Output CSV file')
    parser.add_argument('--limit', type=int, help='Limit number of records (for testing)')

    args = parser.parse_args()

    total = consolidate_prices(args.source, args.output, args.limit)

    return 0 if total > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
