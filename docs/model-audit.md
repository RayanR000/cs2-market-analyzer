# Model Audit: Accuracy Analysis & Improvement Roadmap

Current directional accuracy: **~34%** (baseline for 3-class random: 33.3%)
Measured across 187,850+ historical walk-forward samples per window.

---

## Priority 1 — Immediate (biggest impact)

### 1. Feature leakage via `daily_analysis` merge

**File:** `backend/models/forecaster.py:269-274`
```python
df = df.merge(da_df, left_on=["item_id", "date"],
              right_on=["item_id", "analysis_date"], how="left")
```

**Problem:** The forecaster merges `daily_analysis` features (MA, momentum, volatility, opportunity_score, etc.) into training data. These features are computed from the *same* price history the model is trying to predict. They contain forward-looking information about the current price relative to recent history, creating a direct leakage path to the target.

**Fix:**
- Remove the `daily_analysis` merge entirely and let the model learn its own price representations from raw features, OR
- Lag the join by 1 day: join on `analysis_date - 1` so features don't contain information about the current date.

### 2. Target is price level, not returns (non-stationary)

**File:** `backend/models/forecaster.py:248-254`
```python
df[f"target_{horizon}d"] = df.groupby("item_id")["price"].shift(-horizon)
```

**Problem:** The model predicts absolute price level (`target_7d`, `target_30d`). Price levels are non-stationary — a $500 skin and a $0.50 sticker have completely different scales and trends. The model wastes capacity learning item-specific intercepts and long-term trends instead of predicting directional dynamics. The `target_return` column is computed but never used as the actual prediction target.

**Fix:**
- Change the primary target to percentage return: `target_return_{horizon}d`
- At prediction time, convert returns back: `forecast_price = current_price * (1 + predicted_return / 100)`

### 3. NaN → 0 imputation destroys feature semantics

**File:** `backend/models/forecaster.py:357-360`
```python
X_train = train_set[self.feature_cols].fillna(0)
X_val = val_set[self.feature_cols].fillna(0)
```

**Problem:** Many features produce NaN legitimately:
- Rolling features are NaN for items with insufficient history (`min_periods=3`)
- Volume-based features are NaN when volume data is missing
- Event features default to 999 (fine), but rolling features get 0

Filling with 0 creates a spurious signal: items with short histories get feature value 0 for `price_mean_30d` while mature items get the true value. The model learns to discriminate on data maturity, not price dynamics.

**Fix:**
- Use `min_periods=1` for rolling features to get partial estimates
- For truly missing features, impute with per-feature median from valid data only
- Add boolean indicator columns for features with frequent missingness

---

## Priority 2 — High Impact

### 4. Train/validation split violates temporal ordering

**File:** `backend/models/forecaster.py:320-355`
```python
def _sample_training_data(self, targets, horizon, max_rows=200_000):
    train = targets.dropna(...)
    before_split = train[... < self.TRAIN_SPLIT_DATE]
    after_split = train[... >= self.TRAIN_SPLIT_DATE]
    ...

def train(self, max_rows=200_000):
    ...
    split_idx = int(len(train_df) * 0.8)
    train_set = train_df.iloc[:split_idx]
    val_set = train_df.iloc[split_idx:]
```

**Problem:** Two overlapping temporal splits:
1. `_sample_training_data` separates data by `TRAIN_SPLIT_DATE` (21 days ago), keeping all recent data
2. `train()` then does a *second* 80/20 split, potentially putting older rows in validation and newer rows in training

**Fix:** Single proper walk-forward split:
- Sort all data chronologically
- Train on data up to date D
- Validate on D+1 through D + VALIDATION_WINDOW_DAYS
- For the final model, train on all data up to `today - VALIDATION_WINDOW_DAYS`

### 5. Missing classic technical features

**File:** `backend/analytics/trend_analyzer.py:110-218` (implementations exist)
**File:** `backend/models/forecaster.py:129-173` (not used)

**Problem:** `TrendAnalyzer` already implements RSI(14), MACD, Bollinger Bands, and Support/Resistance detection, but none of these are wired into the forecaster's feature engineering pipeline. The forecaster only uses lag prices, returns, and rolling statistics.

**Missing features that implementations already exist for:**
- `rsi_14` — Relative Strength Index (mean reversion signal)
- `macd_line`, `macd_signal`, `macd_histogram` — trend convergence/divergence
- `bb_upper`, `bb_middle`, `bb_lower` — Bollinger Band position
- `bb_pct_b` — normalized position within bands (0 = lower, 1 = upper)
- `bb_width` — volatility regime indicator
- `support`, `resistance`, `distance_to_support`, `distance_to_resistance`

