# Accuracy Improvement & Per-Forecast Tracking

Date: 2026-07-12

Covers three work streams:
1. Accuracy improvements from `docs/2026-07-11-accuracy-improvement-brainstorm.md`
2. Per-forecast outcome tracking (correct/wrong for every prediction)
3. Next-day (1d) forecast horizon

---

## Stream 1: Accuracy Improvements

### 1. Feature Medians Persistence (Bug fix — High Impact)

**File:** `backend/models/forecaster.py:__init__()`, `train()`, `predict()`, `save_models()`, `load_models()`

**Before:** `predict()` recomputed `feature_medians` from the prediction batch:
```python
feature_medians = latest_rows[self.feature_cols].median()
```
For single-item predictions, `median()` equals the item's own value, so `fillna` was a no-op. For batch predictions, batch medians could differ from training medians due to distribution shift.

**After:** Training medians computed with INF→NaN sanitization, stored on `self.feature_medians`, saved to `meta.json`. At prediction time, saved medians are loaded and used — falling back to batch median only for feature columns not present during training.

### 2. Cyclical Temporal Encoding (High Impact)

**File:** `backend/models/forecaster.py:_add_temporal_features()`

**Before:** `day_of_week` (0-6), `month` (1-12), `day_of_year` (1-366) stored as raw integers. LightGBM treats integers as ordinal, so Dec→Jan (12→1) looked like a gap of 11 rather than adjacency.

**After:** Added sin/cos transformations alongside raw values:
```python
df["dow_sin"] = np.sin(2 * np.pi * dow / 7)
df["dow_cos"] = np.cos(2 * np.pi * dow / 7)
df["month_sin"] = np.sin(2 * np.pi * month / 12)
df["month_cos"] = np.cos(2 * np.pi * month / 12)
df["doy_sin"] = np.sin(2 * np.pi * doy / 366)
df["doy_cos"] = np.cos(2 * np.pi * doy / 366)
```

### 3. Optuna HP Search Per Quantile (High Impact)

**File:** `backend/models/forecaster.py:_optuna_search_params()`, `train()`

**Before:** Optuna searched only for `alpha=0.5` (p50), and the best params were shared across p10/p90. Tail quantiles need different regularization.

**After:** `_optuna_search_params()` accepts a `quantile` parameter and optimizes for that specific quantile's loss. The training loop runs a separate 30-trial Optuna search per quantile per horizon.

### 4. INF Value Handling (Quick Win)

**File:** `backend/models/forecaster.py:train()`, `predict()`

**Before:** `np.inf` from division by zero was never sanitized. LightGBM behavior on INF is platform-dependent.

**After:** Added `replace([np.inf, -np.inf], np.nan)` before median imputation in both training and prediction paths.

### 5. Winsorize Extreme Returns (Quick Win)

**File:** `backend/models/forecaster.py:_compute_price_features()`

**Before:** Returns >500% (0.06-0.07% of daily data), likely from low-volume stamp trades, were passed through — distorting rolling statistics.

**After:** All return features clipped to ±500%.

### 6. Prediction Sanity Checks (Moderate Impact)

**File:** `backend/models/forecaster.py:_sanitize_forecasts()`

**Before:** No guardrails for model output — NaN/INF/negative prices could propagate to the database.

**After:** `_sanitize_forecasts()` method that:
- Replaces NaN/INF/negative forecast prices with `current_price` (conservative no-change)
- Marks direction as `flat` and confidence as `low` for sanitized forecasts
- Downgrades `high` → `low` confidence for items with zero recent volume (staleness)

---

## Stream 2: Per-Forecast Outcome Tracking

### Problem

The system computed aggregate accuracy metrics (MAE, directional accuracy %) and stored them in `prediction_accuracy`. But there was no way to see whether *individual* forecasts were correct or wrong — you couldn't ask "which predictions did the model get wrong yesterday?"

### Solution

Added a `forecast_outcomes` table — one row per forecast, written during the daily backtest when actual prices become known.

**`ForecastOutcome` model** (`backend/database.py:252-287`):

