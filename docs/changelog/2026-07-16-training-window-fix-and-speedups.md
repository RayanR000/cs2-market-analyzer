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

---

## Part 3 — Bugs found during the first real retrain (2026-07-16)

Running the first full `--train-only` against the local Parquet archive surfaced
several **pre-existing** bugs (unrelated to Parts 1–2) that had silently broken
training and production inference. All are fixed in `models/forecaster.py`.

### 3.1 — Price/source column mislabeling (CRITICAL)

`fetch_price_history()` builds its DataFrame from a DuckDB query whose column
order is `(item_slug, day, source, mean_price AS price, volume)`, but the
DataFrame was constructed with `columns=["item_id", "timestamp", "price",
"volume", "source"]`. The names were **shifted by one** from `source` onward:

| SELECT position | Actual data | Was named |
|---|---|---|
| 2 | `source` (e.g. `STEAMCOMMUNITY`) | `price` |
| 3 | `mean_price` | `volume` |
| 4 | `volume` | `source` |

So the model trained on — and `predict()` served from — **source name strings in
the `price` column**. This first surfaced as a `np.median` `TypeError` in
`_apply_multi_source_voting` (median of strings), which is why the weekly retrain
"kept failing." Introduced by the multi-source voting commit (`e5f4eb0`).

**Impact:** every forecast since that commit was trained on and generated from
garbage prices. Fixing this is the single most important change in this batch.

**Fix:** column order aligned to the SELECT
(`["item_id", "timestamp", "source", "price", "volume"]`).

### 3.2 — VARCHAR price/volume coercion

Some Parquet years store `mean_price`/`volume` as `VARCHAR`; the glob union then
coerces the whole column to string. Added `pd.to_numeric(..., errors="coerce")`
for `price`/`volume` and a `dropna(subset=["price"])`.

### 3.3 — `meta.json` not JSON-serializable

The permutation-test results stored `numpy.bool_`/`numpy.float64` in
`cv_results`, so `json.dump` raised `Object of type bool is not JSON
serializable` **after** all model `.txt` files were written — leaving a valid
model set with no metadata. Fixed by casting `passed`/`drop_pp`/`base_acc`/
`shuffled_acc` to native types at the source and adding a `default=` handler to
`json.dump` (covers `np.bool_`, `np.integer`, `np.floating`, `np.ndarray`).

### 3.4 — `load_models()` hard-failed on corrupt `meta.json`

A truncated/corrupt `meta.json` (e.g. from the 3.3 crash) made startup raise
`JSONDecodeError` and abort the entire run. Now caught → logs a warning and
returns `False` (retrain from scratch) instead of crashing.

### 3.5 — Operational: `optuna` missing from venv

`optuna>=3.6.0` is in `requirements.txt` but was absent from the local venv;
installed. (CI installs from `requirements.txt`, so this was local-only.)

---

## Verified end-to-end retrain (2026-07-16)

First successful full retrain on the corrected pipeline:

- Voted 2.96M → 2.91M rows; **stratified subsample to 504K rows / 1,495 items with the full 730-day calendar preserved** (was silently ~51 days)
- Feature matrix bounded at 504K rows (not the 2.9M that OOM'd)
- **Expanding-window CV produces 2 folds/horizon** (was zero)
- Peak memory ~6.3 GB during voting, ~3 GB after subsample
- Wall-clock **~10 min** for a full 4-horizon retrain locally (bundle A active)
- `meta.json` saves; 12 model groups load cleanly

### Re-baselined accuracy (CV directional, post auto-prune)

| Horizon | Folds | Mean | Range |
|---|---|---|---|
| 3d | 2 | 69.3% | 66.4–72.2% |
| 7d | 2 | 68.0% | 65.1–71.0% |
| 14d | 2 | 67.8% | 64.6–70.9% |
| 30d | 2 | 67.0% | 61.0–72.9% |

These are the first trustworthy cross-validated numbers; prior 60–68% figures
came from the broken pipeline. Auto-prune reduced 124 → ~43 features
(only `price_technicals` passed the permutation test at 3d).

### Committed

`a13d01e` — code fixes + all 12 retrained model groups + `meta.json`.

### Follow-ups

- Watch CI memory: voting peaks ~6.3 GB against the 7 GB `ubuntu-latest` limit.
- `scripts/forecast_prices.py` still passes `max_rows=200_000` (final per-horizon fits sample ~200K of ~490K available rows).
