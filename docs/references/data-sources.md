# Data Source Audit & Plan

## Current Sources

| Source | Type | Interval | Freshness | Auth | Status |
|---|---|---|---|---|---|
| CSGOTrader aggregator | JSON API | Every 6h | 24h avg of Steam sales (stale) | None | **Active (primary)** |
| skins.ai catalog | JSON API (bulk) | Every 6h | Edge-cached ~5–60m best cross-market listing price | None | **Active (additional source)** |
| Steam Market (scraped) | Web scrape | Daily | Live snapshot but rate-limited | Cookies (for pricehistory) | **Active (secondary)** |
| Steam Market supply scraper | Burst scrape | Daily | Live sell_listings count (burst-limited) | None | **Active** |
| CSFloat API | REST API | Not running | Live listings | API key not configured | **Degraded** |
| Steam Web API | REST API | Manual only | Item schema/icons | STEAM_API_KEY | **Active (manual)** |
| Skinport (via aggregator) | JSON API | Every 6h | Broken — reads wrong keys (`last_24h` instead of `starting_at`) | None | **Broken** |
| Skinport (direct API) | REST API | N/A | Cloudflare 403 — unavailable server-side | None | **Dead** |
| cs2.sh archive | API stub | N/A | Not implemented | CS2SH_API_KEY | **Stub** |
| Steam Announcements | Stub | N/A | Not implemented | None | **Stub** |
| Synthetic demo | Generated | Dev only | Fake | None | **Dev only** |
| Steam `priceoverview` | Undocumented endpoint | Per-item | 24h sales volume, lowest/median price | None | **Not integrated** |
| CSMarketCap API | GraphQL + REST | Bulk (all items in 1 call) | Trade volume (24h/7d/30d/90d), listings, buy orders | JWT token | **Not integrated** ($9.99/mo) |

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

## skins.ai (additional price source)

**Added 2026-07-16.** Free, no-key, no-cookie bulk price source. Intended as a *parallel* source that flows into the Parquet archive alongside CSGOTrader — **not** a replacement.

- **Source:** `skins.ai/api/item-names` (public, no auth) — one call returns the full catalog (~8,000 items: `n` name, `s` slug, `g` game, `p` best cross-market price).
- **What it returns:** the best *listing* price across markets (cross-market), **not** the Steam sale price. Liquidity field `dvol30d` exists but no daily volume, so `volume` is written as `0` in the snapshot.
- **Matching:** exact name → base name (wear/variant stripped) → slug fallback. Knives are listed without the `★` prefix and stickers carry their `(Holo)/(Gold)` variants, so `StatTrak`/`★`/`Souvenir` prefixes and wear suffixes are stripped before lookup.
- **Coverage:** ~57% of the ~8.7K tracked items match (knives/stickers/cases partially covered; the free catalog is a subset). Unmatched items are skipped — CSGOTrader remains the primary for those.
- **Storage:** collector writes a snapshot CSV (`item_slug, day, source=skinsai, price, volume`) consumed by `append_to_parquet.py` → `prices-YYYY.parquet` / `snapshots-YYYY.parquet` on the `data-archive` branch. The forecaster already includes any non-`historical_fallback` source in multi-source voting, so no forecaster change was needed.
- **Runner:** GitHub Actions every 6h (`skinsai-update.yml`), 60-min timeout. Migrate → `run_task.py skinsai` → checkout `data-archive` → `append_to_parquet.py --snapshot-csv` → commit/push (with `pull --rebase` to avoid clashing with the aggregator workflow).
- **Code:** `backend/collectors/skinsai_collector.py`, entry `backend/scripts/run_skinsai_collection.py`, tests `backend/tests/test_skinsai_collector.py`.

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

## Volume Data Status (audited 2026-07-16)

The Parquet archive contains **404,563 price rows with non-zero volume** from the `STEAMCOMMUNITY` source (Jan–Mar 2026 historical backfill). **Every aggregator source records `volume=0`** — the daily pipeline never collects trade volume.

| Time Period | Volume Source | Status |
|---|---|---|
| Jan–Mar 2026 | STEAMCOMMUNITY (Steam backfill) | ✅ Non-zero volume available |
| Apr–Jun 2026 | (gap) | ❌ No volume data |
| Jul 2026 onward | All aggregator sources | ❌ All zeros |
| CSMarketAPI backfill DB | `csmarketapi.db` | ❌ Not present on disk |

### Volume data sources evaluated (2026-07-16)

| Source | Cost | Bulk? | Trade Volume Fields | Coverage |
|--------|:----:|:-----:|:-------------------|:--------:|
| Steam `priceoverview` | Free | No (per-item) | 24h sales count | All Steam items |
| CSMarketCap API (Standard) | **$9.99/mo** | ✅ 1 call = all items | `last_24h/7d/30d/90d`, `avg_daily_volume` | All Steam items |
| SteamWebAPI Item Small | €15/mo | ✅ 1 call = all items | `sold24h/7d/30d/90d` | All Steam items |
| CS2Cap Pro | $79/mo | ✅ batch (1K items) | `sales_1d/7d/30d` | All items, 40+ markets |
| Pricempire Standard | $99.90/mo | No (per-item) | trade count metas | All items |
| cs2.sh Developer | $75/mo | ✅ bulk endpoint | ask_volume (listing count, not trade vol) | 6 markets |

**Verdict:** No free source provides bulk trade volume data. CSMarketCap API at $9.99/mo is the cheapest option — one API call daily returns trade volume for every item.

## Quality gaps
- Wire `data_validation.py` checks into the pipeline
- Add stale-data detection (compare timestamps)
- Stop creating fake flat-line data via historical fallback