**Fix:** Compute these in `_compute_price_features()` and add to `self.feature_cols`.

---

## Priority 3 — Important

### 6. LightGBM hyperparameters untuned for financial noise

**File:** `backend/models/forecaster.py:365-378`
```python
params = {
    "num_leaves": 63,
    "learning_rate": 0.05,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    ...
}
```

**Problems:**

| Parameter | Current | Recommended | Reason |
|-----------|---------|-------------|--------|
| `num_leaves` | 63 | 15-31 | Current is too deep; overfits to noise |
| `min_data_in_leaf` | not set | 10-20 | Prevents leaf nodes from fitting single outliers |
| `max_depth` | not set | 4-5 | Prevents excessive tree depth with correlated features |
| `lambda_l1` | not set | 0.5-1.0 | L1 regularization for sparse features |
| `lambda_l2` | not set | 0.5-1.0 | L2 regularization for correlated rolling features |
| `learning_rate` | 0.05 | 0.01-0.03 | Lower rate + more rounds = better convergence |
| `num_boost_round` | 500 | 1000-2000 | More rounds with regularization |
| `early_stopping` | 20 | 50-100 | More patience for noisy signals |
| `min_gain_to_split` | not set | 0.1 | Prevents splitting on noise |

### 7. No cross-sectional / market-regime features

**Problem:** Each item is modeled independently. The model has no information about broader market context — whether *everything* is rising, whether this item's category is outperforming, or whether volatility is elevated market-wide.

**Missing features to add in `_compute_price_features()` or after feature engineering:**

- `market_return_7d` — mean 7d return across all items on that date
- `market_volatility_30d` — mean volatility across all items
- `item_return_vs_market_7d` — item's 7d return minus market return
- `category_return_7d` — mean return for items of same type (skin/case/sticker)
- `item_return_vs_category_7d` — item's return minus category return
- `market_regime` — binary/triclass: bull/bear/range based on median market return

### 8. Confidence score is heuristic, not calibrated

**File:** `backend/models/forecaster.py:506-515`
```python
def _compute_confidence(mid, low, high, current):
    range_pct = (high - low) / mid
    change_pct = abs(mid - current) / current
    if range_pct < 0.1 and change_pct > 0.03:
        return "high"
    elif range_pct < 0.2:
        return "medium"
    return "low"
```

**Problem:**
- Confidence is based on prediction interval width, not empirical accuracy
- Thresholds (`< 0.1`, `< 0.2`) are arbitrary, not data-driven
- The backtest measures confidence accuracy, but the metric is meaningless without calibration

**Fix:**
- After training, compute empirical directional accuracy per confidence bucket on the validation set
- Adjust thresholds so "high" confidence historically achieves ≥80% directional accuracy
- Use Platt scaling or isotonic regression for probability calibration

---

## Priority 4 — Should Fix

### 9. Event features are too coarse

**File:** `backend/models/forecaster.py:189-225`

**Problems:**
- `days_since_{event_type}` has a hard cutoff at 999 — no decay weighting
- No event *density* feature (e.g., how many events in the last 30/60/90 days)
- No event *magnitude* distinction — a Major and a minor update within the same type get the same treatment
- `events_next_30d` uses future information (acceptable as known schedule, but debatable)

**Fix:**
- Replace `days_since_event` with exponential decay: `exp(-days_since / decay_constant)`
- Learn or set `decay_constant` per event type (7d for updates, 21d for operations, 60d for majors)
- Add `event_density_last_30d` and `event_density_last_90d` per event type

### 10. Volume features are degenerate

**File:** `backend/models/forecaster.py:159-171`

**Problems:**
- `volume_change_1d = volume / volume_lag_1d` — when lag is 0, this produces NaN (filled as 0, which is wrong)
- No volume-price confirmation features (is price up on high volume?)
- Volume data quality varies across sources
- No volume trend acceleration (second derivative)

**Fix:**
- Use log-ratio for volume change: `log(volume / volume_mean_7d)`
- Add volume-price confirmation: `return_7d * (volume_change_7d > 1)`
- Add volume z-score relative to 30-day mean
- Flag suspicious volume entries via data source quality scores

### 11. Quantile crossing is sorted away, not fixed

