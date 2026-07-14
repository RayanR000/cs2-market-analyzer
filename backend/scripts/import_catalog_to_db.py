#!/usr/bin/env python3
"""Import all items from market_catalog.db into the main DB with correct types.

Reads the local Steam Market catalog (31,908 items), maps Steam's verbose
types to the simplified DB type enum (skin/sticker/graffiti/musickit/case),
inserts new items with is_backfilled=0, and fixes types on existing items.

Usage:
    python scripts/import_catalog_to_db.py          # import all catalog items
    python scripts/import_catalog_to_db.py --dry-run # preview without writing
"""

import sys
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, Item

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("import_catalog_to_db")

CATALOG_DB = Path(__file__).parent.parent / "runtime" / "market_catalog.db"


def map_steam_type(steam_type: str | None) -> str:
    """Map Steam's verbose type to the simplified DB type enum.

    Steam types encode both rarity and category (e.g. 'Mil-Spec Grade Pistol').
    We strip rarity and map by content category.
    """
    if not steam_type:
        return "skin"

    t = steam_type.lower()

    if "sticker" in t:
        return "sticker"
    if "graffiti" in t:
        return "graffiti"
    if "music kit" in t:
        return "musickit"
    if any(kw in t for kw in ["container", "key", "pass", "gift", "tag", "tool"]):
        return "case"

    return "skin"


def detect_type_from_name(name: str) -> str:
    """Name-based type detection fallback for items with NULL Steam type."""
    nl = name.lower()
    if "sticker" in nl:
        return "sticker"
    if "graffiti" in nl:
        return "graffiti"
    if "music kit" in nl or "musickit" in nl:
        return "musickit"
    if any(kw in nl for kw in ["case", "capsule", "key", "pass", "gift", "tag", "tool", "operation", "souvenir package"]):
        return "case"
    return "skin"


def import_catalog(dry_run: bool = False) -> dict:
    import sqlite3

    if not CATALOG_DB.exists():
        logger.error(f"Catalog DB not found at {CATALOG_DB}")
        sys.exit(1)

    # ── 1. Read catalog items ──
    cat = sqlite3.connect(str(CATALOG_DB))
    try:
        cursor = cat.execute(
            "SELECT hash_name, name, type, icon_url, classid FROM market_items"
        )
        catalog_rows = cursor.fetchall()
    finally:
        cat.close()

    logger.info(f"Read {len(catalog_rows):,} items from market_catalog.db")

    # ── 2. Load existing DB items ──
    db = SessionLocal()
    try:
        existing = db.query(Item).all()
        existing_by_id = {item.item_id: item for item in existing}
        logger.info(f"Loaded {len(existing_by_id):,} existing DB items")

        # ── 3. Map types and build insert/update batch ──
        type_fix_counts: dict[str, int] = {}
        new_items: list[Item] = []
        update_items: list[Item] = []
        type_mismatches = 0

        for hash_name, name, steam_type, icon_url, classid in catalog_rows:
            mapped_type = map_steam_type(steam_type)
            if mapped_type == "skin" and steam_type is None:
                mapped_type = detect_type_from_name(name)

            item_id = hash_name

            existing_item = existing_by_id.get(item_id)
            if existing_item:
                # Fix type if catalog has better data and DB has generic "skin"
                if steam_type is not None and existing_item.type == "skin" and mapped_type != "skin":
                    existing_item.type = mapped_type
                    update_items.append(existing_item)
                    type_mismatches += 1
                    type_fix_counts[mapped_type] = type_fix_counts.get(mapped_type, 0) + 1
            else:
                item = Item(
                    item_id=item_id,
                    name=name,
                    type=mapped_type,
                    icon_url=icon_url or "",
                    classid=classid,
                    is_backfilled=0,
                )
                new_items.append(item)

        # ── 4. Apply changes ──
        if dry_run:
            logger.info("─── DRY RUN ───")
            logger.info(f"Would create {len(new_items):,} new items")
            logger.info(f"Would update {len(update_items):,} existing item types")
            logger.info(f"  Fix distribution: {dict(sorted(type_fix_counts.items()))}")
            logger.info(f"Total DB items after import: {len(existing) + len(new_items):,}")
        else:
            for item in new_items:
                db.add(item)
            db.commit()

            for item in update_items:
                db.add(item)
            db.commit()

            logger.info(f"Created {len(new_items):,} new items (is_backfilled=0)")
            logger.info(f"Updated {len(update_items):,} existing item types")
            if type_fix_counts:
                logger.info(f"  Type fix distribution: {dict(sorted(type_fix_counts.items()))}")
            logger.info(f"Total DB items: {len(existing) + len(new_items):,}")

        return {
            "existing": len(existing),
            "new": len(new_items),
            "updated": len(update_items),
            "type_mismatches_fixed": type_mismatches,
            "type_fix_counts": type_fix_counts,
        }

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import market catalog items into main DB"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    result = import_catalog(dry_run=args.dry_run)
    logger.info("Done.")


if __name__ == "__main__":
    main()
