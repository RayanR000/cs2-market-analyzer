# Regime-switching models

**Date:** 2026-07-18

**Files changed:**
- `models/forecaster.py` — added `_assign_regime_label`, `_assign_regime_labels`, `_detect_current_regime`, regime training in `train()`, regime preference in `predict()`, regime persistence in `save_models()`/`load_models()`
- `scripts/forecast_prices.py` — added `--compare-regime` flag for A/B prediction + backtest
- `tests/test_forecaster.py` — 15 new tests in `TestRegimeSwitching` class

---

## What

Separate LightGBM ensembles per market regime (bear / range / bull). Each regime gets its own set of 72 models (4 horizons × 3 quantiles × 6 ensemble members). During prediction, the current regime is detected and regime-specific models are preferred when available.

## Architecture

```
Regime detection: market_return_30d
  bear:  return < -3%
  range: -3% ≤ return ≤ 3%
  bull:  return > 3%
```

Global models stored at `self.models[(horizon, q)]` (unchanged). Regime models stored at `self.regime_models[(regime, horizon, q)]` — a separate dict, loaded/saved alongside global models.

### Total model count

| Layer | Horizons | Quantiles | Ensembles | Regimes | Total |
|-------|----------|-----------|-----------|---------|-------|
| Global | 4 | 3 | 6 | — | 72 |
| Regime | 4 | 3 | 6 | 2–3 | ~180 |
| **Total** | | | | | **~252** |

## Training behavior

Regime models are trained in `train()` after global models complete. Per regime:

1. Filter training data by `_regime` column (assigned from `market_return_30d`)
2. Skip regime if <500 train or <50 val rows
3. Reuse global hyperparameters (no separate Optuna)
4. Train full ensemble (3 quantiles × 6 members)

### Regime distribution from initial run (2026-07-18)

| Horizon | Bear | Range | Bull |
|---------|------|-------|------|
| 3d | skipped (0 val) | 149K / 3.9K | 177K / 5.5K |
| 7d | 74K / 438 | 148K / 5.1K | 177K / 3.8K |
| 14d | 74K / 432 | 146K / 5.6K | 175K / 3.5K |
| 30d | skipped (0 val) | 145K / 2.6K | 170K / 6.9K |

## Prediction behavior

`predict()` now:

1. Detects current regime from `_detect_current_regime()` (global `market_return_30d` mean)
2. For each (horizon, quantile), prefers regime model if available, falls back to global
3. Logs regime vs global usage count after prediction

### Initial prediction (2026-07-18)

Current regime was **bull** (global `market_return_30d` > 3%). Regime model usage: **12/12 (100%)** — all 4 horizons × 3 quantiles used bull-specific models.

## Persistence

- Saved models use filename pattern: `lgb_{horizon}d_q{q}_{regime}_e{ei}.txt`
- `meta.json` stores:
  - `trained_regimes`: list of regimes with trained models
  - `regime_feature_cols`: feature columns used for each regime ensemble

## A/B comparison

`forecast_prices.py --compare-regime` runs two predictions and stores them under different model versions:
- `lgbm-v3-regime`: prediction WITH regime-switching
- `lgbm-v3-global-only`: prediction WITHOUT regime-switching

Both are written to `item_forecasts` with distinct `model_version` values. Backtest runs on all mature forecasts, grouped by `(horizon, model_version)`.

### ⚠️ Known issue: immediate comparison not possible

Calls `backtest_forecasts()` after writing, but new forecasts are for `today` and not yet mature (`today + horizon_days > today`). Meaningful A/B results appear when the first batch of forecasts matures (3+ days).

### Training time impact

Full retrain with regime models adds ~20–25 min on top of global training (53 min total vs ~30 min for global-only on Mac). Breakdown:
- Global training: ~30 min (unchanged)
- Regime training: ~23 min extra (range + bull for 4 horizons)
