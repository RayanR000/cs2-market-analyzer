# Data Source Audit & Plan

## Current Sources

| Source | Type | Interval | Freshness | Auth | Status |
|---|---|---|---|---|---|
| CSGOTrader aggregator | JSON API | Every 6h | 24h avg of Steam sales (stale) | None | **Active (primary)** |
| Steam Market (scraped) | Web scrape | Daily | Live snapshot but rate-limited | Cookies (for pricehistory) | **Active (secondary)** |
| Steam Market supply scraper | Burst scrape | Daily | Live sell_listings count (burst-limited) | None | **Active** |
| CSFloat API | REST API | Not running | Live listings | API key not configured | **Degraded** |
| Steam Web API | REST API | Manual only | Item schema/icons | STEAM_API_KEY | **Active (manual)** |
| Skinport (via aggregator) | JSON API | Every 6h | Broken — reads wrong keys (`last_24h` instead of `starting_at`) | None | **Broken** |
| Skinport (direct API) | REST API | N/A | Cloudflare 403 — unavailable server-side | None | **Dead** |
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

## Supply Scraper (Steam sell_listings)

**Added 2026-07-15.** Daily collector for supply-side data (sell_listings count).

- **Source:** `steamcommunity.com/market/search/render/` (public, no auth)
- **Strategy:** Burst scrape (20 rapid requests → 30s pause). Full catalog scan (~3,400 pages of 10 items each) → ~115 min.
- **Coverage:** 34K+ items on CS2 Steam Market, filtered to ~5.5K tracked items
- **Storage:** `supply_snapshots` table in Supabase, consumed by forecaster for supply-depth features
- **Runner:** GitHub Actions daily at 22:00 UTC (`supply-scraper.yml`), 120-min timeout
- **Code:** `backend/collectors/supply_scraper.py`, entry at `backend/scripts/run_supply_scraper.py`

### Skinport (dead)
The Skinport direct API (`/v1/items`) is now behind Cloudflare Bot Management (403 on server-side requests). Removed from the scraper. The CSGOTrader aggregator still references Skinport data but it reads the wrong JSON keys so it contributes nothing anyway.

## Deduplication strategy
- Only insert price row if value actually changed vs previous row
- Without dedup at 5-min intervals: ~3.9M rows/day (200GB/year — not viable)
- With dedup at 30-min intervals: ~65-130K rows/day (~10-18 MB/day, ~3.5-6.5 GB/year)
- Fits comfortably in Supabase Pro (8GB)

## Steam priceoverview as fallback
- Already coded in `steam_market.py:294`
- Covers items Skinport misses
- Rate-limited (~1 req/sec) — fine for gap-filling

### Items to fix in aggregator (`csgotrader_aggregator.py:150`)
- Tag each price with its source marketplace
- Skinport JSON parsing reads wrong keys (`last_24h`/`price` vs actual `starting_at`/`suggested_price`) — but Skinport is dead anyway

### Quality gaps
- Wire `data_validation.py` checks into the pipeline
- Add stale-data detection (compare timestamps)
- Stop creating fake flat-line data via historical fallback
