# Prediction Model Fixes — 2026-07-12

Addressed all 10 weaknesses identified in the prediction model audit:

## 1. 🧪 Unit Tests (foundation)
**`tests/test_forecaster.py`** — 41 tests covering every major code path:
- Feature engineering (lags, returns, Bollinger, RSI, MACD, volume, missingness)
- Temporal, event, and cross-sectional features
- Feature pruning (correlation-based)
- Target preparation (forward-looking)
- Quantile monotonicity and crossing diagnostics
- Confidence computation and fallback defaults
- Sanitization (invalid price clamping, zero-volume downgrade)
- Pipeline integration (daily resampling, end-to-end feature set)
- Concept drift detection (low/high accuracy, insufficient data)
- Calibration (min samples, per-horizon thresholds)
- Predict edge cases (empty data, insufficient history, spike detection)
- Model persistence (save/load, JSON serialization)

## 2. 🐛 CRITICAL: Target computation was inverted
**File:** `backend/models/forecaster.py:512-532`

The `prepare_targets` merge was looking up the price `horizon` days **ago** instead of `horizon` days **ahead**. The model was trained to predict past returns from current features — effectively learning that `return_7d` (a feature) equals `target_return_7d` (the target). This produced deceptively high validation accuracy because the model simply memorized that a feature equals the target, rather than learning to predict future price movements.

**Fix:** Reversed the merge direction. Each row now looks up the price at `date + horizon` (forward), using a backward date shift on the future table.

**Impact:** After retraining, the model will predict actual future returns instead of past-return extrapolation. Validation accuracy dropped from the illusory 86-88% to ~60-66% (walk-forward evaluation on fixed code, vs 50% 2-class baseline) — this is the **real** predictive accuracy, not a regression.

## 3. 📉 Prediction spike smoothing
**File:** `backend/models/forecaster.py:730-745`

`predict()` was using `groupby("item_id").last()` to get the latest price and features. A single outlier row (price spike, volume artifact) contaminated all forecasts.

**Fix:** After feature engineering, the code computes a 3-day median price per item. If the latest price deviates >10% from the 3d median, it's replaced with the smoothed value. The count of outliers is logged for monitoring.

## 4. 🔗 Name-based join fragility
**File:** `backend/scripts/forecast_prices.py:72-76`

The Parquet-to-DB slug mapping was joining on `items.name` (display name) instead of `items.item_id` (stable hash name). If item names were ever edited, forecasts would silently drop (logged as warnings).

**Fix:** Changed the query from `SELECT id, name` to `SELECT id, item_id`, matching the `item_slug` convention used in `export_daily_snapshot.py` and `build_chart_points.py`.

## 5. 🎯 Confidence calibration improved
**File:** `backend/models/forecaster.py:888-1009`

The calibration loop was optimizing for **maximum accuracy** in the "high" confidence bucket, producing 99.6% accuracy — but this covered almost no predictions (only trivial near-zero-move predictions qualified).

**Fix:** Changed to **maximize coverage subject to ≥80% accuracy**. The calibration:
1. Scans `range_pct` thresholds, picking the widest (most coverage) that meets 80% accuracy
2. Applies a `change_pct` floor to filter out trivial near-zero predictions
3. Falls back to the highest-accuracy threshold that covers ≥5% of items if 80% is unreachable

## 6. 🔄 Auto-retraining on drift
**File:** `backend/scripts/forecast_prices.py:76-92`

Concept drift monitoring existed (`check_concept_drift`) but only logged DB alerts — it never triggered retraining.

**Fix:** Before prediction in `--predict-only` mode, the script checks drift for all horizons. If any horizon has drifted below 60% accuracy (averaged over 7-day sliding window), it triggers a full retrain before generating predictions. Outside of Monday's scheduled retrain, this catches silent degradation.

## 7. 📊 Per-fold CV metrics in evaluation
**File:** `backend/scripts/evaluate_forecaster.py`

