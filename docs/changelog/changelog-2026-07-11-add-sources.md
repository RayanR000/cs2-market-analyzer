# 2026-07-11: Added 3 new CSGOTrader price sources + exchange rates

## What changed

### 1. New daily data sources (`backend/collectors/csgotrader_aggregator.py`)

Added 3 new market endpoints + exchange rates, bringing the total from 4 to 7 sources:

| Source | Endpoint | Doppler phases | Items |
|---|---|---|---|
| `csmoney` | `prices.csgotrader.app/latest/csmoney.json` | ✅ | ~39,549 |
| `csgotrader` | `prices.csgotrader.app/latest/csgotrader.json` | ✅ | ~39,549 |
| `youpin` | `prices.csgotrader.app/latest/youpin.json` | ❌ | ~39,549 |

Previously: `steam` (~34k), `skinport` (~39k), `buff163` (~39k), `csfloat` (~39k)

### 2. Performance optimization (`backend/collectors/csgotrader_aggregator.py`)

`_match_item()` was rebuilding lowercase + normalized lookup dicts from scratch for every item-source pair (38,675 times). Fixed by:
- Added `_build_source_lookup()` static method — builds lookup dicts once per source
- `_match_item()` now accepts pre-built `cache_keys` and `normalized_cache_keys` instead of raw `source_data`
- `collect_batch_items()` pre-builds all lookups before the loop

**Result:** Full 5,525-item matching dropped from ~5+ minutes (timeout) to ~2 seconds.

### 3. Exchange rates (`backend/collectors/csgotrader_aggregator.py`)

- New endpoint: `prices.csgotrader.app/latest/exchange_rates.json`
- New method: `fetch_exchange_rates()` — returns `Dict[str, float]` (51 currencies + BTC/ETH)
- Fetched and written to CSV as part of daily pipeline

### 4. Source labels (`backend/collectors/pipeline.py`)

New source labels added to `SOURCE_LABELS` dict:

```python
"csmoney": "aggregator_csmoney",
"csgotrader": "aggregator_csgotrader",
"youpin": "aggregator_youpin",
```

Also added to `source_breakdown` in `CollectionRun` for monitoring.

### 5. Parquet archive (`backend/scripts/append_to_parquet.py`)

- Added `--exchange-rates-csv` argument
- Writes `exchange-rates-YYYY.parquet` keyed on `(currency, day)`

### 6. GitHub Actions (`.github/workflows/aggregator-update.yml`)

- Passes `--exchange-rates-csv /tmp/exchange-rates-$(date -u +%F).csv` to append script
- Updated commit message

## Data flow

```
CSGOTrader endpoints (7) → pipeline.run_full_aggregator_collection()
  ├── /tmp/aggregator-snapshots-{date}.csv   (all sources, all items)
  ├── /tmp/aggregator-backfilled-{date}.csv  (backfilled items only)
  └── /tmp/exchange-rates-{date}.csv         (currency rates)
         ↓
  append_to_parquet.py
  ├── price-archive/prices-YYYY.parquet       (OHLCV by item_slug/day/source)
  ├── price-archive/snapshots-YYYY.parquet    (raw snapshots by item_slug/day/source)
  └── price-archive/exchange-rates-YYYY.parquet (currency rates by currency/day)
         ↓
  data-archive git branch (daily commit)
```

## No Supabase writes

Daily data is CSV → Parquet only. The Supabase price_history write path was removed in this session.

## Benchmark results (2026-07-11)

Run against Supabase (remote PostgreSQL, 5,525 items):

| Metric | Before | After |
|---|---|---|
| API fetch time (7 endpoints) | ~3s | ~3s |
| Item matching (5,525 × 7 sources) | >5 min (timeout) | ~2s |
| Total pipeline time | >5 min | **8.1s** |
| CSV rows written | ~15k | **57,420** |
| Items matched | 4,800 (partial) | **5,504 / 5,525 (99.6%)** |

## Coverage per source (against 5,525 DB items)

| Source | Items matched | % of DB items |
|---|---|---|
| `aggregator_csgotrader` | 5,525 | 100.0% |
| `aggregator_steam_30d` | 5,525 | 100.0% |
| `aggregator_steam_90d` | 5,525 | 100.0% |
| `aggregator_steam_7d` | 5,524 | 99.98% |
| `aggregator_youpin` | 5,512 | 99.76% |
| `aggregator_skinport` | 5,438 | 98.42% |
| `aggregator_buff163` | 5,008 | 90.64% |
| `aggregator_csfloat` | 4,878 | 88.29% |
| `aggregator_buff163_buy` | 4,631 | 83.84% |
| `aggregator_csmoney` | 4,350 | 78.73% |
| `aggregator_steam` (24h) | 4,422 | 80.0% |

21 items unmatched (99.6% match rate) — mostly niche stickers and sealed graffiti.

## Parquet archive state

Files in `price-archive/` after update:

| File | Rows | Sources |
|---|---|---|
| `prices-2026.parquet` | 467,407 (57,420 new + 409,987 historical) | 11 source labels + STEAMCOMMUNITY |
| `snapshots-2026.parquet` | 57,420 | 11 source labels (raw) |
| `exchange-rates-2026.parquet` | 51 | 51 currency rates |
| `prices-2013.parquet` – `prices-2025.parquet` | ~12 years | Historical CSMarketAPI data |
