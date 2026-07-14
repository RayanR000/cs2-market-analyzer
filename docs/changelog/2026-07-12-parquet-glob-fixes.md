# Workflow Failure Diagnosis & Fixes — 2026-07-12

## Summary

Five workflows were failing intermittently due to DuckDB `read_parquet` glob patterns, schema incompatibilities across parquet file versions, numpy type leakage into PostgreSQL, and a missing-horizon crash in the forecaster. All six fixes are now deployed on `main` and all workflows are passing.

---

## Fix 1: `*.parquet` → `prices-*.parquet` (3 files, 4 sites)

### Symptom

```
Binder Error: Referenced column "item_slug" not found in FROM clause!
Candidate bindings: "rate"
```

### Root Cause

The `price-archive/` directory (checked out from the `data-archive` branch) contains multiple parquet file types:
- `prices-{year}.parquet` — schema: `item_slug, day, mean_price, median_price, min_price, max_price, volume, source`
- `exchange-rates-{year}.parquet` — schema: `currency, rate, day`
- `snapshots-{year}.parquet` — schema: `item_slug, day, source, price, volume`

Using `read_parquet('{dir}/*.parquet')` matches ALL parquet files. DuckDB's glob-based read uses the schema of the **alphabetically first file**. Since `exchange-rates-2026.parquet` comes before `prices-2013.parquet`, DuckDB sees only `(currency, rate, day)` and `item_slug` is invisible.

### Fix

Replace `*.parquet` with `prices-*.parquet` to match only price files.

### Files changed

| File | Line | Before | After |
|------|------|--------|-------|
| `backend/scripts/event_analyzer.py` | 63 | `{archive_dir}/*.parquet` | `{archive_dir}/prices-*.parquet` |
| `backend/scripts/long_term_trend_analyzer.py` | 63 | `{}/*.parquet` | `{}/prices-*.parquet` |
| `backend/scripts/long_term_trend_analyzer.py` | 106 | `{archive_dir}/*.parquet` | `{archive_dir}/prices-*.parquet` |
| `backend/scripts/analyze_trends.py` | 88 | `{ARCHIVE_DIR}/*.parquet` | `{ARCHIVE_DIR}/prices-*.parquet` |

---

## Fix 2: `source` column not in older parquet files

### Symptom

```
Binder Error: Referenced column "source" not found in FROM clause!
Candidate bindings: "volume"
```

### Root Cause

The parquet files were generated over time with an evolving schema. Older files (prices-2013 through prices-2022) lack the `source` column that newer files include. DuckDB's `read_parquet` with a glob union selects the schema of the first file matched. Since `prices-2013.parquet` is alphabetically first among price files, DuckDB uses its schema (no `source` column), making `WHERE source = 'STEAMCOMMUNITY'` fail.

Verified schemas on `origin/data-archive`:

| File | Has `source`? |
|------|---------------|
| `prices-2013.parquet` | ❌ |
| `prices-2026.parquet` | ✅ |

### Fix

Remove the `WHERE source = 'STEAMCOMMUNITY'` filter from the backfilled-slugs query. The parquet archive was explicitly built from STEAMCOMMUNITY backfill data, so all items in the archive are backfilled by definition. The `source` filter was redundant.

Replace the DuckDB subquery with a two-step approach: load all distinct slugs, then filter in Python.

### Files changed

| File | Change |
|------|--------|
| `backend/models/forecaster.py:62-78` | Removed `WHERE source = 'STEAMCOMMUNITY'` subquery; use `SELECT DISTINCT item_slug` without filter instead |

---

## Fix 3: Missing horizon key crash in `_sanitize_forecasts`

### Symptom

```
KeyError: 1
  cf = result_df.iloc[i]["forecasts"][h]
```

### Root Cause

When items without full model coverage (e.g., recently added items missing models for horizon 1) enter the forecast pipeline, their `forecasts` dict may lack certain horizon keys. The `_sanitize_forecasts` method used direct indexing (`forecasts[h]`) at line 817, while the adjacent code at line 810 used safe access (`.get(h, {})`). This inconsistency caused a `KeyError` when forecasts for a specific horizon were absent.

### Fix

Replace `forecasts[h]` with `forecasts.get(h)` and skip if `None`.

### Files changed

| File | Line | Before | After |
|------|------|--------|-------|
| `backend/models/forecaster.py` | 817 | `cf = result_df.iloc[i]["forecasts"][h]` | `cf = result_df.iloc[i]["forecasts"].get(h)` + `if cf is None: continue` |

---

## Fix 4: `np.float64` in PostgreSQL INSERT

### Symptom

```
psycopg2.errors.InvalidSchemaName: schema "np" does not exist
LINE 1: ..., 0.0, NULL, np.float64(23.6)...
```

### Root Cause

`numpy.float64` values from volatility/price-stability calculations were passed directly to SQLAlchemy. PostgreSQL's wire protocol stringifies them as `np.float64(...)`, which the database interprets as a reference to schema `np` with type `float64(...)`.

### Fix

Add `isinstance(value, (np.floating, np.integer)) → float(value)` conversion before inserting. The daily trend analyzer (`analyze_trends.py`) already had this conversion in `_filter_daily_analysis_row()`, but the long-term trend analyzer's `_daily_analysis_upsert()` did not.

### Files changed

| File | Change |
|------|--------|
| `backend/scripts/long_term_trend_analyzer.py:244-259` | Added numpy-to-float conversion in the upsert loop |

---

## Fix 5: Relative path in `pipeline.py`

### Symptom

```
IO Error: No files found that match the pattern "../price-archive/prices-*.parquet"
```

### Root Cause

`backend/collectors/pipeline.py:_load_parquet_histories()` used a hardcoded relative path `'../price-archive/prices-*.parquet'` instead of building an absolute path from `Path(__file__)`. This path is only correct when the working directory is `./backend`, which broke if the CWD changed.

### Fix

Replace the relative path with an absolute path computed from `Path(__file__)`, consistent with every other script in the codebase.

### Files changed

| File | Change |
|------|--------|
| `backend/collectors/pipeline.py:759,767` | Added `archive_dir = Path(__file__).parent.parent.parent / "price-archive"`; used `{archive_dir}` in the SQL string |

---

## Workflow Chain

```
23:00 UTC  Aggregator Market Update
             │
03:00 UTC  Daily Trend Analysis (── Fix 1, 4)
             │
           Price Forecast (── Fix 2, 3)
             │
           Backtest Accuracy
             │
Sun 04:00  Long-Term Trend Analysis (── Fix 1, 4)
Sun 06:00  Event Correlation Analysis (── Fix 1)
```

All workflows are passing as of `d7aea7e`.
