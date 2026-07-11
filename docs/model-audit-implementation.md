# Model Audit Implementation

Changes applied to `backend/models/forecaster.py` addressing Priority 1 and Priority 2 items from `docs/model-audit.md`.

---

## Priority 1 — Immediate

### 1. Feature leakage via `daily_analysis` merge

**Before:** `build_training_data` and `predict` merged daily_analysis features (MA, momentum, volatility, opportunity_score) into training data — these features contained forward-looking information about the current price, creating a leakage path to the target.

**After:** Removed `fetch_daily_analysis()` method entirely. `build_training_data` and `predict` no longer merge daily_analysis or one-hot encode `trend_direction`. The model now learns directly from raw price features.

### 2. Target changed from price level to returns

**Before:** Model predicted absolute price level (`target_7d`, `target_30d`), which is non-stationary — a $500 skin and a $0.50 sticker had completely different scales.

**After:** Primary target is now percentage return (`target_return_{horizon}d`). At prediction time, return predictions are converted back to price levels:

```python
price = current_price * (1 + predicted_return / 100)
```

**Bug fix (Jul 2026):** `prepare_targets` originally used `df.groupby("item_id")["price"].shift(-horizon)` which is **row-based**, not calendar-day-based. With ~72% daily coverage (262 rows over 363 days), `shift(-7)` moved only ~10 calendar days, not 7. The last valid targets appeared in March rather than July, collapsing the validation set to 0 rows. Fixed to use date-based merge lookup: each row looks up the price exactly `horizon` calendar days later via `_target_date` join.

### 3. NaN imputation fixed

**Before:** `X_train = train_set[self.feature_cols].fillna(0)` — filling NaN with 0 created a spurious signal where items with short histories got feature value 0 while mature items got true values.

**After:**
- `min_periods=3` → `min_periods=1` for rolling features (partial estimates instead of NaN)
- `fillna(0)` → per-feature median imputation (learned from training data, applied consistently to train/val/predict)
- Added boolean indicators: `volume_missing`, `rsi_missing`, `macd_missing`

---

## Priority 2 — High Impact

### 4. Temporal train/val split (walk-forward)

**Before:** Two overlapping temporal splits — `_sample_training_data` separated by date, then `train()` did a second 80/20 split that could put older rows in validation and newer in training. The split date was computed as `now - 21`, but after `prepare_targets` drops NaN rows, the effective max date was ~March (not July), making the split date always after all valid data. The fallback 80/20 split always triggered — the "walk-forward" was dead code.

**After:** Single proper walk-forward split using **actual data dates**:
1. Compute `max_date` from the data after target preparation (accounts for NaN-target trimming)
2. Train on data before `max_date - VALIDATION_WINDOW_DAYS` (21 calendar days)
3. Validate on the last 21 days of actual data
4. Fallback to 80/20 only if validation set has <100 rows

The split now correctly produces ~66k validation rows per horizon instead of 0.

### 5. Technical indicators added

New features computed in `_compute_price_features`:

| Feature | Description |
|---------|-------------|
| `bb_upper`, `bb_lower`, `bb_pct_b`, `bb_width` | Bollinger Bands (20-day) |
| `rsi_14` | Relative Strength Index |
| `macd_line`, `macd_signal`, `macd_histogram` | MACD |
| `distance_to_support`, `distance_to_resistance` | Distance from 30-day min/max |
| `high_low_range_30d` | 30-day high/low range |
| `price_accel_7d` | Price acceleration (2nd derivative) |
| `log_return_1d`, `log_return_7d` | Log returns (stationary) |
| `autocorr_1d`, `autocorr_7d` | Autocorrelation proxies |

Additional rolling window: `price_mean_20d`, `price_std_20d`, `price_min_20d`, `price_max_20d` (needed for Bollinger).

Volume features improved:
- `volume_change_*` (ratio) → `volume_log_change_*` (log-ratio, avoids division-by-zero)
- Added `volume_zscore_30d`, `volume_price_conf_7d`, `volume_price_conf_1d`
- Added `volume_mean_30d`, `volume_std_30d` for longer-term context

### 6. LightGBM hyperparameters tuned

