# Accuracy Improvement Brainstorm

Date: 2026-07-11
Current accuracy (200 items, walk-forward eval): 7d=84.4%, 30d=77.0%

---

## High Impact (~3-8pp directional accuracy)

### 1. Feature medians not persisted (bug)

`forecaster.py:596-601` computes per-feature medians from training data for NaN
imputation, but never saves them to `meta.json`. At prediction time (`:704`),
medians are recomputed from the prediction batch:

- For single-item predictions, median == the item's own value, so `fillna` is
  effectively a no-op.
- For batch predictions, batch medians may differ from training medians due to
  distribution shift.

**Fix:** Save `feature_medians` dict to `meta.json`; load and reuse at
prediction time.

---

### 2. Cyclical temporal encoding

`day_of_week` (0-6), `month` (1-12), `day_of_year` (1-366) are stored as raw
integers (`:264-267`). LightGBM treats integers as ordinal, so Dec→Jan (12→1)
looks like a gap of 11 rather than adjacency.

**Fix:** Apply sin/cos transformation:
```
day_of_week_sin = sin(2π * dow / 7)
day_of_week_cos = cos(2π * dow / 7)
```
Same for month and day_of_year.

---

### 3. Optuna only tunes p50 — same params used for p10/p90

The Bayesian search (`:420-448`) optimizes only the median (p50) quantile loss.
Best params are then applied to p10 and p90 models (`:624-628`). Tail quantiles
likely benefit from different regularization (higher `min_data_in_leaf`, more
`lambda_l1/l2`).

**Fix:** Either run Optuna separately per quantile, or use a joint loss (sum of
quantile losses across p10/p50/p90).

---

### 4. Expanding-window CV instead of single 21-day holdout

Current validation is a single 21-day window (`VALIDATION_WINDOW_DAYS = 21`,
`:32`). A Major or quiet period in those 21 days can arbitrarily inflate or
deflate validation error, making HP selection noisy.

**Fix:** Expanding-window cross-validation (3-5 folds). Train on increasing
windows, validate on contiguous held-out blocks.

---

## Moderate Impact (~1-3pp)

### 5. CatBoost + LightGBM ensemble

Already documented in `model-architecture-decisions.md`. Cross-family ensembles
exploit different bias/variance tradeoffs. Expected lift: +1-3pp. Runs fine on
standard GHA runners.

---

### 6. Prediction sanity checks

No guardrails exist for model output:
- Predicted returns of -200% produce negative prices (no clipping).
- Items with zero volume in the last 30 days still generate forecasts.
- No NaN/INF check after feature imputation at prediction time.

**Fix:** Add price bounds (0 < price < plausible_max), volatility-based
plausibility filters, and volume-staleness warnings.

---

### 7. Event decay: learn decay constants

Decay taus are hardcoded (`:280-286`):
- major: 60d, operation: 21d, case_drop: 14d, update/game_update: 7d

These are domain-informed but not optimized. A simple grid search over tau
values (per event type) on validation data could improve event signal.

---

## Quick Wins

### 8. Player count as a feature

10,470 rows of CS2 player count history (2011-2026) are already collected in
`csmarketapi_reference.db` but never wired into the forecaster. Player count
correlates with market activity and volume.

---

### 9. Winsorize extreme returns

0.16% of daily returns exceed ±500%. These are likely data artifacts
(low-volume stamp trades at extreme prices). Winsorizing at ±200% would
stabilize rolling feature statistics (std, z-score, etc.).

---

### 10. INF value handling

`np.inf` from division by zero is never sanitized before training. LightGBM
behavior on INF is platform-dependent (may silently treat as NaN, may error).

**Fix:** Add `np.isfinite()` check and replace non-finite values with NaN before
imputation.

---

### 11. Drift-triggered retraining

Currently retrains every Monday regardless. `check_concept_drift` (:914-980)
already monitors accuracy but only creates alerts — it doesn't trigger
retraining.

**Fix:** Wire the drift alert into the training scheduler: if accuracy drops
below threshold, schedule an out-of-cycle retrain.

---

## Deeper Architectural Changes (higher effort)

### 12. Conformal prediction instead of quantile crossing fix

Post-hoc monotonicity fix (`:750-751`):
```python
low_ret_arr = np.minimum(p10_ret, p50_ret)
high_ret_arr = np.maximum(p50_ret, p90_ret)
```
This distorts quantile identities (interval becomes [p50, p90] instead of
[p10, p90]). Conformal prediction on the validation set would give
distribution-free coverage guarantees without crossing issues.

---

### 13. Multi-horizon training

Train a single model that predicts both 7d and 30d returns simultaneously
(multi-output). Forces the model to learn shared representations of market
dynamics instead of treating horizons independently.

---

### 14. Item-type sub-models

Cases, stickers, knives, and gloves have fundamentally different price dynamics.
A single global tree must split many times to capture category-specific
patterns. Category-specific models (or category as a learned categorical with
enough depth) could specialize.

---

## Current accuracy (for reference)

| Measure | 7d | 30d |
|---------|:--:|:---:|
| Directional accuracy (200 items, fresh eval) | 84.4% | 77.0% |
| Baseline (2-class random) | ~50% | ~50% |
| Lift over random | ~34pp | ~27pp |
| Interval coverage (80% target) | 94.7% | 92.1% |