**File:** `backend/models/forecaster.py:478`
```python
quantile_preds = np.sort(
    np.round(np.vstack([preds[0.1], preds[0.5], preds[0.9]]), 2), axis=0
)
```

**Problem:** Sorting quantile predictions breaks the integrity of individual models. After sorting, the "10th percentile" prediction might actually come from the 50th percentile model. Prediction intervals become statistically invalid.

**Fix:**
- Train a single multi-quantile model with alpha as a feature
- Use non-crossing quantile regression constraints
- At minimum, log the crossing rate as a diagnostic metric during prediction

### 12. Event analyzer z-score uses hardcoded baseline volatility

**File:** `backend/scripts/event_analyzer.py:219`
```python
baseline_volatility = 2.0  # Typical daily volatility in percentage
```

**Problem:** Assumes every item has ~2% daily volatility. In reality:
- Popular skins: 1-3% daily vol
- Rare/collectible items: 5-15%
- Cases during hype periods: 20%+

An item with 15% volatility would need a 30%+ 1-day move to reach z=2. An item with 1% vol needs only 2%. The significance test is useless for both extremes.

**Fix:**
```python
item_returns = [...]
baseline_volatility = statistics.stdev(item_returns)  # or MAD for robustness
z_score = abs(impact_1day) / (baseline_volatility + 1e-6)
```

### 13. Holdout validation in event analyzer is circular

**File:** `backend/scripts/event_analyzer.py:282`
```python
pattern.holdout_accuracy = consistency_score  # Circular!
```

**Problem:** The "holdout accuracy" is literally set equal to the `consistency_score`, not measured on actual held-out data. Check #6 in the 6-point validation framework passes tautologically whenever Check #3 passes. The entire "holdout validation" column is meaningless.

**Fix:** Compute holdout accuracy by:
1. Training the pattern on all events except the most recent N
2. Testing the pattern's predictions against actual outcomes for those N held-out events
3. Storing the result separately from the consistency score

### 14. Long-term vs daily analyzer inconsistency

**File:** `backend/scripts/long_term_trend_analyzer.py:171-178`
**File:** `backend/scripts/analyze_trends.py:283-293`

