# Training window fix + training speedups

**Date:** 2026-07-16

**Files changed:**
- `models/forecaster.py` — pre-feature-engineering stratified subsample, calendar-preserving safety cap, `predict()` window reconciliation, Optuna/Dataset/`max_bin` speedups
- `tests/test_forecaster.py` — `TestTrainingWindow` regression tests
- `.github/workflows/price-forecast.yml` — `timeout-minutes` 120 → 180

---

## Part 1 — Training window fix

Fixes the bug documented in `docs/2026-07-16-training-window-audit.md`: the
post-feature-engineering `train_set.tail(max_rows)` cap kept only the most
recent ~51 calendar days (dropping 93% of voted rows) as the archive grew.
This silently disabled expanding-window CV (needs `CV_MIN_TRAIN_DAYS=200`
distinct dates) and caused the weekly Monday retrain to OOM/timeout because
`engineer_features` still ran on all ~2.9M rows.

### Changes

| # | Change | Location |
|---|---|---|
| 1 | `_stratified_item_subsample()` — keeps whole item histories (stratified by rarity) to bound rows **before** `engineer_features`, preserving the full 730-day calendar window and per-item time-series continuity | `build_training_data()` |
| 2 | `build_training_data(max_feature_rows=500_000)` — subsamples up front | `forecaster.py` |
| 3 | Replaced `train_set.tail(max_rows)` with a random, calendar-preserving safety guard; bumped `train()` default cap 200k → 600k | `train()` |
| 4 | `predict()` `days_back` 365 → 730 for train/predict consistency | `predict()` |
| 5 | `TestTrainingWindow` — asserts row bounding, calendar preservation, full-history retention, CV ≥ 2 folds, and documents the 51-day zero-fold failure | `tests/test_forecaster.py` |
| 6 | `timeout-minutes` 120 → 180 (safety margin) | `price-forecast.yml` |

### Expected outcome

- Feature engineering stays bounded (~500k rows) and under the 7 GB runner limit
- Training spans the full 730-day window
- Expanding-window CV produces folds → fold-level metrics + pooled-OOF calibration return
- Weekly Monday retrain succeeds

### Note

`scripts/forecast_prices.py` still calls `train(max_rows=200_000)` explicitly.
The calendar window is now correct regardless (subsample fixed that), but the
per-horizon final fit still samples ~200k rows (randomly, not `tail`). Raise
those call sites to use the fuller matrix if desired (trades training time).

---

## Part 2 — Training speedups (bundle A)

Reduces full-retrain wall-clock ~40–50% with negligible accuracy impact
(estimated ~0 to −0.5pp directional, most likely within noise).

| Lever | Change | Location | Accuracy impact |
|---|---|---|---|
| A1 | Optuna `n_trials` 15 → 8; `MedianPruner(n_startup_trials 5 → 3)` | `_optuna_search_params()` | ~0 to −0.5pp (docs peg 15→50 at only +0.5–1pp) |
| A2 | Build `lgb.Dataset` once and reuse across quantiles/ensemble/CV instead of rebuilding per fit | Optuna search, `train()` horizon loop, `_cv_evaluate_horizon()` | 0pp (pure refactor — same data/binning/seeds) |
| A3 | `max_bin` 255 → 127 (set in params **and** at Dataset construction for deterministic binning) | Optuna params, ensemble base params, all `lgb.Dataset(...)` | ~0 to −0.3pp (mild regularization) |

### Cost structure (why A1 dominates)

Per horizon (×4): Optuna 3 quantiles × 15 trials = 45 fits (~55–62% of time),
final ensemble 9 fits, CV ~9 fits. Optuna is the largest block, so cutting its
trials is the biggest single lever.

### Verification

- All 46 `test_forecaster.py` tests pass.
- Recommend timing one horizon before a full retrain to confirm the speedup.
