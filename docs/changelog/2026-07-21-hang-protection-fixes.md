# Hang protection fixes — eight blocking-level hang sources fixed in retraining pipeline

**Date:** 2026-07-21

**Files changed:**
- `backend/models/forecaster.py` — 7 hang/crash fixes (timeouts, platform-aware multiprocessing, CUDA probe, DuckDB memory, corrupt model handling)
- `backend/db/parquet.py` — `_append_parquet()` rewritten to use DuckDB-native operations, avoiding loading the full file into Python memory
- `backend/scripts/forecast_prices.py` — DB connection health check before batch insert + retry logic per batch

---

## What changed

The previous commit (172f848) introduced parallelism into model training — `ThreadPoolExecutor` for ensemble members, `Pool.map()` for multi-horizon training — but deployed these without any hang protection. Eight specific hang/crash sources were identified and fixed.

### `backend/models/forecaster.py` — 7 fixes

**Fix 1 — `ThreadPoolExecutor.f.result()` timeout on ensemble training** (lines 2363, 2444)  
`f.result()` was unbounded — if any LightGBM `train()` call hung (e.g., OMP deadlock, GPU driver issue), the process would block indefinitely with no error. Changed to `f.result(timeout=1800)` with `try/except TimeoutError` and descriptive `logger.error` messages before re-raise. The 30-minute timeout is ~3× the expected max ensemble training time.