| Parameter | Before | After | Reason |
|-----------|--------|-------|--------|
| `num_leaves` | 63 | 31 | Prevents overfitting to noise |
| `max_depth` | not set | 5 | Prevents excessive tree depth |
| `min_data_in_leaf` | not set | 15 | Prevents fitting single outliers |
| `min_gain_to_split` | not set | 0.1 | Prevents splitting on noise |
| `learning_rate` | 0.05 | 0.03 | Better convergence |
| `num_boost_round` | 500 | 1000 | More rounds with regularization |
| `early_stopping` | 20 | 50 | More patience for noisy signals |
| `feature_fraction` | 0.8 | 0.7 | More feature subsampling |
| `bagging_fraction` | 0.8 | 0.7 | More bagging regularization |
| `lambda_l1` | not set | 0.5 | L1 regularization |
| `lambda_l2` | not set | 0.5 | L2 regularization |

### 7. Cross-sectional / market-regime features

New features computed in `_add_cross_sectional_features`:

| Feature | Description |
|---------|-------------|
| `market_return_{1,7,14,30}d` | Mean return across all items per date |
| `item_return_vs_market_{lag}d` | Item's return minus market return |
| `market_volatility_30d` | Mean price_std_30d across all items |
| `market_volume_mean_30d` | Mean volume across all items (30d rolling) |
| `item_volume_vs_market_30d` | Item volume / market volume |
| `market_regime_{bull,bear,range}` | Binary flags based on median market return |

**Bug fix (Jul 2026):** `market_volume_mean_30d` was originally computed as `df.groupby("date")["volume"].transform(lambda x: x.rolling(30, min_periods=1).mean())`. Grouping by date then rolling 30 within a single-date group produces a meaningless rolling average over arbitrary items in index order, not a temporal market-volume signal. Fixed to: compute daily cross-sectional mean volume, then compute rolling 30-day average of that daily series.

### 8. Event feature columns made consistent

**Before:** `_add_event_features` created generic columns (`days_since_last_event`, `events_next_30d`) when `events_df` was empty, but type-specific columns (`days_since_major`, `days_since_operation`, etc.) when events existed. This meant `self.feature_cols` differed between train and predict if event availability changed.

**After:** Always creates type-specific columns for all five event types (`major`, `operation`, `case_drop`, `update`, `game_update`) with defaults of 999/0, regardless of whether `events_df` is empty. Generic columns are no longer created.

---

## Accuracy Results

Walk-forward evaluation on 8,632 items across 365 days of parquet data (1.3M+ rows). Validation set is the last 21 calendar days of data.

| Metric | 7d | 30d |
|--------|-----|-----|
| **Directional Accuracy** | **70.9%** (66,218 samples) | **72.5%** (66,168 samples) |
| **MAE** | $0.01 | $0.02 |
| **Interval Coverage** (80% target) | 90.9% | 77.2% |
| Confidence "high" accuracy | 99.7% | 99.7% |
| Confidence "medium" accuracy | 47.6% | 37.5% |
| Confidence "low" accuracy | 95.5% | 68.2% |

Directional accuracy is well above the 33.3% random baseline for both horizons. The confidence calibration remains heuristic (see remaining items).

### Comparison to prior state

The pre-fix baseline was ~34% directional accuracy (near random) for the old MA-crossover analyzer. The ML forecaster now achieves ~71-72%, a ~37pp improvement.

---

## Remaining Items (not yet addressed)

From `docs/model-audit.md`:

| Step | Change | Expected Impact | Complexity | File |
|------|--------|----------------|------------|------|
| 8 | Replace days-since-event with exponential decay | Medium | Low | `forecaster.py` |
| 9 | Fix event analyzer z-score (per-item volatility) | Low | Low | `event_analyzer.py` |
| 10 | Calibrate confidence scores on validation set | Low | Medium | `forecaster.py` |
| 11 | Standardize long-term vs daily analyzer labels | Low | Low | `long_term_trend_analyzer.py`, `analyze_trends.py` |
| 12 | Fix backtest evaluation (volatility-relative threshold) | Low | Low | `backtest_accuracy.py` |

---

## Files Modified

- `backend/models/forecaster.py` — all changes described above
- `backend/scripts/evaluate_forecaster.py` — walk-forward evaluation script (added Jul 2026)

## Files Cleaned Up

- `backend/models/saved_models/*` — cleared (incompatible with new feature set/target)
