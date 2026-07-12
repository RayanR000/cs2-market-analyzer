# Model Architecture Decisions

## Current Architecture

Single `ItemForecaster` containing **36 LightGBM models**:

```
3d horizon:  3 quantiles (p10, p50, p90) × 3 seeds (42, 73, 91)
7d horizon:  3 quantiles (p10, p50, p90) × 3 seeds (42, 73, 91)
14d horizon: 3 quantiles (p10, p50, p90) × 3 seeds (42, 73, 91)
30d horizon: 3 quantiles (p10, p50, p90) × 3 seeds (42, 73, 91)
```

Predictions are averaged across seeds per quantile. p10/p90 provide the interval, p50 is the point prediction.

## Decisions

| Component | Current | Keep? | Why |
|-----------|---------|-------|-----|
| Ensemble seeds | 3 | ✅ Keep | 3-5 is the sweet spot. More seeds give diminishing variance reduction. |
| Quantiles | 3 (p10/p50/p90) | ✅ Keep | Minimal set for point prediction + confidence interval. Dropping p50 loses predictions; adding more doesn't help much. |
| Horizons | 4 (3d, 7d, 14d, 30d) | ✅ Keep | 3d captures short-term momentum similar to 7d (87.7% dir acc); 14d is a natural midpoint between 7 and 30 (85.9%). 1d was rejected for being too noisy. |
| Confidence | Per-horizon binary (high/low) | ✅ Keep | Each horizon calibrates its own range_pct and change_pct thresholds from validation data. Stored as nested dict in meta.json. |
| Model family | LightGBM only | ➕ Add CatBoost | Largest remaining lift opportunity. Different algorithm = different error patterns. Ensemble averaging across families typically gives +1-3pp. |

## What Not To Do

- **Do not replace with a fine-tuned LLM.** LLMs are worse at numerical time series, slower, harder to retrain, and need 100-1000x more data. LightGBM is the right tool for tabular forecasting.
- **Do not add more neural forecasting models** (N-BEATS, PatchTST, etc.) unless accuracy plateaus and you're willing to manage GPU training. The complexity jump isn't justified at 86-88% accuracy.

## Hyperparameter Search

Replaced brute-force grid search with **Optuna Bayesian optimization** (Jul 2026).

| Before | After |
|--------|-------|
| Grid search: 81 combos (3⁴) | Optuna TPE: 30 Bayesian trials |
| Searched 4 params (`num_leaves`, `lr`, `lambda_l1`, `lambda_l2`) | Searches **6 params** (+ `max_depth`, `min_data_in_leaf`) |
| Fixed discrete values per param | Continuous ranges with log-uniform sampling for `lr` |
| All 81 trials run to completion | `MedianPruner` kills bad trials early (n_startup=5, n_warmup=10) |
| 1 trial round per param combo | TPE sampler learns which regions are promising and focuses there |

**Why:** Bayesian search with pruning finds equally good or better params in ~1/3 the time. The grid was wasteful — many combos were nearly tied in validation loss, and the winner was noisy run-to-run. Optuna also let us expand to 6 params without increasing search time.

**Bug fix (Jul 2026):** `_optuna_search_params` originally hardcoded `alpha=0.5` in the objective function, and the caller's `quantile=q` parameter was never received by the method (signature mismatch). This meant the p10 and p90 models were optimized with hyperparameters found at alpha=0.5, not the correct quantile. Fixed by adding `quantile: float = 0.5` to the method signature and using it as `alpha` in the objective.

**Files changed:**
- `backend/requirements.txt` — added `optuna>=3.6.0`
- `backend/models/forecaster.py` — replaced `_grid_search_params` → `_optuna_search_params`, updated `train()` merge logic

## Confidence Calibration

After training, `_calibrate_confidence()` scans the validation set per horizon to find optimal thresholds:

- **`high_range`**: Max prediction interval width (normalized by midpoint) that achieves ≥75% directional accuracy
- **`high_change`**: Minimum absolute price change (normalized) to further tighten the high-confidence bucket
- Thresholds are stored per-horizon in `meta.json` as `{"3": {...}, "7": {...}, "14": {...}, "30": {...}}`
- Backward compatible: legacy flat dicts are distributed to all horizons on load

## Horizon Selection

3d and 14d were chosen over 1d and 60d:

| Horizon | Rejected? | Why |
|---------|-----------|-----|
| 1d | ❌ Too noisy | Day-to-day CS2 price action is dominated by random walk. The feature set lacks same-day microstructure data. |
| 3d | ✅ Added | Short-term momentum, smooths weekend gaps, performs nearly as well as 7d (87.7% vs 88.4%). |
| 14d | ✅ Added | Natural midpoint between 7 and 30. Many CS2 trade/demand cycles run ~2 weeks. The feature set already computes 14d rolling windows. |
| 60d | ❌ Not yet | Would require more training data. The 30d model already sees accuracy drop to 79.7%; 60d would be worse without richer long-term features. |

## Future Consideration (do this after CatBoost)

- **Expanding-window CV** — train on multiple expanding windows, average predictions across folds. Reduces sensitivity to any single validation window. Would replace the current single 21-day holdout.
