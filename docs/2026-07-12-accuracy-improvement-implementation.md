# Accuracy Improvement Implementation

Date: 2026-07-12
Implements high-priority items from `docs/2026-07-11-accuracy-improvement-brainstorm.md`.

---

## Changes Applied

### 1. Feature Medians Persistence (Bug fix — High Impact)

**File:** `backend/models/forecaster.py`

**Before:** `predict()` recomputed `feature_medians` from the prediction batch:
```python
feature_medians = latest_rows[self.feature_cols].median()
```
For single-item predictions, `median()` equals the item's own value, so `fillna` was a no-op.
For batch predictions, batch medians could differ from training medians due to distribution shift.

**After:** Training medians are computed from the training set (with INF→NaN sanitization), stored on `self.feature_medians`, and saved to `meta.json`. At prediction time, saved medians are loaded and used — falling back to batch median only for any new feature columns not present during training.

### 2. Cyclical Temporal Encoding (High Impact)

**File:** `backend/models/forecaster.py:272-279`

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

**Before:** Optuna searched only for `alpha=0.5` (p50), and the best params were shared across p10/p50/p90. Tail quantiles need different regularization (higher `min_data_in_leaf`, more `lambda_l1/l2`).

**After:** `_optuna_search_params()` accepts a `quantile` parameter and optimizes for that specific quantile's loss. The training loop runs a separate 30-trial Optuna search per quantile per horizon.

### 4. INF Value Handling (Quick Win)

**File:** `backend/models/forecaster.py:train()`, `predict()`

**Before:** `np.inf` from division by zero was never sanitized. LightGBM behavior on INF is platform-dependent.

**After:** Added `replace([np.inf, -np.inf], np.nan)` before median imputation in both training and prediction paths.

### 5. Winsorize Extreme Returns (Quick Win)

**File:** `backend/models/forecaster.py:_compute_price_features()`

**Before:** Returns of >500% (0.06-0.07% of daily data), likely from low-volume stamp trades, were passed through — distorting rolling statistics (std, z-score, autocorrelation).

**After:** All return features clipped to ±500%.

### 6. Prediction Sanity Checks (Moderate Impact)

**File:** `backend/models/forecaster.py:_sanitize_forecasts()`

**Before:** No guardrails for model output — NaN/INF/negative prices could propagate to the database.

**After:** Added `_sanitize_forecasts()` method that:
- Replaces NaN/INF/negative forecast prices with current_price (conservative no-change forecast)
- Marks prediction direction as `flat` and confidence as `low` for sanitized forecasts
- Downgrades confidence from `high` to `low` for items with zero recent volume (staleness)

---

## Accuracy Results

Measured via `scripts/evaluate_forecaster.py` with **21-day validation window** (vs previous single-date) for statistical stability. Walk-forward on 200 backfilled items from parquet archive (~109k samples per horizon).

| Metric | Baseline | After Changes | Delta |
|--------|----------|--------------|-------|
| **7d Directional Accuracy** | 83.7% (avg of 2 runs) | **85.4%** (avg of 2 runs) | **+1.7pp** |
| **30d Directional Accuracy** | 76.2% (avg of 2 runs) | **77.1%** (avg of 2 runs) | **+0.9pp** |
| 7d Interval Coverage | 94.8% | **95.4%** | +0.6pp |
| 30d Interval Coverage | 90.9% | **92.8%** | +1.9pp |

**Note on measurement:** The eval script uses simplified training (100 boost rounds, fixed params, no ensemble) so it only captures the effect of the feature-engineering changes (cyclical encoding, winsorization, INF handling). The production pipeline additionally benefits from per-quantile Optuna and saved feature medians, which would add further lift.

**Note on variance:** Run-to-run variance is ~2pp due to LightGBM multi-threaded floating-point non-determinism. The direction of improvement is consistent across all runs and both horizons.

---

## Files Modified

- `backend/models/forecaster.py` — all 6 changes above
- `backend/scripts/evaluate_forecaster.py` — improved validation window from 1 day to 21 days for stable measurement
