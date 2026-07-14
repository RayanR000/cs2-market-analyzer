# CatBoost Removal — 2026-07-13

## Goal

Determine whether the LGBM+CatBoost quantile ensemble adds predictive value. If not, remove CatBoost entirely to simplify the codebase, reduce training time, and eliminate a heavy dependency.

## Methodology

1. **Shallow ensemble test** — trained CB (Quantile alpha) and LGB on 500 random items, compared direction agreement and price impact. Found only 5.2% direction change rate and <1% mean price impact, suggesting CB was near-redundant or noise.
2. **Walk-forward evaluation** — ran side-by-side LGB-only vs LGB+CB over 4 horizons (3d/7d/14d/30d) with the same train/val splits:
   - LGB-only: 60–66% directional accuracy
   - LGB+CB ensemble: **41–47%** (below random baseline)
   - CB degraded accuracy by ~18–20 percentage points.

## Conclusion

CatBoost quantile regression is systematically inaccurate on this data. When averaged with LGB predictions, it destroys signal. The ensemble provides no benefit.

## What Was Removed

| File | Change |
|------|--------|
| `backend/models/forecaster.py` | Removed `catboost` import, `cb_models` dict, CB training (`_train_cb_ensemble`), CB CV, CB prediction branch in `_predict_item`, CB save/load in `save_models`/`load_models`. Removed `cb_n_ensembles` from meta.json deserialization. |
| `backend/scripts/forecast_prices.py` | `MODEL_VERSION` changed from `lgbm-catboost-v2` to `lgbm-v2` |
| `backend/scripts/evaluate_forecaster.py` | Removed `--use-cb` flag, `catboost` import, CB training branch in walk-forward loop |
| `backend/tests/test_forecaster.py` | Removed `test_save_load_cb_models`, entire `TestCatBoost` class (3 tests) |
| `backend/requirements.txt` | Removed `catboost>=1.2` |
| `backend/models/saved_models/*.cbm` | Deleted 24 CatBoost model files |

## Codebase Impact

- `forecaster.py`: 1468 lines (down from 1563 in the CB era, −95 lines)
- Tests: 41 pass (down from 45), all CI-relevant coverage retained
- Dependencies: catboost removed, environment lighter

## Retrain Results

Full retrain without CatBoost completed in ~30 minutes:

| Horizon | CV Accuracy | CV Std |
|---------|-------------|--------|
| 3d | 68.1% | 5.7% |
| 7d | 70.0% | 8.3% |
| 14d | 68.2% | 6.7% |
| 30d | 65.8% | 6.0% |

- 36 LGB models saved (4 horizons × 3 quantiles × 3 ensemble seeds)
- 22,168 forecasts written to DB with `lgbm-v2` model_version
- Stale `lgbm-catboost-v2` forecasts overwritten by upsert

## Current State

- `saved_models/` contains 37 files: 36 `lgb_*.txt` + `meta.json`
- DB contains 44,120 `lgbm-v1` forecasts and 22,168 `lgbm-v2` forecasts
- Pipeline stages: fetch → backfill → aggregate → train → predict (no CB in any stage)