| Column | Type | Description |
|--------|------|-------------|
| `forecast_id` | FK → item_forecasts.id | Links back to the original prediction |
| `item_id` | FK → items.id | Denormalized for querying |
| `forecast_date` | Date | When the prediction was made |
| `horizon_days` | Integer | 1, 7, or 30 |
| `target_date` | Date | When the prediction is for |
| `current_price` | Float | Price at forecast time |
| `predicted_price_mid` | Float | What the model predicted |
| `actual_price` | Float | What actually happened |
| `direction_predicted` | String | up/down/flat |
| `direction_actual` | String | up/down/flat |
| `direction_correct` | Bool | Was the direction right? |
| `in_interval` | Bool (nullable) | Did actual fall in [p10, p90]? |
| `abs_error` | Float | \|predicted - actual\| |
| `pct_error` | Float | % error |
| `model_version` | String | Model that made it |

### How it's populated

Modified `backtest_forecasts()` in `backend/scripts/backtest_accuracy.py` to collect per-forecast outcome dicts alongside the existing aggregate counters. After computing aggregates, calls `_store_forecast_outcomes()` which bulk-upserts into `forecast_outcomes` (upserts by `forecast_id` so re-running backtest updates rather than duplicates).

The daily GitHub Actions workflow (`backtest-accuracy.yml`) will automatically write outcome records starting the next time it runs.

### API Endpoints

**`GET /accuracy/outcomes`** — query individual outcomes:
- `?item_id=123` — outcomes for a specific item
- `?horizon_days=1` — just 1d predictions
- `?correct=true` — only correct predictions
- `?correct=false` — only wrong predictions
- `?limit=200` — pagination (default 50, max 500)

**`GET /accuracy/outcomes/stats`** — aggregated stats across all outcomes:
- `overall_accuracy` — % of correct predictions
- `mean_abs_error` / `mean_pct_error`
- `per_horizon` — breakdown by horizon_days with accuracy, avg error per horizon

### Migration

`backend/migrations/versions/0014_add_forecast_outcomes.py` — run `alembic upgrade head` to create the table.

---

## Stream 3: Next-Day (1d) Forecast Horizon

### Change

Added `1` to the horizon list in `backend/models/forecaster.py`:
```python
# Before
HORIZONS = [7, 30]
# After
HORIZONS = [1, 7, 30]
```

### Why it works with zero other changes

All loops use `self.HORIZONS` — target preparation, feature engineering, model training, prediction output, backtest evaluation, and outcome recording all handle any horizon generically.

### Impact on training

| Aspect | Before | After |
|--------|--------|-------|
| Models trained | 18 (2 horizons × 3 quantiles × 3 ensemble) | 27 (3 × 3 × 3) |
| Optuna searches | 6 (2 × 3 quantiles) | 9 (3 × 3) |
| Est. training time | ~10 min | ~15 min |
| GHA timeout | 120 min | 120 min ✅ |

---

## Accuracy Results

Measured via `scripts/evaluate_forecaster.py` with **21-day validation window** (improved from single-date for stability). Walk-forward on 200 backfilled items from parquet archive (~109k samples per horizon).

| Metric | Baseline | After Changes | Delta |
|--------|----------|--------------|-------|
| **7d Directional Accuracy** | 83.7% | **85.4%** | **+1.7pp** |
| **30d Directional Accuracy** | 76.2% | **77.1%** | **+0.9pp** |
| 7d Interval Coverage | 94.8% | 95.4% | +0.6pp |
| 30d Interval Coverage | 90.9% | 92.8% | +1.9pp |

**Note:** The eval script uses simplified params (100 rounds, fixed HP, no ensemble) so it only captures feature-engineering improvements (cyclical encoding, winsorization, INF handling). The production pipeline additionally benefits from per-quantile Optuna, saved feature medians, and ensemble averaging.

---

## Files Changed

| File | Change |
|------|--------|
| `backend/models/forecaster.py` | 6 accuracy fixes + 1d horizon |
| `backend/scripts/forecast_prices.py` | No changes needed (uses self.HORIZONS) |
| `backend/scripts/backtest_accuracy.py` | Added `_store_forecast_outcomes()` + per-forecast recording in `backtest_forecasts()` |
| `backend/database.py` | Added `ForecastOutcome` model |
| `backend/api/routes/accuracy.py` | Added `GET /outcomes` and `GET /outcomes/stats` endpoints |
| `backend/migrations/versions/0014_add_forecast_outcomes.py` | New migration for `forecast_outcomes` table |
| `backend/scripts/evaluate_forecaster.py` | 21-day validation window for stable measurement |
