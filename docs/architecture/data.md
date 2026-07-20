# Data Architecture

## Motivation

Supabase has a 500 MB limit. `price_history` held 15.2M daily OHLCV rows that couldn't fit. The local `csmarketapi.db` (4.2 GB, 5,542 items, 15.2M rows) had full daily granularity but wasn't backed up. Analysis scripts needed daily data for SMA-7, momentum, event impact, and forecasts, but Supabase couldn't hold it all.

**Solution:** Move full historical data to Parquet files on the `data-archive` branch. Supabase becomes a lean serving layer. Analysis scripts read training data from local Parquet via DuckDB instead of querying Supabase over the network.

---

## Current Architecture

```
data-archive branch:
  └─ prices-YYYY.parquet    — Full daily OHLCV by year (~10-45 MB each)
  └─ snapshots-YYYY.parquet — Raw multi-source snapshots
  └─ exchange-rates-YYYY.parquet — Currency rates

Supabase (~68 MB):
  └─ items (+ is_backfilled flag)
  └─ price_history           — Stale (aggregator writes only to Parquet)
  └─ supply_snapshots        — Daily Steam sell_listings (supply scraper)
  └─ item_forecasts
  └─ events / event_impacts / event_correlations
  └─ collection_runs         — Run tracking
  └─ prediction_accuracy / forecast_outcomes / accuracy_alerts
  └─ users
```

### Data Flow

```
csmarketapi.db ──export_historical_parquet.py──▶ archive/price-archive/prices-*.parquet
                                                          │
Live aggregator ──▶ CSVs ──▶ daily Parquet append
                                                          │
HF CS2 dataset ──merge_hf_dataset.py──▶ append to prices-2026.parquet
                                          (Mar 22 – Apr 15, ~33K items)
                                                          │
Analysis scripts (DuckDB + read_parquet)
  └─ 90-day or 365-day or full history — local, ~200ms
  └─ Compute results → write to Supabase tables

API serving:
  GET /items/{id}/price-history
    ├─ days < 365  → Supabase price_history
    └─ days >= 365 → Parquet archive (via DuckDB)
```

### Storage Breakdown

| Table / File | Size | Rows | Growth |
|-------|------|------|--------|
| `items` | ~2 MB | 5,525 | Static |
| `price_history` | ~1 MB | few hundred | Stale (aggregator writes to Parquet only) |
| `supply_snapshots` | ~2 MB | 35,037 | ~11K rows/day |
| `item_forecasts` | ~8.4 MB | 10,970 | UPSERT, bounded |
| `event_correlations` | ~17 MB | 67,211 | Weekly rebuild |
| `event_impacts` | ~17 MB | 67,211 | Weekly rebuild |
| `collection_runs` | ~1 MB | ~1,000 | 1 row/day |
| `prediction_accuracy` | ~2 MB | ~5,000 | UPSERT, bounded |
| `forecast_outcomes` | ~4 MB | ~50,000 | UPSERT, bounded |
| `accuracy_alerts` | ~1 MB | ~100 | UPSERT, bounded |
| `users` | ~0.1 MB | few | Static |
| Others | ~8 MB | — | Static |
| **Supabase total** | **~68 MB** | | |
| `prices-2026.parquet` | **44.6 MB** (was 19 MB) | **4.1M** (was 2.0M) | After HF merge |
| `snapshots-2026.parquet` | **21.2 MB** (was 7.6 MB) | **3.7M** (was 1.6M) | After HF merge |

### Performance

| Operation | Before | After |
|-----------|--------|-------|
| Analysis (Actions runner) | Supabase query over network (~2-5s) | DuckDB local Parquet (~200ms) |
| API listing filter | Correlated EXISTS subquery | `is_backfilled` column index |
| Aggregator workflow | Same + pruning | Same - pruning + ~10s Parquet append |

---

## Schema Changes

### `items` table — `is_backfilled` column

```python
is_backfilled = Column(Integer, default=0)
```

Boolean flag replacing the old pattern of scanning `price_history` for `source IN ('market_csgo', 'steam_historical')` on every listing query.

### `price_history` composite PK

`(item_id, timestamp, source)` promoted to primary key. Dropped surrogate `id` bigint PK (no FKs referenced it). Freed ~80 MB index space.

### `backfilled_item_clause()` rewritten

Before: `EXISTS (SELECT 1 FROM price_history WHERE item_id=Item.id AND source IN ('market_csgo','steam_historical'))`

After: `Item.is_backfilled == True`

### Migration summary

| Migration | What it does |
|-----------|-------------|
| 0001 | Initial schema: items, price_history, daily_analysis, events |
| 0002 | Expand price_history source column, add supply_snapshots |
| 0003 | Add unique constraint on price_history, item_forecasts table |
| 0004 | Add item metadata images columns |
| 0005 | Add performance indexes |
| 0006 | Composite PK on price_history |
| 0007 | Add `is_backfilled` + create `chart_points` (later dropped) |
| 0008 | Drop redundant chart_point index, clean stale price_history rows |
| 0009-0010 | Prune and drop `trend_indicators` table |
| 0011 | Add `prediction_accuracy` table |
| 0012 | Drop `chart_points` table (data lives in Parquet) |
| 0013 | Add `accuracy_alerts` table |
| 0014 | Add `forecast_outcomes` table |
| 0015 | **Drop `daily_analysis` table** (data in Parquet + item_forecasts) |
| 0016 | Add `supply_snapshots` table |
| 0017 | Add item rarity columns |

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `export_historical_parquet.py` | One-time: csmarketapi.db → year-split Parquet files |
| `append_to_parquet.py` | Daily: append aggregator rows to current year's Parquet |
| `merge_hf_dataset.py` | One-time: Hugging Face CS2 dataset → append to 2026 Parquet |
| `build_chart_points.py` | Manual utility: Parquet → chart_points (if needed) |

### Daily aggregator run

```
GitHub Actions (23:00 UTC)
  └─ run_task.py aggregate
       ├─ Fetch all 7 sources from CSGOTraderAggregator
       ├─ Snapshots CSV → /tmp/aggregator-snapshot-{date}.csv
       ├─ Backfilled CSV → /tmp/aggregator-backfilled-{date}.csv
       └─ Record CollectionRun (no prices written to Supabase)

  └─ append_to_parquet.py
       ├─ Collapse to daily OHLCV
       ├─ Append to archive/price-archive/prices-YYYY.parquet
       └─ Also writes snapshots, exchange rates, and player counts
```

---

## Key Schema Milestones

See `docs/changelog/` for full detail. Major changes:
- **2026-07-07**: Composite PK on `price_history` promoted (`item_id, timestamp, source`), freed ~80 MB
- **2026-07-08**: Backfilled catalog (5,525 items), 1×/day collection, Parquet archive on `data-archive`
- **2026-07-08**: Dropped `trend_indicators` table, cleared stale rows (~350 MB recovered)
- **2026-07-11**: All 7 sources written to Parquet; dropped `chart_points` (freed 290 MB)
- **2026-07-16**: Dropped `daily_analysis` table (migration 0015)
- **2026-07-20**: Merged HF CS2 dataset (32K items, Mar 22 – Apr 15) into Parquet archive — filled 17 gap days, expanded 8 overlap days, 2.1M new OHLCV rows
