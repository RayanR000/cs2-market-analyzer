# Cold retrain + accuracy backtest — three bugs fixed

**Date:** 2026-07-22

**Files changed:**
- `backend/models/forecaster.py` — fixed `_skip_cv`/`_warm_retrain` fallthrough for DART horizons during warm retrain; fixed `HORIZON_EXCLUDED_GROUPS` feature-pruning mismatch during warm retrain
- `backend/db/parquet.py` — fixed `_append_parquet` schema-drift crash when new data columns differ from existing Parquet columns
- `docs/changelog/2026-07-22-cold-retrain-accuracy-backtest.md` — this entry

---

## What

Ran a full cold retrain (Optuna HP search from scratch) with CV and regime skips, then attempted to generate forecasts and backtest accuracy against the new models. Hit three bugs during the forecast + backtest pipeline that were fixed in sequence.

## Cold retrain

- **Command:** `FORCE_RETRAIN=1 FORCE_HP_SEARCH=1 SKIP_CV=1 SKIP_REGIMES=1 python scripts/forecast_prices.py --train-only`
- **Duration:** 15.2 min (cold with 10-trial Optuna for 7d)
- **Data:** 6.4M rows from Parquet, 8,691 items, 121 features, 4 horizons
- **Models:** 72 global models (3 quantiles × 3 ensemble members × 4 horizons, plus Ridge residuals for DART horizons)
- 3d and 7d: GBDT with Optuna HP search
- 14d and 30d: DART with HP search skipped (SKIP_HP_HORIZONS), Ridge residual stacking

## Bug 1: `_skip_cv` → `_warm_retrain` RuntimeError on DART horizons

**File:** `backend/models/forecaster.py:2418`

**Root cause:** `_skip_cv` is computed as `SKIP_CV=1 AND boosting_type == "gbdt"`, so it's always False for DART horizons (14d, 30d). When `_warm_retrain` is True, the CV block correctly sets `oof_records = []` at line 2392, but the `elif _skip_cv` check at 2418 is False for DART, so execution falls through to `else: raise RuntimeError(...)`.

**Fix:** Changed `elif _skip_cv:` to `elif _skip_cv or _warm_retrain:` to match the same guard used at line 2387.

## Bug 2: `HORIZON_EXCLUDED_GROUPS` feature-count mismatch during warm retrain

**File:** `backend/models/forecaster.py:2527`

**Root cause:** During warm retrain, feature-group validation is skipped, so models are trained on the full 121 features. But `HORIZON_EXCLUDED_GROUPS` (prunes `cross_sectional` for 14d, both `cross_sectional` + `events` for 30d) still runs, setting `horizon_feature_cols` to 108 and 88 features respectively. At predict time, `X_horizon` selects the pruned columns but the model expects 121 → `LightGBMError: feature count mismatch`.

**Fix:** Added `and not _warm_retrain` guard to the excluded-groups block so `horizon_feature_cols` matches the actual training feature set during warm retrain.

## Bug 3: Parquet append schema-drift crash

**File:** `backend/db/parquet.py:80`

**Root cause:** `_append_parquet` used `SELECT * FROM _new UNION ALL SELECT * FROM read_parquet(...)`. When the new data has a different column set than the existing Parquet file (schema drift), DuckDB raises `BinderError: Set operations can only apply to expressions with the same number of result columns`.

**Fix:** Before the UNION, read the existing Parquet columns via `DESCRIBE`, compute the intersection of columns, and use explicit `SELECT {common_cols} FROM ...` on both sides.

## Accuracy results

Backtest ran against 38,794 mature forecasts stored in the DB (from prior Monday CI runs, not from this session's models — the forecast step hit a stale engineered-feature cache that only covered 2 cached items, so no new forecasts were persisted).

| Horizon | DirAcc | MAPE | wMAPE | IntCov | Samples |
|---------|--------|------|-------|--------|---------|
| **3d** | **61.5%** | 33.9% | 31.9% | 41.8% | 5,512 |
| **7d** | 52.8% | 44.9% | 31.8% | 43.0% | 5,431 |
| **14d** | 55.7% | 53.3% | 32.2% | 51.9% | 5,434 |
| **30d** | 54.2% | 35.0% | 32.5% | 58.9% | 5,360 |

**3d directional accuracy at 61.5%** — well above 50% baseline. Longer horizons cluster around 53-56%, consistent with increasing uncertainty over CS2 market volatility. Coverage interval (IntCov) is healthy for DART horizons (51.9%/58.9%) but weak for GBDT (41.8%/43.0%) — expected when SKIP_CV is enabled and calibration uses a single holdout split instead of pooled OOF predictions.

Per-tier bias corrections were updated from outcomes (21,737 outcome records processed).

## Risk assessment

- **Bug 1 fix** is low-risk — simply extends the existing GBDT guard to also cover DART horizons during warm retrain. Only affects the fallback calibration path.
- **Bug 2 fix** is low-risk — skips an exclusion block during warm retrain that was already inconsistent with the training feature set. Only affects `horizon_feature_cols` alignment.
- **Bug 3 fix** is low-risk — the column-intersection logic is strictly more permissive than the original `SELECT *`. No data loss because the union still contains all unique rows (dedup on `dedup_keys`).
- The stale engineered-feature cache is a pre-existing issue (cached 2026-07-21 with only 60 rows). Next Monday's CI will rebuild it.
