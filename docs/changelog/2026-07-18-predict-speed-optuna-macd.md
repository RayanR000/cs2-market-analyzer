# Predict speed cache, Optuna reduction, MACD vectorization

**Date:** 2026-07-18

**Files changed:**
- `models/forecaster.py` — feature cache for predict (Parquet), Optuna 50→15 trials, vectorized MACD (no lambda), `_train_ensemble_member` static helper, `defaultdict` import
- `tests/test_forecaster.py` — 3 new tests in `TestFeatureCache` class
- `requirements.txt` — added `joblib>=1.3.0`
- `.gitignore` — ignore `engineered_data.parquet` cache

---

## 1 — Predict feature cache (biggest speed win)

**Problem:** `predict()` ran the full feature engineering pipeline (1460 days of price history for all items) every time, even when no new data had arrived. This took ~5 min per run despite only needing the latest row per item for inference.

**Fix:** After `build_training_data()` completes, save the fully-engineered DataFrame to `engineered_data.parquet` in the model directory. At predict time, load the cache and skip feature engineering if the cache is fresh (≤3 days old, checked via `df.attrs["_cache_date"]`).

**Expected impact:**
- Predict-only: **5 min → ~10-30s on 6/7 days** (cache hit)
- Training day: still runs full pipeline (same as before, then saves cache)

**Staleness detection:**
- Primary: `_cache_date` attrs field (set on save, checked on load)
- Legacy fallback: DuckDB query against Parquet archive (for caches without attrs)
- 3-day tolerance prevents unnecessary refreshes

## 2 — Optuna trials 50 → 15

**Problem:** Initial HP search ran 50 trials per quantile (200 fits/horizon), adding ~20-30 min to the first-ever retrain. Prior experiments showed 15→8 trials cost ≈0pp.

**Fix:** Reduced default `n_trials` from 50 to 15. Cached HP reuse (from Tier-1 speedups) already skips Optuna on subsequent runs.

**Expected impact:** First retrain saves ~15 min.

## 3 — MACD vectorized (lambda removal)

**Problem:** MACD used `groupby.transform(lambda x: x.ewm(...))` which calls a Python function per item group (~5K items × 2 EMAs = 10K function calls).

**Fix:** Replaced lambda transforms with `df.groupby("item_id")["price"].ewm(span=N, min_periods=N, adjust=False).mean()` — a single vectorized call per EMA, no Python overhead.

**Expected impact:** Saves ~30s per run (both train and predict).

## 4 — Ensemble training refactor

Extracted `_train_ensemble_member` as a `@staticmethod` to support future parallel training. The sequential fallback remains because LightGBM's C-level Dataset constructor is not thread-safe for joblib `threading` backend (segfault). Internal `n_jobs=-1` per model still uses all cores.

## Remaining opportunities

| Item | Approach | Effort | Impact |
|------|----------|--------|--------|
| Parallel ensemble training | `ProcessPoolExecutor` with fresh Dataset per worker | 1 day | Saves ~10 min retrain |
| Incremental cache update | Append-only feature engineering for new dates | 2 days | Saves ~4 min on all days |