The walk-forward evaluation tracked aggregate metrics only, hiding variance across validation windows.

**Fix:** Added per-fold tracking: each 60-day expanding window now records its own directional accuracy, MAE, and interval coverage. The final report includes mean ± std across folds, min/max, and the improvement over the effective ~50% 2-class baseline (since "flat" is never the actual direction in practice).

## 8. 🎯 Better quantile crossing
**File:** `backend/models/forecaster.py:806-830` and `evaluate_forecaster.py`

The old fix (`np.minimum(p10, p50)`) collapsed prediction intervals to zero width for crossing items — losing all uncertainty information.

**Fix:** When quantiles cross, the code now imputes the **average interval half-width from well-behaved items**: the mean distance from p50 to p10/p90 among non-crossing items. This preserves a meaningful confidence interval even when individual quantile models disagree. The crossing rate and imputed width are logged.

## 9. 📈 30d horizon improvements
**File:** `backend/models/forecaster.py`

The 30d horizon underperformed in the bug-era eval (79.7% vs 86-88% for shorter horizons — both illusory due to the target inversion). After the fix, the 30d horizon actually performs **best** (65.8% vs ~60-61% for shorter horizons), likely because the longer 730d training window and new 60d rolling features give it more signal. Root causes originally identified (insufficient long-term features, too little training data) are still relevant for further improvement.

**Fixes:**
- Added 60-day rolling windows (price_mean/ std/ min/ max, volume_mean/ std)
- Added `return_60d` lag and corresponding winsorization
- Added `vol_regime_60_30`: ratio of 60d to 30d volatility (rising/falling volatility signal)
- Added `trend_divergence_30_60`: ratio of 30d return to 60d return (short-vs-long-term momentum)
- Extended training data from 365 to 730 days (~24 independent 30d cycles)

## 10. 📝 Accuracy baseline awareness
The evaluation output now explicitly states the effective ~50% 2-class baseline and reports improvement in percentage points above it. Documentation updated in `evaluate_forecaster.py` output.

---

## Files Modified

| File | Changes |
|------|---------|
| `backend/models/forecaster.py` | Target fix, spike smoothing, long-term features, quantile crossing fix, confidence calibration rewrite, training window 365→730d |
| `backend/scripts/forecast_prices.py` | Name join fix, drift-triggered auto-retrain |
| `backend/scripts/evaluate_forecaster.py` | Per-fold CV metrics, baseline reporting, quantile crossing fix |
| `backend/scripts/backtest_accuracy.py` | (unchanged) |
| `backend/tests/test_forecaster.py` | **New** — 41 tests |

## Test Results

```
41 passed in test_forecaster.py
85 passed across all tests (6 pre-existing integration failures unrelated)
```

## Measured Accuracy (Post-Fix)

Walk-forward evaluation on 50 items, 26 expanding windows (60-day steps), ~27k samples per horizon, fixed LightGBM params (no ensemble):

| Horizon | Directional Accuracy | vs 50% baseline | Interval Coverage | MAE |
|---------|:--------------------:|:---------------:|:-----------------:|:---:|
| **3d**  | 59.7%                | +9.7pp          | 85.8%             | $0.20 |
| **7d**  | 61.1%                | +11.1pp         | 86.2%             | $0.25 |
| **14d** | 60.8%                | +10.8pp         | 85.6%             | $0.34 |
| **30d** | 65.8%                | +15.8pp         | 82.8%             | $0.52 |

All horizons are well above the 50% 2-class baseline (9-16pp improvement). The 30d horizon benefits most from the 730d training window and added long-term features. The ~80% target interval coverage is being met consistently by the crossing-aware quantile fix.

## Next Retrain Needed

The target fix (#2) changes what the model predicts. A full retrain (`python scripts/forecast_prices.py`) is required before the next forecast run to use corrected targets. The saved models on disk were trained with the inverted target and should be regenerated.
