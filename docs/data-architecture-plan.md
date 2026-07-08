# Data Architecture Plan

## Problem

- Supabase is limited to 500 MB. Historical price data has been pruned (daily → weekly granularity).
- Local `csmarketapi.db` (4.2 GB, 5,542 items, 15.2M daily OHLCV rows) still has full daily granularity but isn't backed up.
- Analysis workflows need daily granularity for accurate SMA-7, momentum, event impact, and 7-day forecasts.
- Website charts need access to all-time price history.

## Solution

Move the full historical data to the `data-archive` branch as Parquet files. Supabase becomes a lean serving layer. Analysis workflows read from Parquet, write results to Supabase.

```
data-archive branch:
  └─ prices-YYYY.parquet    ← Full daily OHLCV by year (~10-15 MB each)

Supabase (~70 MB):
  └─ items (+ is_backfilled flag)
  └─ price_history           ← Last 7 days of aggregator snapshots
  └─ chart_points            ← Daily close price per item (for all-time charts)
  └─ trend_indicators
  └─ daily_analysis
  └─ item_forecasts
  └─ events / event_impacts / event_correlations
```

## Step-by-step

### 1. One-time: export csmarketapi.db → Parquet

- **Script:** `scripts/export_historical_parquet.py`
- Read `csmarketapi.db`, write year-split Parquet files to `archive/price-archive/`
- Columns: `item_slug`, `day`, `market`, `mean_price`, `min_price`, `max_price`, `median_price`, `volume`
- Commit to `data-archive` branch

### 2. Add `is_backfilled` column to items table

- Add boolean column `is_backfilled` to `items` table in Supabase
- Backfill: set `is_backfilled = TRUE` for items with CSMarketAPI history (from the Parquet data)
- Replace `backfilled_item_clause()` in `database.py` with `Item.is_backfilled == True`
- Update `database.py` — optionally keep `BACKFILLED_SOURCES` constant for backward compat

### 3. Create `chart_points` table

```sql
CREATE TABLE chart_points (
    item_id INTEGER REFERENCES items(id),
    day DATE NOT NULL,
    close FLOAT NOT NULL,
    PRIMARY KEY (item_id, day)
);
```

- **Script:** `scripts/build_chart_points.py`
- Reads Parquet files on `data-archive`, writes one daily close per item into Supabase
- ~5,500 items × ~730 days ≈ 4M rows ≈ 50 MB

### 4. Update analysis scripts to read from Parquet

Scripts that currently do `db.query(PriceHistory)...` need to switch to DuckDB + Parquet:

| File | Change |
|---|---|
| `collectors/pipeline.py` — `run_feature_computation()` | Read 90-day history from DuckDB reading `archive/prices-2026.parquet` |
| `collectors/pipeline.py` — `run_trend_analysis()` | Same |
| `scripts/analyze_trends.py` | Same |
| `scripts/long_term_trend_analyzer.py` | Read full history from multi-year Parquet files |
| `models/forecaster.py` | Same |
| `scripts/event_correlation_analyzer.py` | Same |

Pattern for each:
```python
# Before
rows = db.query(PriceHistory).filter(PriceHistory.item_id.in_(ids), ...).all()

# After
import duckdb
con = duckdb.connect()
rows = con.sql("""
    SELECT * FROM read_parquet('archive/price-archive/prices-*.parquet')
    WHERE item_id IN ?
""", [ids]).fetchall()
```

Results still write to Supabase tables (`trend_indicators`, `daily_analysis`, `item_forecasts`, etc.) — no change there.

### 5. Update aggregator workflow to append to Parquet

In `.github/workflows/aggregator-update.yml`, after `export_daily_snapshot.py`:

```yaml
- name: Append to Parquet archive
  run: python scripts/append_to_parquet.py --date $(date -u +%F) --out-dir ../archive
```

**Script:** `scripts/append_to_parquet.py`
- Reads today's aggregator rows from Supabase
- Appends to the current year's Parquet file
- Runs `build_chart_points.py` to upsert today's close into Supabase

### 6. Update API to read chart points

| Endpoint | Change |
|---|---|
| `GET /items/{id}/price-history` | Falls through to normal (reads latest 7 days from `price_history` for the "current" view). For all-time, reads `chart_points` instead of `price_history`. |
| `GET /items/{id}/prices` | When `days >= 365` or `source=historical`, read from `chart_points` instead of `price_history`. |
| `GET /items/{id}/trends` | Reads from `trend_indicators` and `daily_analysis` (already computed, no change). |

### 7. Remove or reduce pruning

- Historical pruning of `price_history` is no longer needed for Parquet-backed sources.
- `price_history` keeps only 7 days of live data (enough for "current price" display).
- `chart_points` never needs pruning (it's the durable chart source).

## Security

Historical market data is public (same as CSGOTrader/Steam). API keys stay in GitHub secrets. Supabase surface area shrinks.

## Speed

| Operation | Before | After |
|---|---|---|
| Analysis (Actions runner) | Supabase query over network (~2-5s) | DuckDB local Parquet query (~200ms) |
| API chart response | `price_history` query (~100-500ms) | `chart_points` query (~50ms) |
| Aggregator workflow | Same | Same + ~10s for Parquet append + chart_points sync |

All analysis runs faster. All API responses stay fast.

## Files to create

| File | Purpose |
|---|---|
| `scripts/export_historical_parquet.py` | One-time: csmarketapi.db → Parquet files |
| `scripts/build_chart_points.py` | Read Parquet → upsert daily close into Supabase |
| `scripts/append_to_parquet.py` | Daily: append aggregator rows to current year's Parquet |

## Files to modify

| File | Change |
|---|---|
| `backend/database.py` | Replace `backfilled_item_clause()` with `Item.is_backfilled` field |
| `backend/api/routes/items.py` | `get_price_history`/`prices`—read from `chart_points` for deep history |
| `collectors/pipeline.py` | `run_feature_computation`, `run_trend_analysis`—use DuckDB+Parquet |
| `models/forecaster.py` | Read training data from Parquet |
| `scripts/analyze_trends.py` | Read from Parquet |
| `scripts/event_correlation_analyzer.py` | Read from Parquet |
| `.github/workflows/aggregator-update.yml` | Add Parquet append step |
