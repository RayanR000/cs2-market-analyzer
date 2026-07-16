# Data Architecture

## Motivation

Supabase has a 500 MB limit. `price_history` held 15.2M daily OHLCV rows that couldn't fit. The local `csmarketapi.db` (4.2 GB, 5,542 items, 15.2M rows) had full daily granularity but wasn't backed up. Analysis scripts needed daily data for SMA-7, momentum, event impact, and forecasts, but Supabase couldn't hold it all.

**Solution:** Move full historical data to Parquet files on the `data-archive` branch. Supabase becomes a lean serving layer. Analysis scripts read training data from local Parquet via DuckDB instead of querying Supabase over the network.

---

## Current Architecture

```
data-archive branch:
  └─ prices-YYYY.parquet    — Full daily OHLCV by year (~10-15 MB each)
  └─ snapshots-YYYY.parquet — Raw multi-source snapshots
  └─ exchange-rates-YYYY.parquet — Currency rates

Supabase (~70 MB):
  └─ items (+ is_backfilled flag)
  └─ price_history           — Last 7 days of aggregator snapshots
  └─ supply_snapshots        — Daily Steam sell_listings (supply scraper)
  └─ daily_analysis
  └─ item_forecasts
  └─ events / event_impacts / event_correlations
```

### Data Flow

```
csmarketapi.db ──export_historical_parquet.py──▶ archive/price-archive/prices-*.parquet
                                                         │
Live aggregator ──▶ CSVs ──▶ daily Parquet append
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

| Table | Size | Rows | Growth |
|-------|------|------|--------|
| `items` | ~2 MB | 5,525 | Static |
| `price_history` | ~1 MB | few hundred | 7-day rolling |
| `supply_snapshots` | ~2 MB | 35,037 | 35K rows/day (7 MB/day) |
| `daily_analysis` | ~1.8 MB | 4,313 | UPSERT, bounded |
| `item_forecasts` | ~8.4 MB | 10,970 | UPSERT, bounded |
| `event_correlations` | ~17 MB | 67,211 | Weekly rebuild |
| `event_impacts` | ~15 MB | 67,211 | Weekly rebuild |
| Others | ~11 MB | — | Static |
| **Total** | **~68 MB** | | |

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
| 0006 | Composite PK on price_history |
| 0007 | Add `is_backfilled` + create `chart_points` (later dropped) |
| 0008 | Drop redundant chart_point index, clean stale price_history rows |
| 0009-0010 | Prune and drop `trend_indicators` table |
| 0012 | Drop `chart_points` table (data lives in Parquet) |

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `export_historical_parquet.py` | One-time: csmarketapi.db → year-split Parquet files |
| `append_to_parquet.py` | Daily: append aggregator rows to current year's Parquet |
| `build_chart_points.py` | Manual utility: Parquet → chart_points (if needed) |

### Daily aggregator run

```
GitHub Actions (23:00 UTC)
  └─ run_task.py aggregate
       ├─ Fetch all sources from CSGOTraderAggregator
       ├─ Prices → /tmp/aggregator-backfilled-{date}.csv
       └─ Record CollectionRun

  └─ append_to_parquet.py
       ├─ Collapse to daily OHLCV
       ├─ Append to archive/price-archive/prices-YYYY.parquet
       └─ Also writes snapshots and exchange rates
```

---

## History of Changes

### 2026-07-07: Schema fix (589 MB → 392 MB)
- Drop surrogate `id` PK on `price_history`, promote `(item_id, timestamp, source)`
- Freed 80 MB pkey + 256 MB bloated unique index → 138 MB fresh PK

### 2026-07-08: Backfilled-only catalog + Parquet storage
- Catalog reduced to 5,525 backfilled items; 13,796 snapshot-tier items archived
- Collection schedule: 4×/day → 1×/day at 23:00 UTC (CSGOTrader refreshes ~21:40 UTC)
- 117,990 intraday duplicates deleted
- Daily Parquet archive on `data-archive` branch

### 2026-07-08: DB optimization (775 MB → 301 MB)
- Removed redundant `idx_chart_point_item_day` index (~100 MB)
- Deleted stale `price_history` rows for backfilled items (~350 MB)
- Dropped `trend_indicators` table (redundant with `daily_analysis`)

### 2026-07-11: Multi-source storage
- All 8 CSGOTrader sources now written to Parquet instead of just `aggregator_sync`
- Dropped `chart_points` table (freed 290 MB; data in Parquet)
- Parquet schema: `item_slug, day, source, mean_price, min_price, max_price, median_price, volume`
- Added exchange rates to archive
- Supabase: 66 MB total
