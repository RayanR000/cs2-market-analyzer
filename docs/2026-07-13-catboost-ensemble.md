# CatBoost Ensemble — Implementation

## Summary

Added CatBoost as a second model family alongside LightGBM, with predictions averaged across both families at inference. Different boosting algorithms produce different error patterns, so averaging them typically yields +1–3pp directional accuracy.

## Architecture

| Before | After |
|--------|-------|
| 36 LGB models (3 seeds × 3 quantiles × 4 horizons) | 36 LGB + 24 CB models (2 seeds × 3 quantiles × 4 horizons) |
| 3 predictions averaged per quantile | 5 predictions averaged per quantile |

### File naming

- LGB: `lgb_{horizon}d_q{quantile}_e{ei}.txt`
- CB: `cb_{horizon}d_q{quantile}_e{ei}.cbm`

### CatBoost parameters (fixed, no HP search)

| Param | Value |
|-------|-------|
| `loss_function` | `Quantile:alpha={q}` |
| `iterations` | 2000 |
| `learning_rate` | 0.03 |
| `depth` | 6 |
| `l2_leaf_reg` | 3.0 |
| `subsample` | 0.7 |
| `early_stopping_rounds` | 50 |
| `random_seed` | 42, 73 |

Seeds 42 and 73 are used (the first 2 of the 3 LGB ensemble seeds). 91 is skipped since CB converges faster and benefits less from additional seeds.

## Files Changed

| File | Change |
|------|--------|
| `backend/requirements.txt` | Added `catboost>=1.2` |
| `backend/models/forecaster.py` | +147 lines: CB training, predict ensemble, CV evaluation, save/load, meta tracking |
| `backend/scripts/forecast_prices.py` | `MODEL_VERSION` → `lgbm-catboost-v2` |
| `backend/tests/test_forecaster.py` | +70 lines: 4 new tests (CB trains, quantile monotonicity, save/load, has_models) |
| `docs/model-architecture-decisions.md` | Status: "Add CatBoost" → "Done" |

## Key Design Decisions

**No HP search for CatBoost.** A separate CB-specific Optuna run (15 trials × 12 quantile-horizon combos = 180 trials) would add ~20 min to training. Fixed params capture most of the ensemble benefit. HP search can be added later if CB becomes the primary model.

**CV fold evaluation uses both families.** The `_cv_evaluate_horizon` method trains both LGB + CB per fold and averages predictions, so OOF records for confidence calibration reflect the full ensemble.

**Separate model dict.** `self.cb_models` is kept separate from `self.models` (which remains LGB-only). This preserves backward compatibility — old `meta.json` files without `cb_n_ensembles` load LGB models correctly and skip CB loading.

## Expected Impact

| Metric | Estimate |
|--------|----------|
| Directional accuracy | +1–3pp (from 60–66% → 61–69%) |
| Training time | +3–5 min (still within 120-min GH Action timeout) |
| Inference time | +5s (negligible for batch nightly run) |
| Model storage | +12 MB (24 CB files × ~500KB) |

## Verification

All 45 existing + new tests pass:
- 3 CatBoost-specific tests (trains without error, quantile ordering, has_models integration)
- 1 CB save/load roundtrip test
- All 41 original LGB tests unchanged

Next Monday's full retrain will produce both model families. Predict-only mode continues working with LGB-only models until then.
