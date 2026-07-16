#!/usr/bin/env python3
"""
CLI entry point for the skins.ai price collection.

Collects skins.ai best cross-market prices for all tracked items and writes a
snapshot CSV (item_slug, day, source, price, volume) that the Parquet archive
pipeline consumes. Designed to be called by the skinsai-update GitHub Actions
workflow (or `python scripts/run_task.py skinsai`).

Usage:
    python scripts/run_skinsai_collection.py
    python scripts/run_skinsai_collection.py --limit 2000
"""

import sys
import csv
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from collectors.skinsai_collector import SkinsAIClient, SOURCE_LABEL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("run_skinsai_collection")


def run(limit: int = None) -> Dict:
    logger.info("=" * 60)
    logger.info("SKINSAI COLLECTION — Starting")
    if limit:
        logger.info("  Priority mode: top %s items", limit)
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        from database import Item

        if limit:
            items = db.query(Item).order_by(Item.id).limit(limit).all()
        else:
            items = db.query(Item).all()

        if not items:
            logger.warning("No items found in database")
            return {"status": "skipped", "reason": "no_items"}

        item_list = [
            {"id": i.id, "item_id": i.item_id, "name": i.name} for i in items
        ]
        logger.info("Loaded %s items from database", len(item_list))

        client = SkinsAIClient()
        result = client.collect_for_items(item_list)
        records = result["records"]

        if not records:
            logger.error("ZERO skins.ai prices matched — upstream may be down or format changed")
            return {
                "status": "failed",
                "error": "no_matches",
                "matched": 0,
                "total": result["total"],
                "unmatched": result["unmatched"],
            }

        snapshot_csv_path = None
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        csv_path = Path(f"/tmp/skinsai-snapshots-{date_str}.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["item_slug", "day", "source", "price", "volume"])
            for r in records:
                writer.writerow([r["slug"], date_str, r["source"], r["price"], 0])
        snapshot_csv_path = str(csv_path)
        logger.info("Wrote %s skins.ai rows to %s", len(records), snapshot_csv_path)

        return {
            "status": "success",
            "items_collected": len(records),
            "matched": result["matched"],
            "unmatched": result["unmatched"],
            "total": result["total"],
            "snapshot_csv_path": snapshot_csv_path,
        }
    except Exception as e:
        logger.error(f"Unhandled error: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="skins.ai price collection")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit to top N liquidity items (default: all)")
    args = parser.parse_args()

    result = run(limit=args.limit)
    print(f"RESULT: {result}")
    if result.get("status") in ("failed", "error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
