# Data Source Audit & Plan

> **Consolidated into `docs/references/data-sources.md`.** This file is preserved for reference but may be stale.

## Current Sources

| Source | Type | Interval | Freshness | Auth | Status |
|---|---|---|---|---|---|
| CSGOTrader aggregator | JSON API | Every 6h | 24h avg of Steam sales (stale) | None | **Active (primary)** |
| Steam Market (scraped) | Web scrape | Daily | Live snapshot but rate-limited | Cookies (for pricehistory) | **Active (secondary)** |
| CSFloat API | REST API | Not running | Live listings | API key not configured | **Degraded** |
| Steam Web API | REST API | Manual only | Item schema/icons | STEAM_API_KEY | **Active (manual)** |
| Skinport (via aggregator) | JSON API | Every 6h | Broken — reads wrong keys (`last_24h` instead of `starting_at`) | None | **Broken** |
| cs2.sh archive | API stub | N/A | Not implemented | CS2SH_API_KEY | **Stub** |
| Steam Announcements | Stub | N/A | Not implemented | None | **Stub** |
| Synthetic demo | Generated | Dev only | Fake | None | **Dev only** |

## CSGOTrader Accuracy Issues

- `steam.json` is a **rolling 24h average** of completed Steam Market sales, NOT a live price
- Lags significantly on volatile items (new cases, sticker releases, event spikes)
- `volume=0` is hardcoded in the aggregator — no way to distinguish liquid vs illiquid items
- No freshness metadata in the JSON dump — can't detect stale/failed upstream
- Skinport data merged into same dict but broken (reads `last_24h`/`price` keys that don't exist)
- `data_validation.py` has outlier/anomaly checks but they are NEVER called in the pipeline
- Historical fallback re-inserts stale prices with `timestamp=now` — downstream tools see fake fresh data

## Recommended Path Forward

**Priority: Live/fresh prices (current aggregator too stale)**

### Phase 1: Skinport API (primary live source)
- Endpoint: `GET https://api.skinport.com/v1/items?app_id=730&currency=USD`
- **No API key needed** (public)
- Rate limit: 8 req / 5 min (more than enough — one request returns entire catalog)
- Cache: 5 min on their end
- Coverage: ~13,700 currently listed items (smaller than Steam's ~34k but live)
- Returns: `min_price` (lowest listing), `mean_price`, `median_price`, `quantity`
- Required header: `Accept-Encoding: br` (Brotli)

### Phase 2: Deduplication strategy
- Only insert price row if value actually changed vs previous row
- Without dedup at 5-min intervals: ~3.9M rows/day (200GB/year — not viable)
- With dedup at 30-min intervals: ~65-130K rows/day (~10-18 MB/day, ~3.5-6.5 GB/year)
- Fits comfortably in Supabase Pro (8GB)

### Phase 3: Steam priceoverview as fallback
- Already coded in `steam_market.py:294`
- Covers items Skinport misses
- Rate-limited (~1 req/sec) — fine for gap-filling

### Items to fix in aggregator (`csgotrader_aggregator.py:150`)
- Read `starting_at` from Skinport data instead of `last_24h`
- Tag each price with its source marketplace

### Quality gaps
- Wire `data_validation.py` checks into the pipeline
- Add stale-data detection (compare timestamps)
- Stop creating fake flat-line data via historical fallback