**Problems:**
- Daily analyzer: directions `"up"`, `"down"`, `"flat"`
- Long-term analyzer: directions `"bullish"`, `"bearish"`, `"neutral"`
- Both write to the same `daily_analysis.trend_direction` column
- The long-term analyzer uses a different opportunity score formula (`momentum * 0.6 + deviation * 0.4` vs the daily's piecewise thresholds)

**Fix:** Standardize direction labels and opportunity score formula across both analyzers. The long-term analyzer's docstring says it "replaces" short-term results, but both upsert with the same composite key — the last writer wins, creating unpredictable behavior.

### 15. Backtest evaluation methodology issues

**File:** `backend/scripts/backtest_accuracy.py`

**Problems:**
- Directional accuracy uses a 2% threshold to define "up"/"down" — moves of 1.9% are classified "flat," deflating accuracy for genuinely directional models
- Historical backtest skips "flat" predictions entirely, cherry-picking only non-flat signals for evaluation
- Actual prices come from `chart_points` (built from parquet) while predictions come from `price_history` — potential data source mismatch in aggregation methods

**Fix:**
- Use a volatility-relative threshold (e.g., 0.5 * 30d volatility) instead of a fixed 2%
- Include "flat" predictions in the historical backtest confusion matrix
- Align ground truth data source with the prediction data source

---

## Priority 5 — Lower Impact

### 16. Additional missing features (mostly resolved)

Most features listed in the original audit are now implemented (log returns, autocorrelation, price acceleration, distance to support/resistance). Still absent:

| Feature | Why It Matters |
|---------|----------------|
| On-balance volume (OBV) | Volume confirms trend direction |
| Price spike indicator (price > 2*std in 24h) | Detects anomaly events |
| Volatility regime change (vol_30d / vol_7d) | Regime shift detection |
| Volume-weighted price | True value consensus |

### 17. Recency mismatch between training and prediction (partially resolved)

**File:** `backend/models/forecaster.py:48-52` vs `:531`

Training fetches **365 days** of price history while `predict()` fetches only **90 days**. The daily_analysis merge issue was fixed (merge removed entirely), but the window asymmetry remains: rolling features (mean, std, min/max) at inference time average over shorter lookbacks than during training. This shifts their distribution.

**Fix:** Either train on a matching 90-day window, or extend the predict fetch window to 365 days.

### 18. No automated hyperparameter tuning or feature selection (partially resolved)

Hyperparameters were manually tuned with sensible defaults for financial noise (lower `num_leaves`, added regularization, etc.), but the codebase still lacks:
- Automated search (grid / Bayesian) over hyperparameters
- Feature importance-based pruning of low-value features
- Correlation analysis to remove redundant features (~70+ features, many correlated)
- Learning curve analysis to determine optimal training size
- Permutation importance to validate feature contributions

---

## Priority 6 — Post-Audit Improvements

### 19. Medium confidence bucket is near-useless

**File:** `backend/models/forecaster.py:641-756`

**Current accuracy:** Medium bucket achieves 19-35% directional accuracy — at or below random (50% for 2-class). The calibration loop finds thresholds that technically meet the ≥55% target, but the bucket collapses in practice because range_pct between "high" and "medium" boundaries captures a heterogenous mix of predictions.

**Fixes (choose one):**
- Consolidate to binary confidence (high/low), dropping the medium tier
- Replace range_pct heuristic with model-based uncertainty (variance of predictions across trees, or dropout-like Monte Carlo sampling)
- Require medium bucket to meet a higher accuracy target (≥60%) and accept it may be empty most days

### 20. No ensembling

**File:** `backend/models/forecaster.py:482-517`

Each quantile+horizon combination uses a single LightGBM model. Single models are sensitive to seed and data ordering, producing higher prediction variance.

**Fix:**
- Train 3-5 LightGBM models per quantile with different `random_state` values
- Average predictions across ensemble members
- Optionally add XGBoost or CatBoost as a secondary model family and average across model types

### 21. Single fixed walk-forward split is noisy

**File:** `backend/models/forecaster.py:453-458`

The validation split is a single 21-day holdout at the end of the time series. A single split is sensitive to the specific events in that window (a Major during validation inflates error, a quiet period deflates it).

**Fix:**
- Implement expanding-window cross-validation: train on months 1-6, validate on month 7; train on months 1-7, validate on month 8; etc.
- Report mean ± std of accuracy across folds
- Alternatively, use purged walk-forward (avoid temporal leakage between folds)

### 22. No concept drift monitoring

Once deployed, the model's accuracy will degrade as market dynamics shift (new game updates, changing player behavior, source data quality changes). There is no mechanism to detect drift or trigger retraining.

**Fix:**
- Track rolling directional accuracy over the last N predictions (e.g., 7-day sliding window)
- Flag drift when accuracy drops below a threshold (e.g., 60% for 7d)
- Trigger automatic retraining via a scheduler or webhook
- Log drift events to an `accuracy_alerts` table for observability

---

## Summary: Implementation Order

| Step | Change | Expected Impact | Complexity | Status |
|------|--------|----------------|------------|--------|
| 1 | Remove `daily_analysis` feature leakage | **High** | Low | ✅ Done |
| 2 | Change target from price level to returns | **High** | Medium | ✅ Done |
| 3 | Fix NaN imputation (per-feature medians) | **High** | Low | ✅ Done |
| 4 | Add RSI, MACD, Bollinger %B features | **High** | Medium | ✅ Done |
| 5 | Fix temporal train/val split (walk-forward) | **High** | Medium | ✅ Done |
| 6 | Tune LightGBM params (regularization, depth) | Medium | Low | ✅ Done |
| 7 | Add cross-sectional / market-regime features | Medium | Medium | ✅ Done |
| 8 | Replace days-since-event with decay weighting | Medium | Low | ✅ Done |
| 9 | Fix event analyzer z-score (per-item volatility) | Low | Low | ✅ Done |
| 10 | Calibrate confidence scores | Low | Medium | ✅ Done |
| 11 | Standardize long-term vs daily analyzer | Low | Low | ✅ Done |
| 12 | Fix backtest evaluation methodology | Low | Low | ✅ Done |
| 13 | Fix recency mismatch (365d → 90d align) | Medium | Low | ❌ Pending |
| 14 | Automated HP search (grid/Bayesian) | Medium | Medium | ❌ Pending |
| 15 | Feature pruning (correlation + importance) | Medium | Medium | ❌ Pending |
| 16 | Fix medium confidence bucket | Low | Medium | ❌ Pending |
| 17 | Model ensembling (multi-seed + XGBoost) | Medium | Medium | ❌ Pending |
| 18 | Expanding-window CV (multiple folds) | Medium | Medium | ❌ Pending |
| 19 | Concept drift monitoring & auto-retrain | Medium | Medium | ❌ Pending |