**Fix 2+3 — `Pool.map()` replaced with `map_async().get(timeout=7200)`** (lines 2144–2158)  
`mp.get_context("fork").Pool().map()` has no timeout mechanism — if a worker process deadlocks, the parent hangs forever. Replaced with:
- Platform-aware context selection: `spawn` on Windows (where `fork` doesn't exist), `fork` elsewhere (for copy-on-write speed)
- `pool.map_async().get(timeout=7200)` for a 2-hour wall-clock timeout covering all 4 horizons

The 2-hour timeout is ~2× the expected max cold retrain time on slow hardware.

**Fix 4 — `lgb.train()` timeouts in Optuna HP search and CV evaluation** (lines 1668, 3123)  
The `lgb.train()` calls inside Optuna trials (line 1651) and the expanding-window CV evaluation (line 3099) have no timeout — a single trial or fold could hang forever on problematic data. Wrapped both with `ThreadPoolExecutor(max_workers=1).submit().result(timeout=600)` for a 10-minute per-call timeout (normal trial time: 10–30s, worst case: ~2 min).

**Fix 5 — DuckDB `fetchall()` → `fetchdf()` + CUDA probe** (lines 522–542)  
Three changes in one:
- Changed the critical Parquet data load from `con.sql(...).fetchall()` → `.fetchdf()` to avoid creating an intermediate Python tuple list before the DataFrame, saving ~2× memory on the 5M+ row load. The old code explicitly did `df = pd.DataFrame(rows, columns=...)` then `del rows` — using `fetchdf()` skips the tuple list entirely.
- Added `import sys` and a subprocess-based CUDA probe to `_gpu_available()` so spawned workers correctly detect CPU-only LightGBM builds. Directly calling `lgb.train(device="cuda")` in-process segfaults if the pip wheel is CPU-only — the subprocess isolates this crash.
- Added `os.environ["CUDA_VISIBLE_DEVICES"] = ""` in `_train_horizon_worker` to force CPU training in all worker processes regardless of the parent's GPU state.

**Fix 7 — `lgb.Booster(model_file=...)` wrapped in try/except** (lines 3636, 3640, 3674)  
Corrupted model files (truncated writes from a previous crash, mismatched LightGBM versions) cause `lgb.Booster(model_file=path)` to throw `LightGBMError` — previously unhandled, causing the entire prediction run to abort. Wrapped all three occurrences (global ensemble, non-ensemble fallback, regime ensemble) in `try/except (lgb.basic.LightGBMError, Exception)` with `logger.warning` to skip corrupt files gracefully.

### `backend/db/parquet.py` — Fix 6

**`_append_parquet()` rewritten** to use DuckDB-native `COPY TO` with an anti-join for deduplication instead of the old pattern:
- Old: `duckdb.connect().sql("SELECT * FROM read_parquet(...)").fetchdf()` → `pd.concat()` → `pd.drop_duplicates()` → `pd.to_parquet()`
- New: `COPY (SELECT * FROM _new UNION ALL SELECT * FROM existing WHERE NOT EXISTS (anti-join)) TO '...' (FORMAT PARQUET)`

The old implementation loaded the entire existing Parquet file into Python memory as a DataFrame. For ops tables approaching 100 MiB (e.g., `item_forecasts.parquet`), this was the memory bottleneck during forecast persistence. The new approach keeps all data processing within the DuckDB C++ engine — the only Python-side data is the new rows being appended.

### `backend/scripts/forecast_prices.py` — Fix 8

**DB connection health check + per-batch retry** added to `_write_forecasts_to_db`:
- Added `db.execute(text("SELECT 1"))` before the batch insert loop to detect stale connections after long training runs (training can take >1h, and the connection may have gone stale, particularly behind PgBouncer or during Supabase connection pool rotation).
- Each batch insert is now wrapped in `try/except` with `db.rollback()`, `db.close()`, session recreation via `SessionLocal()`, and a single retry — this mirrors the pattern already used elsewhere in the codebase for transient DB failures.

## Why

The previous commit (172f848) introduced parallelism — `ThreadPoolExecutor` for ensemble members, `Pool.map()` for multi-horizon training — to reduce total retrain time. But it deployed these without any hang protection:

- `Pool.map()` has no timeout — a single deadlocked worker process blocks the entire retrain forever
- `f.result()` has no timeout — a hanging `lgb.train()` call blocks the ensemble forever  
- `lgb.Booster(model_file=...)` silently crashes on truncated model files
- The old `_append_parquet()` could OOM on large ops tables during forecast persistence
- Stale DB connections after 53+ min training caused `_write_forecasts_to_db` to fail silently with unhelpful `SSL SYSCALL` / `connection closed` errors

These are not hypothetical edge cases — they were encountered in production during the 2026-07-20 full retrain cycle. The 180-minute GHA workflow timeout served as the sole safety net, meaning a stuck training run burned 3 hours of runner time before being killed, and that failure could not be programmatically handled (no partial save, no error reporting, no automatic retry).

## Verification

- `python -m py_compile backend/models/forecaster.py backend/db/parquet.py backend/scripts/forecast_prices.py` — all three pass
- 83/84 forecaster tests pass (the 1 pre-existing failure on Windows: `fork` context unavailable — the original code also failed here)
- The previously broken `test_regime_models_populated_after_train` test now runs further (actual training completes) vs. dying immediately on `fork` context creation

## Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| `spawn` context on Windows | LightGBM access violation on some Windows builds with mismatched OpenMP runtime | Falls back to `fork` on Linux/macOS where it's safe; CUDA probe + disable in workers avoids GPU-related crashes |
| `timeout=1800` on ensemble | Ensemble training may abort if running on extremely slow hardware | 30 min is 3× the expected max ensemble time (10 min on Mac with 9 ensembles); if triggered, the error propagates clearly with a descriptive message |
| `timeout=7200` on horizon pool | Entire retrain may abort | 2h is ~2× expected max cold retrain time (53 min on Mac with regime models) |
| `timeout=600` on Optuna/CV | A trial or fold may abort prematurely | 10 min per trial is generous (normal: 10–30s; worst case: ~2 min for 200 rounds on dense data) |
| `_append_parquet` DuckDB rewrite | DuckDB version compatibility | Uses basic DuckDB SQL (`COPY TO`, `read_parquet`, anti-join) available since DuckDB 0.8; no version-specific features |
| `fetchall()` → `fetchdf()` | Column name mismatch | `fetchdf()` preserves SELECT aliases as column names; explicitly renamed with `df.rename(columns={"item_slug": "item_id", "day": "timestamp"})` |
| Subprocess CUDA probe | 30s added latency on GPU machines | Only called once per process on cold start; the 30s timeout is conservative — actual probe completes in ~2s on GPU, ~0.5s on CPU |
