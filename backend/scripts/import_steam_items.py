#!/usr/bin/env python3
"""
Bulk import CS2 items from Steam with icons.

Uses ISteamEconomy/GetSchemaItems/v2/ with your Steam API key.
Returns all CS2 item definitions (names, classids, instanceids,
icon_url_large 512x512) in ~1 API call.

Usage:
    python scripts/import_steam_items.py
    python scripts/import_steam_items.py --limit 100   # test
    python scripts/import_steam_items.py --from-map     # apply saved mapping
    python scripts/import_steam_items.py --build-map    # build mapping from DB
    python scripts/import_steam_items.py --usage        # show API call history

Environment:
    STEAM_API_KEY    Required, from https://steamcommunity.com/dev/apikey

Rate Limits:
    Steam Web API: 100,000 calls/day
    This import uses 1-2 calls.
"""

import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from database import SessionLocal, Item

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("import_steam_items")

CLASSID_MAP_FILE = Path(__file__).parent.parent / "data" / "classid_map.json"
API_TRACKER_FILE = Path(__file__).parent.parent / "runtime" / ".steam_api_usage.json"
CDN_BASE = "https://community.cloudflare.steamstatic.com/economy/image"
SCHEMA_API_URL = "https://api.steampowered.com/ISteamEconomy/GetSchemaItems/v2/"
MAX_ITEMS_PER_CALL = 50000

# ── API call tracker ──────────────────────────────────────────────────

def _load_api_usage() -> dict:
    if API_TRACKER_FILE.exists():
        return json.loads(API_TRACKER_FILE.read_text())
    return {}

def _save_api_usage(usage: dict):
    API_TRACKER_FILE.write_text(json.dumps(usage, indent=2, sort_keys=True))

def track_api_call():
    today = time.strftime("%Y-%m-%d")
    usage = _load_api_usage()
    usage[today] = usage.get(today, 0) + 1
    _save_api_usage(usage)

def get_today_api_calls() -> int:
    return _load_api_usage().get(time.strftime("%Y-%m-%d"), 0)

def print_api_usage():
    usage = _load_api_usage()
    if not usage:
        print("No API calls recorded yet.")
        return
    today = time.strftime("%Y-%m-%d")
    total = sum(usage.values())
    print(f"Today ({today}): {usage.get(today, 0)} calls")
    print(f"All time:     {total} calls")
    print(f"\nLast 7 days:")
    dates = sorted(usage.keys(), reverse=True)[:7]
    for d in dates:
        print(f"  {d}: {usage[d]} calls")

# ── Helpers ───────────────────────────────────────────────────────────

def build_cdn_url(icon_url_hash: str) -> str:
    if not icon_url_hash:
        return ""
    return f"{CDN_BASE}/{icon_url_hash}/512fx512f"

def classify_type(name: str) -> str:
    name_lower = name.lower()
    if "sticker | " in name_lower or name_lower.startswith("sticker"):
        return "sticker"
    if any(kw in name_lower for kw in ["case", "capsule", "key", "operation", "pass"]):
        return "case"
    return "skin"

# ── Schema API ────────────────────────────────────────────────────────

def fetch_schema_page(api_key: str, start: int = 0) -> dict:
    params = {
        "key": api_key,
        "appid": 730,
        "start": start,
    }
    today_count = get_today_api_calls()
    if today_count >= 100000:
        logger.error(f"Already used {today_count}/100000 API calls today. Refusing to make more.")
        sys.exit(1)

    logger.info(f"  API calls today before this: {today_count}/100000")
    resp = requests.get(SCHEMA_API_URL, params=params, timeout=60)
    track_api_call()
    resp.raise_for_status()
    return resp.json()

