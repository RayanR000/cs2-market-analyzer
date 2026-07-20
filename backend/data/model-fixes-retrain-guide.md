# Retrain Guide — Model Fixes (Tier 1)

> **Historical — all fixes implemented.** See `docs/architecture/model.md` for current model architecture.

**Date:** 2026-07-17
**Context:** `backend/data/model-fixes-priority.md` — fixes 1–5 implemented in `backend/models/forecaster.py`

## What changed

| Fix | File | Change |
|-----|------|--------|
| 1. 2026 distribution-shift guard | `build_training_data()` | Moved before subsample; always excludes 2026 rows (removed `month < 6` no-op) |
| 2. Validation-set floor | `train()` temporal split | 100 rows → 2000 rows AND ≥7 distinct dates |
| 3. Permutation-pruning gate | `train()` feature validation | Skipped entirely when val window <2000 rows or <7 dates |
| 4. Zero-fold CV hard failure | `_cv_evaluate_horizon()` | Raises `RuntimeError` instead of silent `[], []` |
| 5. Optuna trials | `_optuna_search_params()` | 20 → 50 trials |

## Retrain steps

### 1. Cold retrain (with HP search)

This is the first retrain after the fixes. It runs Optuna (50 trials × 12 quantile-horizon combos) so it will take longer than subsequent warm retrains.

```bash
cd backend
source venv/bin/activate

# Force HP search since the cached params were from the buggy run
FORCE_HP_SEARCH=1 python scripts/forecast_prices.py --train-only
```

Expected duration: ~30–45 min (cold, full Optuna).

### 2. Backtest

After the retrain completes, run the Parquet backtest to verify the fixes:

```bash
FORECAST_DATE_OVERRIDE=2025-12-01 python scripts/forecast_prices.py --predict-only
python scripts/backtest_accuracy.py --type forecast
```

### 3. Compare against baseline

Check that:
- 7d backtest accuracy recovers from ~53% → ~62%
- 14d/30d models retain more than 4 features
- CV fold_count > 0 (no silent fallback)
- CV accuracy is closer to backtest accuracy (narrower gap)

### 4. If results look good, commit the saved models

```bash
git add backend/models/saved_models/
git commit -m "Retrain after Tier-1 model fixes (2026 distribution guard, val floor, pruning gate, CV hard failure, 50 Optuna trials)"
```

### 5. If results are worse

Check `backend/data/model-fixes-priority.md` for the investigation path. The most likely culprit is the 2026 guard fix not catching all sparse rows — verify the exclusion count in the logs.</think>

<｜DSML｜tool_calls>
<｜DSML｜invoke name="write">
<｜DSML｜parameter name="filePath" string="true">/Users/rayanrane/personal-projects/cs2-market-analyzer/backend/data/model-fixes-retrain-guide.md