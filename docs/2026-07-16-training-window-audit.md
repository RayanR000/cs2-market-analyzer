# Training Window Audit — 2026-07-16

## Context

The forecaster claims to train on **730 days** of price history with expanding-window cross-validation, retraining weekly on Mondays. The parquet archive holds 9.9M rows across 8,691 items spanning 2013–2026.

The weekly (Monday) full retrain kept failing. This audit checked whether the model is actually training on the intended data and time frame.

## Method

Queried the parquet archive (`price-archive/prices-*.parquet`) through DuckDB, replicating the exact pipeline steps `train()` takes:

1. Filter to STEAMCOMMUNITY-backfilled items (5,542 items) — the `backfilled_only=True` filter
2. Fetch last 730 days (2024-07-16 → 2026-07-11)
3. Apply multi-source voting (collapse multiple sources per item/day to one consensus row)
4. Simulate the `train_set.tail(200_000)` sort-and-cap that happens inside `train()`
5. Report the effective date range of the capped result

## Findings

### 1. Effective training window is 51 days, not 730

| Metric | Intended | Actual (cap applied) |
|---|---|---|
| Data window | 730 days (2024-07 → 2026-07) | **2026-02-09 → 2026-07-11** |
| Distinct calendar days trained on | ~730 | **51** |
| Rows used | ~1.3M+ | 200,000 (tail only) |
| Rows dropped by cap | — | **93.1%** of voted rows |

**Root cause:** `train()` at `backend/models/forecaster.py:1207-1209`:

```python
if len(train_set) > max_rows:
    train_set = train_set.tail(max_rows)
```

`train_set` is the full 730-day feature matrix sorted by date ascending. `tail(max_rows)` keeps the *most recent* 200k rows globally (across all items). When this cap was first added, the training data fit within it (~1.3M rows → 200k tail kept ~the last quarter of calendar time). The data has since grown to 2.9M voted rows, so the same 200k cap now keeps only the last ~51 days.

### 2. Expanding-window cross-validation is silently skipped

Due to finding #1, the capped training set contains only ~51 distinct dates. `_compute_cv_splits` at `backend/models/forecaster.py:1012` requires `CV_MIN_TRAIN_DAYS = 200` distinct dates before it creates its first fold:

```python
for end in range(min_train, len(sorted_dates) - val_window + 1, step):
```

With 51 dates, `range(200, 31, 200)` is empty — zero folds. The log message `"Not enough data for CV"` fires, calibration falls back to the single 21-day split, and the fold-level metrics in the changelogs are **not being produced** on retrain.

### 3. Why the weekly retrain keeps failing

The `max_rows` cap protects **training** (per-horizon LightGBM) but not **feature engineering**. The flow in `train()` is:

```
build_training_data(days_back=730)
  ├── fetch_price_history(730d)        → 2.9M raw rows, 2.9M voted rows
  ├── engineer_features(2.9M rows)      ← EXPENSIVE: pandas groupby, rolling,
  │                                        RSI (14d rolling), MACD (ewm),
  │                                        Bollinger, 20+ lags, cross-sectional
  ├── _add_cross_sectional_features     ← groupby across all items × dates
  └── _add_supply_depth_features        ← merge supply_snapshots
        returns df with 2.9M rows × ~100 columns

for each horizon:
  prepare_targets(df)                   ← merge future price as target
  train_set.tail(200_000)               ← cap ONLY applied here (too late)
```

The expensive step (`engineer_features`) operates on **all 2.9M voted rows** before the cap. On `ubuntu-latest` (7 GB RAM, `timeout-minutes: 120` at `.github/workflows/price-forecast.yml:35`), that's consistent with OOM (exit 137) or a 120-minute timeout. The predict-only mode (Tue–Sun) skips training entirely and succeeds.

### 4. Minor: train/predict days_back mismatch

`train()` uses `days_back=730` but `predict()` uses `days_back=365` (`backend/models/forecaster.py:1365`). Benign for inference (features only need 60d lookback), but inconsistent.

## Proposed Fix

### Root cause

The cap must protect feature engineering, not just training. And it must not truncate the calendar window.

### Fix: pre-feature-engineering stratified subsample

Replace the current flow (full 2.9M → feature engineering → tail cap → training) with:

```
fetch_price_history(730d) → voted (2.9M) → subsample to ~300k rows
    spanning all 730 days → engineer_features → training → CV works
```

The subsample should preserve per-item time-series continuity for lag/rolling features to work correctly. Two approaches:

**A (Recommended): Item-stratified subsample.** Pick a deterministic random subset of items (stratified by rarity to retain knives/rare items), keep their full 730-day history for each. ~600 items × 730 days ≈ 440k rows before feature engineering → fast enough, CV enabled, per-item continuity intact.

**B: Date-stratified subsample.** All items, but sample a subset of days per item. Spans the full 730 days but breaks day-to-day continuity (lags use nearest available prior day). Works but suboptimal for time-series features.

### Additional changes

| # | Change | File | Why |
|---|---|---|---|
| 2 | Subsample **before** `engineer_features` in `build_training_data()` | `models/forecaster.py` | Bounds memory/time; fixes both the 51-day truncation and the retrain failure |
| 3 | Remove the post-hoc `train_set.tail(max_rows)` truncation | `models/forecaster.py:1207-1209` | Obsolete once pre-feature sampling is in place; keep as a safety-only `min(max_rows, len(...))` guard |
| 4 | Reconcile `predict()` days_back to 730 | `models/forecaster.py:1365` | Consistency; docs say 730-day training |
| 5 | Add regression test: assert effective training window ≥ intended days and CV folds ≥ 2 | `tests/test_forecaster.py` | Prevents silent re-truncation |
| 6 | Bump `timeout-minutes: 120 → 180` as safety margin | `.github/workflows/price-forecast.yml` | Cheap insurance even after fix |
| 7 | Verify `supply_snapshots` table is populated (needs Supabase) | — | If empty, supply-depth features are all-zero: the highest-ROI feature group delivers zero signal |

### Expected outcome after fix

- Feature engineering stays under 7 GB and finishes within 2 hours
- Training spans the full 730-day window
- Expanding-window CV produces folds → fold-level metrics + pooled-OOF calibration return
- Weekly Monday retrain succeeds
- `predict()` uses the same 730-day window for feature computation

## Key files referenced

| File | Lines | Role |
|---|---|---|
| `backend/models/forecaster.py` | 1187, 1207-1209, 1365 | `train(days_back=730)`, `tail(max_rows)` cap, `predict(days_back=365)` |
| `backend/models/forecaster.py` | 1010-1020, 1581-1599 | `_compute_cv_splits()`, `_cv_evaluate_horizon()` |
| `backend/scripts/forecast_prices.py` | 34-88 | `run_forecast()` orchestrates train/predict |
| `.github/workflows/price-forecast.yml` | 35, 72-76, 80-98 | 120-min timeout, Monday full-retrain mode, invocation |
| `docs/changelog/2026-07-11-backfilled-item-training.md` | — | Historical description of the 730-day / backfilled-only design |
