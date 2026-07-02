#!/usr/bin/env python3
"""
Bulk import all CS2 items from Steam Community Market with images/icons.

Phase 1: Scrape market search/render (public, no API key)
  - Gets market_hash_name, classid, instanceid, icon_url
  - Rate limited: ~20 req/min, 10 items per request
  - ~34k items ≈ 3 hours (one-time cost)
  - Saves classid_map.json for future runs

Phase 2: Enrich with GetAssetClassInfo (requires STEAM_API_KEY)
  - Batches 370 classids per request
  - Gets icon_url_large, rarity colors, collection, type, inspect links
  - ~34k items → only 92 API calls ≈ 3 minutes
  - ~92 API calls used (out of 100,000/day)

Usage:
    # First run (initial bulk load):
    python scripts/import_steam_items.py

    # Subsequent runs (skip Phase 1, use saved mapping):
    python scripts/import_steam_items.py --from-map

    # Also run Phase 2 enrichment:
    python scripts/import_steam_items.py --enrich

    # Test:
    python scripts/import_steam_items.py --limit 500

    # Resume Phase 1 after interrupt:
    python scripts/import_steam_items.py --resume

Environment:
    STEAM_API_KEY  Optional, enables Phase 2 enrichment via GetAssetClassInfo

Rate Limits:
    - Steam Community Market (public, no key): 20 requests/minute
    - Steam Web API (with key): 100,000 calls/day, batch up to 370 classids/req
      https://steamcommunity.com/dev/apiterms
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

STEAM_MARKET_URL = "https://steamcommunity.com/market/search/render/"
CHECKPOINT_FILE = Path(__file__).parent / ".import_checkpoint.json"
CLASSID_MAP_FILE = Path(__file__).parent / "classid_map.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}
CDN_BASE = "https://community.cloudflare.steamstatic.com/economy/image"
BATCH_SIZE = 370  # max classids per GetAssetClassInfo call

# Adaptive rate limiting
MIN_DELAY = 3.0
MAX_DELAY = 60.0
current_delay = 3.5
consecutive_ok = 0


def rate_limit():
    global current_delay, consecutive_ok
    time.sleep(current_delay)
    if current_delay > MIN_DELAY and consecutive_ok > 10:
        current_delay = max(MIN_DELAY, current_delay - 0.5)


def handle_429():
    global current_delay, consecutive_ok
    current_delay = min(MAX_DELAY, current_delay * 2)
    consecutive_ok = 0
    logger.warning(f"Rate limited (429), backing off to {current_delay:.1f}s")


def make_request(url: str, params: dict, retries: int = 5) -> Optional[dict]:
    global consecutive_ok
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            if resp.status_code == 429:
                handle_429()
                time.sleep(current_delay * (attempt + 1))
                continue
            resp.raise_for_status()
            consecutive_ok += 1
            return resp.json()
        except requests.RequestException as e:
            logger.warning(f"Request failed (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(current_delay * (attempt + 1))
    return None


def build_cdn_url(icon_url_hash: str) -> str:
    if not icon_url_hash:
        return ""
    return f"{CDN_BASE}/{icon_url_hash}/512fx512f"


def fetch_page(start: int) -> Optional[dict]:
    params = {
        "norender": "1",
        "appid": 730,
        "start": start,
        "count": 10,
        "sort_column": "name",
        "sort_dir": "asc",
        "search_descriptions": 0,
    }
    return make_request(STEAM_MARKET_URL, params)


def get_total_count(max_retries: int = 5) -> Optional[int]:
    for attempt in range(max_retries):
        data = fetch_page(0)
        if data and "total_count" in data:
            return data["total_count"]
        logger.warning(f"Failed to get total_count (attempt {attempt+1}/{max_retries})")
    return None


def parse_item(result: dict) -> Optional[dict]:
    ad = result.get("asset_description")
    if not ad:
        return None
    market_hash_name = ad.get("market_hash_name") or result.get("hash_name")
    if not market_hash_name:
        return None
    icon_hash = ad.get("icon_url", "")
    return {
        "item_id": market_hash_name,
        "name": ad.get("name", market_hash_name),
        "type": _classify_type(market_hash_name, ad.get("type", "")),
        "icon_url": build_cdn_url(icon_hash),
        "classid": ad.get("classid"),
        "instanceid": ad.get("instanceid"),
    }


def _classify_type(name: str, type_str: str) -> str:
    name_lower = name.lower()
    if "sticker | " in name_lower or name_lower.startswith("sticker"):
        return "sticker"
    if "case" in name_lower and "case hardened" not in name_lower:
        return "case"
    if any(kw in name_lower for kw in ["capsule", "key", "operation", "pass"]):
        return "case"
    return "skin"


def save_checkpoint(offset: int, total: int, imported: int):
    CHECKPOINT_FILE.write_text(json.dumps({
        "offset": offset,
        "total": total,
        "imported": imported,
    }))


def load_checkpoint() -> Optional[dict]:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return None


def clear_checkpoint():
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def load_classid_map() -> dict:
    if CLASSID_MAP_FILE.exists():
        return json.loads(CLASSID_MAP_FILE.read_text())
    return {}


def save_classid_map(mapping: dict):
    CLASSID_MAP_FILE.write_text(json.dumps(mapping, indent=2))
    logger.info(f"Saved {len(mapping)} entries to {CLASSID_MAP_FILE.name}")


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


# ─────────────────────────────────────────────
# Phase 1: Market search pagination
# ─────────────────────────────────────────────

def import_items(limit: Optional[int] = None, resume: bool = False, classid_map: Optional[dict] = None):
    checkpoint = load_checkpoint() if resume else None
    start_offset = checkpoint["offset"] if checkpoint else 0
    previously_imported = checkpoint["imported"] if checkpoint else 0

    logger.info("Fetching total item count from Steam...")
    total = get_total_count()
    if total is None:
        logger.error("Could not determine total item count. Aborting.")
        sys.exit(1)

    if limit:
        total = min(total, limit)
    logger.info(f"Items: {total} {'(limited to ' + str(limit) + ')' if limit else ''}")

    if checkpoint:
        logger.info(f"Resuming from offset {start_offset}")

    est_hours = (total - start_offset) / 10 / 20 / 60
    logger.info(f"Estimated time: {est_hours:.1f} hours (at 20 req/min, 10 items/req)")

    db = SessionLocal()
    imported = 0
    skipped = 0
    errors = 0
    offset = start_offset
    mapping = classid_map or {}
    map_updated = False

    try:
        while offset < total:
            rate_limit()

            if offset % 200 == 0 and offset > start_offset:
                remaining = (total - offset) / 10 * current_delay / 60
                logger.info(
                    f"[{offset}/{total}] "
                    f"imported={imported} skipped={skipped} "
                    f"delay={current_delay:.1f}s ETA={remaining:.0f}min"
                )

            data = fetch_page(offset)
            if not data:
                logger.error(f"Empty response at offset {offset}, retrying...")
                time.sleep(current_delay * 2)
                continue

            results = data.get("results", [])
            if not results:
                logger.warning(f"No results at offset {offset}, may have hit the end.")
                break

            for result in results:
                parsed = parse_item(result)
                if not parsed:
                    skipped += 1
                    continue

                item_id = parsed["item_id"]

                # Update mapping
                if parsed["classid"]:
                    mapping[item_id] = {
                        "classid": parsed["classid"],
                        "instanceid": parsed["instanceid"] or "",
                        "icon_url": parsed["icon_url"],
                    }
                    map_updated = True

                existing = db.query(Item).filter(Item.item_id == item_id).first()
                if existing:
                    changed = False
                    if parsed["icon_url"] and existing.icon_url != parsed["icon_url"]:
                        existing.icon_url = parsed["icon_url"]
                        changed = True
                    if parsed["classid"] and existing.classid != parsed["classid"]:
                        existing.classid = parsed["classid"]
                        changed = True
                    if parsed["instanceid"] and existing.instanceid != parsed["instanceid"]:
                        existing.instanceid = parsed["instanceid"]
                        changed = True
                    if changed:
                        imported += 1
                    else:
                        skipped += 1
                else:
                    item = Item(
                        item_id=item_id,
                        name=parsed["name"],
                        type=parsed["type"],
                        icon_url=parsed["icon_url"],
                        classid=parsed["classid"],
                        instanceid=parsed["instanceid"],
                    )
                    db.add(item)
                    imported += 1

            offset += len(results)
            db.commit()
            save_checkpoint(offset, total, imported + previously_imported)

            # Save mapping every 500 items
            if map_updated and offset % 500 == 0:
                save_classid_map(mapping)
                map_updated = False

    except KeyboardInterrupt:
        logger.info("\nInterrupted. Resume with --resume.")
        db.rollback()
        save_checkpoint(offset, total, imported + previously_imported)
        if map_updated:
            save_classid_map(mapping)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        db.rollback()
        if map_updated:
            save_classid_map(mapping)
        raise
    finally:
        db.close()

    total_imported = imported + previously_imported
    logger.info(f"\nDONE: {total_imported} total in DB (+{imported} new/updated, {skipped} skipped)")
    if mapping:
        save_classid_map(mapping)
    clear_checkpoint()


# ─────────────────────────────────────────────
# Phase 2: Batch GetAssetClassInfo enrichment
# ─────────────────────────────────────────────
# Steam Web API daily limit: 100,000 calls.
# Batches 370 classids/request → ~92 requests for 34k items.
# ~92 of 100,000 daily calls used.

def enrich_with_api_key():
    from config import settings

    if not settings.steam_api_key:
        logger.info("No STEAM_API_KEY set. Skipping Phase 2 enrichment.")
        logger.info("Add STEAM_API_KEY=your_key to backend/.env to enable.")
        return

    api_url = "https://api.steampowered.com/ISteamEconomy/GetAssetClassInfo/v1/"
    db = SessionLocal()

    try:
        items = (
            db.query(Item)
            .filter(Item.classid.isnot(None))
            .order_by(Item.classid)
            .all()
        )

        logger.info(
            f"Enriching {len(items)} items via GetAssetClassInfo "
            f"(batch={BATCH_SIZE}/req → ~{len(items)//BATCH_SIZE+1} calls)"
        )

        enriched = 0
        errors = 0
        total_calls = 0

        # Process items in batches of BATCH_SIZE
        for batch_start in range(0, len(items), BATCH_SIZE):
            batch = items[batch_start:batch_start + BATCH_SIZE]

            params = {
                "key": settings.steam_api_key,
                "appid": 730,
                "class_count": len(batch),
            }
            for i, item in enumerate(batch):
                params[f"classid{i}"] = item.classid

            try:
                resp = requests.get(api_url, params=params, timeout=60)
                total_calls += 1
                resp.raise_for_status()
                data = resp.json()

                result = data.get("result", {})
                if not result.get("success"):
                    logger.warning(f"Batch failed (no success flag)")
                    errors += len(batch)
                    time.sleep(1)
                    continue

                for item in batch:
                    info = result.get(item.classid)
                    if not info:
                        continue

                    # Prefer icon_url_large (512x512), fall back to icon_url (128x128)
                    icon_hash = info.get("icon_url_large") or info.get("icon_url", "")
                    if icon_hash:
                        item.icon_url = build_cdn_url(icon_hash)

                    enriched += 1

                if (batch_start + 1) % (BATCH_SIZE * 5) == 0:
                    db.commit()
                    logger.info(
                        f"Enriched {min(batch_start + BATCH_SIZE, len(items))}/{len(items)} "
                        f"(API calls: {total_calls})"
                    )

                time.sleep(0.3)

            except Exception as e:
                logger.warning(f"Batch {batch_start//BATCH_SIZE + 1} failed: {e}")
                errors += len(batch)
                time.sleep(2)

        db.commit()
        logger.info(
            f"Enrichment done: {enriched} items, {errors} errors "
            f"(API calls: {total_calls}/100,000 daily limit)"
        )

    finally:
        db.close()


# ─────────────────────────────────────────────
# Map-only mode: apply classid_map.json to DB
# without re-scraping the Steam market
# ─────────────────────────────────────────────

def apply_classid_map():
    mapping = load_classid_map()
    if not mapping:
        logger.error(f"No mapping file found at {CLASSID_MAP_FILE}")
        logger.info("Run without --from-map first to build the mapping.")
        sys.exit(1)

    logger.info(f"Loaded {len(mapping)} entries from {CLASSID_MAP_FILE.name}")
    db = SessionLocal()

    try:
        updated = 0
        skipped = 0
        created = 0

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
                name = data.get("name") or item_id
                item = Item(
                    item_id=item_id,
                    name=name,
                    type=data.get("type") or _classify_type(item_id, ""),
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
    """Extract classid_map.json from existing DB items."""
    db = SessionLocal()
    try:
        items = (
            db.query(Item)
            .filter(Item.classid.isnot(None))
            .all()
        )
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


def main():
    parser = argparse.ArgumentParser(
        description="Bulk import CS2 items from Steam Community Market"
    )
    parser.add_argument("--limit", type=int, help="Max items to import (testing)")
    parser.add_argument("--resume", action="store_true", help="Resume Phase 1 from checkpoint")
    parser.add_argument("--enrich", action="store_true", help="Run Phase 2 API enrichment after import")
    parser.add_argument("--from-map", action="store_true", help="Skip market search; apply classid_map.json to DB")
    parser.add_argument("--build-map", action="store_true", help="Build classid_map.json from existing DB items")
    parser.add_argument("--skip-migration", action="store_true", help="Skip alembic migration")
    args = parser.parse_args()

    if not args.skip_migration:
        run_migration()

    if args.build_map:
        logger.info("--- Building classid_map.json from DB ---")
        build_map_from_db()
        return

    if args.from_map:
        logger.info("--- Applying classid_map.json to DB ---")
        apply_classid_map()
    else:
        logger.info("--- Phase 1: Market Search Import ---")
        classid_map = load_classid_map()
        if classid_map and not args.resume:
            logger.info(f"Loaded existing mapping ({len(classid_map)} entries)")
        import_items(limit=args.limit, resume=args.resume, classid_map=classid_map)

    if args.enrich:
        logger.info("\n--- Phase 2: GetAssetClassInfo Enrichment ---")
        enrich_with_api_key()

    logger.info("Done.")


if __name__ == "__main__":
    main()
