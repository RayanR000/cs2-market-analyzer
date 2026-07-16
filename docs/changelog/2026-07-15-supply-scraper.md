# Supply Scraper (Steam sell_listings + forecaster depth features)

**Date:** 2026-07-15

## Summary

Added a daily supply scraper that captures sell_listings from the Steam Market, plus supply-depth features in the forecaster. Also dropped Skinport as a source (now 403/Cloudflare).

## Changes

### New files

- **`backend/collectors/supply_scraper.py`** — Burst-limited Steam Market scraper. Paginates the full 34K-item catalog at 10 items/page using burst rate limiting (20 rapid requests → 30s pause). Tracks ~5.5K items for supply snapshots.
- **`backend/scripts/run_supply_scraper.py`** — CLI entry point for the daily run.
- **`.github/workflows/supply-scraper.yml`** — Daily workflow at 22:00 UTC (1h before aggregator), 120-min timeout.
- **`backend/migrations/versions/0016_add_supply_snapshots.py`** — Alembic migration for `supply_snapshots` table.

### Modified files

- **`backend/database.py`** — Added `SupplySnapshot` model (`item_id`, `snapshot_date`, `sell_listings`, `skinport_quantity`, `source`, `created_at`). Composite PK on `(item_id, snapshot_date)`.
- **`backend/models/forecaster.py`** — Added `_fetch_supply_snapshots()`, `_add_supply_depth_features()`. Features: `supply_listings_log` (log1p), `supply_zscore_30d`, `supply_change_7d`, `supply_to_volume_ratio`. Wired into `build_training_data()` and `predict()`.
- **`backend/scripts/run_task.py`** — Added `supply_scrape` task.

### Data assets

- **`supply_snapshots` table** — 35,037 rows seeded from `market_catalog.db` (one-time backfill of existing sell_listings data).

### Source removals

- **Skinport** — Direct API (`/v1/items`) is behind Cloudflare Bot Management (403). Removed from `supply_scraper.py`. The column `skinport_quantity` remains in the schema (already migrated) but is always NULL.

## Architecture

```
Steam Market search/render (burst 20×30s)
        │
        ▼
SupplyScraper.scrape_steam() → {hash_name: sell_listings}
        │
        ▼
SupplyScraper.store_snapshots() → supply_snapshots (Supabase)
        │
        ▼
Forecaster._fetch_supply_snapshots() → pandas DF
        │
        ▼
Forecaster._add_supply_depth_features()
  ├─ supply_listings_log     — log(1 + sell_listings)
  ├─ supply_zscore_30d        — 30-day z-score of log-listings
  ├─ supply_change_7d         — 7-day % change
  └─ supply_to_volume_ratio   — listings / 7d avg volume
```

## Rate limiting

| Metric | Value |
|--------|-------|
| Items per page | 10 (Steam hard limit) |
| Burst size | 20 rapid requests |
| Pause after burst | 30s |
| Total pages for 34K items | ~3,400 |
| Estimated time | ~115 min |
| Workflow timeout | 120 min |

## Performance notes

- Steam `search/render` ignores `count` param; always returns 10 items.
- No query filtering — must paginate whole catalog; can't target specific items.
- Supply depth features require 7-30 days of accumulated snapshots before change/zscore features become informative. Initial backfill from `market_catalog.db` provides the baseline.

## Remaining

- **Historical supply backfill** — The existing `market_catalog.db` has one snapshot from July 4. Full backfill needs 7+ daily runs to produce useful change features.
- **Skinport alternative** — No replacement found. CSFloat API requires auth.
