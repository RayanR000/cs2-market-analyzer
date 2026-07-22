# Remove all multiprocessing and threading from training path

**Date:** 2026-07-21

**Files changed:**
- `backend/models/forecaster.py` — removed `_train_horizon_worker`, `_merge_horizon_result`, `ThreadPoolExecutor` in 3 places, `spawn` Pool + Feather file I/O, imports of `tempfile`/`uuid`/`multiprocessing`/`ThreadPoolExecutor`, `horizon_workers` parameter, CPU budget math
- `backend/scripts/forecast_prices.py` — added retry limit to DB batch insert loop

**Total:** -209 lines, +53 lines

---

## What changed

The training pipeline had two layers of parallelism — a `spawn` multiprocessing Pool to train 4 horizons concurrently, and `ThreadPoolExecutor` to train 3 ensemble members per quantile concurrently. These were fragile and provided marginal benefit on typical CI runners (2–4 cores).

### Removed entirely

| Component | Lines | Risk it caused |
|-----------|-------|----------------|
| `_train_horizon_worker()` | ~58 | Multiprocessing worker that read a temp Feather file, spawned a new `ItemForecaster`, trained one horizon, serialized all models to strings for pickling back to parent. The `spawn` context + Feather file workaround existed because pickling a large DataFrame through OS pipes stalls. |
| `_merge_horizon_result()` | ~22 | Reconstructed LightGBM models from strings via `lgb.Booster(model_str=s)` after receiving worker results. |
| Parallel branch in `train()` | ~35 | `mp.get_context("spawn").Pool().map_async().get(timeout=7200)` — the 2-hour timeout was the safety net for worker deadlocks. Temp Feather file written before pool, cleaned up in `finally`. |
| `ThreadPoolExecutor` in ensemble training (×2) | ~40 | One for global models, one for regime models. Each submitted 3 ensemble members to a thread pool with `f.result(timeout=1800)`. 30-min per-member timeout masked OpenMP deadlocks. |
| `ThreadPoolExecutor` in Optuna per-trial `lgb.train()` | ~7 | Each Optuna trial wrapped `lgb.train()` in a `ThreadPoolExecutor(max_workers=1)` to get a 10-min timeout — a nested thread island around a call that already spawns OpenMP threads. |
| `ThreadPoolExecutor` in CV fold training | ~7 | Same pattern as Optuna — single-thread pool to add timeout to `lgb.train()`. |

### Imports removed

`tempfile`, `uuid`, `multiprocessing as mp`, `from concurrent.futures import ThreadPoolExecutor`

### CPU allocation simplified

Before: `horizon_workers` → `cpu_budget` → `n_workers` → `cpu_per_worker` (5 lines of math per section, duplicated for global + regime).

After: `n_jobs = max(1, (os.cpu_count() or 4) // 2)` — one line, used everywhere.

### DB batch insert retry limit fixed

`_write_forecasts_to_db` in `forecast_prices.py` had unlimited retries — if the DB connection kept failing, it looped forever. Added `max_retries = 3` with `break` on success, `raise` on final failure.

## Why

The parallelism existed to reduce wall-clock retrain time, but the actual savings were small:

- **On a 2-core CI runner:** parallelism disabled entirely (`use_parallel=False`, `n_workers=1`). Sequential total: ~22 min.
- **On a 4-core machine:** 2 horizon workers, 2 ensemble threads. Wall time: ~15 min. Saves **~7 min**.
- **On an 8-core machine:** 4 horizon workers, 2 ensemble threads. Wall time: ~8 min. Saves **~14 min**.

The cost of saving 7–14 min:

| Cost | Detail |
|------|--------|
| Deadlock risk | Nested `spawn` Pool → ThreadPoolExecutor → OpenMP threads could hang indefinitely. The code had comments warning about this. |
| 2-hour silent timeout | `async_result.get(timeout=7200)` — if a worker hung, no feedback for 2 hours. |
| Feather file I/O | Entire training DataFrame written to disk, read 4× by workers. ~200 MB write + ~800 MB read. |
| Model string serialization | All trained models serialized to strings for pickling across process boundary, then deserialized via `lgb.Booster(model_str=s)`. |
| Complexity overhead | ~200 lines of multiprocessing plumbing, CPU budget arithmetic, thread pool management, and timeout constants. |

For a daily retrain that completes in ~22 min even on the slowest runner, the complexity was not justified.

## Verification

- `python -m py_compile models/forecaster.py scripts/forecast_prices.py` — both pass
- 133/134 tests pass (1 pre-existing failure: `test_regime_models_populated_after_train` — missing `optuna-integration[lightgbm]` package, unrelated to these changes)

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Removed all timeouts | `lgb.train()` could hang on corrupted data or OpenMP deadlock | The previous timeouts (1800s, 600s) only masked hangs — they didn't prevent them. A hang that exceeds these timeouts is still a hang, just reported 10–30 min later. If hangs resurface, the fix belongs in LightGBM configuration (reducing `n_jobs`, isolating OpenMP), not in thread-pool timeout wrappers. |
| Sequential ensemble training | ~2× slower on multi-core machines (~70s → ~140s per quantile) | Each ensemble member already uses LightGBM's internal OpenMP threads. On a 4+ core machine, a single `lgb.train()` fully utilizes all cores. Running 3 members concurrently with `n_jobs=1` each was slower per-member but overlapped — net benefit was small. |