def import_items_from_schema(api_key: str, limit: Optional[int] = None):
    logger.info("--- Importing items from Steam Schema API (GetSchemaItems/v2/) ---")

    all_items: list[dict] = []
    start = 0

    while True:
        data = fetch_schema_page(api_key, start)
        result = data.get("result", {})
        items = result.get("items", [])

        if not items:
            logger.warning("No items returned — API may have changed response format.")
            break

        all_items.extend(items)
        logger.info(f"  Fetched {len(items)} items (total so far: {len(all_items)})")

        if limit and len(all_items) >= limit:
            all_items = all_items[:limit]
            break

        if not result.get("more_items", 0):
            break

        start = result.get("next", start + len(items))
        time.sleep(1.0)

    logger.info(f"\nProcessing {len(all_items)} items into database...")
    db = SessionLocal()
    mapping: dict = {}
    imported = 0
    skipped = 0
    errors = 0

    try:
        for idx, schema_item in enumerate(all_items):
            market_hash_name = schema_item.get("market_hash_name") or schema_item.get("name")
            if not market_hash_name:
                errors += 1
                continue

            icon_hash = schema_item.get("icon_url_large") or schema_item.get("icon_url", "")
            icon_url = build_cdn_url(icon_hash) if icon_hash else ""

            classid = str(schema_item.get("classid", ""))
            instanceid = str(schema_item.get("instanceid", ""))
            name = schema_item.get("name", market_hash_name)
            item_type = classify_type(market_hash_name)

            mapping[market_hash_name] = {
                "classid": classid,
                "instanceid": instanceid,
                "icon_url": icon_url,
                "name": name,
                "type": item_type,
            }

            existing = db.query(Item).filter(Item.item_id == market_hash_name).first()
            if existing:
                changed = False
                if icon_url and existing.icon_url != icon_url:
                    existing.icon_url = icon_url
                    changed = True
                if classid and existing.classid != classid:
                    existing.classid = classid
                    changed = True
                if instanceid and existing.instanceid != instanceid:
                    existing.instanceid = instanceid
                    changed = True
                if changed:
                    imported += 1
                else:
                    skipped += 1
            else:
                item = Item(
                    item_id=market_hash_name,
                    name=name,
                    type=item_type,
                    icon_url=icon_url,
                    classid=classid,
                    instanceid=instanceid,
                )
                db.add(item)
                imported += 1

            if (idx + 1) % 500 == 0:
                db.commit()
                logger.info(f"  Progress: {idx + 1}/{len(all_items)} (imported={imported} skipped={skipped})")

        db.commit()
        logger.info(f"\nDONE: {imported} imported/updated, {skipped} skipped, {errors} errors (no name)")

        if mapping:
            save_classid_map(mapping)
            logger.info(f"Saved {len(mapping)} entries to data/classid_map.json")

    except KeyboardInterrupt:
        logger.info("\nInterrupted — partial data committed.")
        db.commit()
    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# ── classid_map helpers ──────────────────────────────────────────────

def load_classid_map() -> dict:
    if CLASSID_MAP_FILE.exists():
        return json.loads(CLASSID_MAP_FILE.read_text())
    return {}

def save_classid_map(mapping: dict):
    CLASSID_MAP_FILE.write_text(json.dumps(mapping, indent=2, sort_keys=True))

def apply_classid_map():
    mapping = load_classid_map()
    if not mapping:
        logger.error(f"No mapping file at {CLASSID_MAP_FILE}")
        logger.info("Run without --from-map first to build the mapping.")
        sys.exit(1)
    logger.info(f"Loaded {len(mapping)} entries from data/classid_map.json")
    db = SessionLocal()
    try:
        updated = created = skipped = 0
        for item_id, data in mapping.items():
            existing = db.query(Item).filter(Item.item_id == item_id).first()
            if existing:
                changed = False
                if data.get("icon_url") and existing.icon_url != data["icon_url"]:
                    existing.icon_url = data["icon_url"]
                    changed = True
                if data.get("classid") and existing.classid != data["classid"]:
                    existing.classid = data["classid"]
                    changed = True
                if data.get("instanceid") and existing.instanceid != data["instanceid"]:
                    existing.instanceid = data["instanceid"]
                    changed = True
                if changed:
                    updated += 1
                else:
                    skipped += 1
            else:
                item = Item(
                    item_id=item_id,
                    name=data.get("name", item_id),
                    type=data.get("type", ""),
                    icon_url=data.get("icon_url", ""),
                    classid=data.get("classid"),
                    instanceid=data.get("instanceid"),
                )
                db.add(item)
                created += 1
            if (updated + created) % 500 == 0:
                db.commit()
        db.commit()
        logger.info(f"Map applied: {created} created, {updated} updated, {skipped} skipped")
    finally:
        db.close()

def build_map_from_db():
    db = SessionLocal()
    try:
        items = db.query(Item).filter(Item.classid.isnot(None)).all()
        mapping = {}
        for item in items:
            mapping[item.item_id] = {
                "classid": item.classid,
                "instanceid": item.instanceid or "",
                "icon_url": item.icon_url or "",
                "name": item.name,
                "type": item.type or "",
            }
        save_classid_map(mapping)
        logger.info(f"Built mapping from {len(mapping)} existing DB items")
    finally:
        db.close()

# ── Migration ─────────────────────────────────────────────────────────

def run_migration():
    import subprocess
    logger.info("Running database migration...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        logger.error(f"Migration failed: {result.stderr}")
        sys.exit(1)

# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Import CS2 items from Steam Schema API"
    )
    parser.add_argument("--limit", type=int, help="Max items to import (testing)")
    parser.add_argument("--from-map", action="store_true", help="Skip API; apply data/classid_map.json to DB")
    parser.add_argument("--build-map", action="store_true", help="Build data/classid_map.json from existing DB items")
    parser.add_argument("--usage", action="store_true", help="Show API call history")
    parser.add_argument("--skip-migration", action="store_true", help="Skip alembic migration")
    args = parser.parse_args()

    if args.usage:
        print_api_usage()
        return

    if not args.skip_migration:
        run_migration()

    if args.build_map:
        build_map_from_db()
        return

    if args.from_map:
        apply_classid_map()
        return

    from config import settings
    if not settings.steam_api_key:
        logger.error("STEAM_API_KEY is not set.")
        logger.error("Add STEAM_API_KEY=your_key to backend/.env or set the environment variable.")
        sys.exit(1)

    import_items_from_schema(settings.steam_api_key, limit=args.limit)
    logger.info("Done.")


if __name__ == "__main__":
    main()
