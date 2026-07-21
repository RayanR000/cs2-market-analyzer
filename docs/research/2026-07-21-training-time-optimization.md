# Training Time Optimization: 64 min → ~14 min

**Date:** 2026-07-21
**Goal:** Aggressively shorten retrain time while minimizing accuracy loss (est. -0.3 to -1.1pp)

---

## Current Breakdown

| Phase | Time | % | Bottleneck |
|-------|:----:|:-:|------------|
| Optuna HP search | ~38 min | 59% | 3d=50 trials × 3 quantiles @ 200 rounds each; pruning is dead code (`trial.report()` at step=0 with `n_warmup_steps=5`) |
| Ensemble training | ~16 min | 25% | Sequential Python loop: 36 models (4 horizons × 3 quantiles × 3 members), up to 1000 rounds each |
| Regime models | ~5 min | 8% | bear/range/bull duplicates ensemble training |
| Data + features | ~3.5 min | 5% | DuckDB Parquet scan + rolling windows |
| CV + calibration | ~1.5 min | 2% | 6 expanding-window folds |
| **Total** | **~64 min** | 100% | |

---

## Changes (single file: `backend/models/forecaster.py`)

### E. Fix Optuna Pruning (lines 1636–1656)

**Bug:** `trial.report(score, 0)` at step=0 + MedianPruner with `n_warmup_steps=5` → pruning never fires.

**Fix:** Use `LightGBMPruningCallback` (auto-reports every iteration) + switch to `HyperbandPruner`.

```python
from optuna.integration import LightGBMPruningCallback

# Replace the objective's lgb.train block:
opt_callbacks = [
    lgb.log_evaluation(0),
    LightGBMPruningCallback(trial, "quantile"),
]
if boosting_type != "dart":
    opt_callbacks.insert(0, lgb.early_stopping(20))
model = lgb.train(params, dtrain, num_boost_round=200,
                  valid_sets=[dval], callbacks=opt_callbacks)
return model.best_score["valid_0"]["quantile"]

# Replace pruner:
pruner = optuna.pruners.HyperbandPruner(
    min_resource=5, max_resource=200, reduction_factor=3
)
```

**Save:** ~10 min. **Risk:** Low (official integration).

---

### F. Freeze 3d Params (lines 151, 2296–2302)

Add 3 to `SKIP_HP_HORIZONS`:
```python
SKIP_HP_HORIZONS = [3, 14, 30]  # was [14, 30]
```

Update fallback defaults to match the validated warm-start params from the 50-trial depth experiment:
```python
# Lines 2296-2302 replacement:
base_params["num_leaves"] = 47     # was 31
base_params["learning_rate"] = 0.01  # was 0.03
base_params["lambda_l1"] = 0.0      # was 0.5
base_params["lambda_l2"] = 1.5      # was 0.5
```

**Save:** ~8 min (3d was 50 trials × 3 quantiles). **Risk:** Low (warm-start validated).

---

### G. GOSS Instead of Bagging (lines 1631–1634, 2265–2268, 2288–2292)

Replace `bagging_fraction` + `bagging_freq` with `data_sample_strategy='goss'`.

**In Optuna params (line 1631-1634):**
```python
"min_gain_to_split": 0.1,
"feature_fraction": 0.7,
"data_sample_strategy": "goss",
"top_rate": 0.2,
"other_rate": 0.1,
```

**In base params (lines 2265-2268):** same swap.

**Remove from merge_keys (line 2290):** `"bagging_fraction"`.

**Remove from warm-start enqueue (line 1669):** `"bagging_fraction": 0.7` line.

**Save:** ~3 min. **Risk:** Medium (GOSS vs bagging accuracy unknown for this dataset).

---

### H. Parallel Ensemble Training (lines 2322–2328, 2391–2397)

Train 2 ensemble members concurrently with `n_jobs` scaled down per worker:

```python
from concurrent.futures import ThreadPoolExecutor
import os

n_workers = min(self.N_ENSEMBLES, max(1, (os.cpu_count() or 4) // 2))
cpu_per_worker = max(1, (os.cpu_count() or 4) // n_workers)

ensemble_models = []
with ThreadPoolExecutor(max_workers=n_workers) as pool:
    futures = []
    for ei in range(self.N_ENSEMBLES):
        p = pq.copy()
        p["random_state"] = self.ENSEMBLE_SEEDS[ei]
        p["feature_fraction"] = self.ENSEMBLE_FEATURE_FRACTIONS[ei]
        p["n_jobs"] = cpu_per_worker
        futures.append(pool.submit(self._train_ensemble_member, p, dtrain, dval, boost_rounds))
    for f in futures:
        ensemble_models.append(f.result())
```

Same pattern for regime ensemble (lines 2391–2397).

**Save:** ~5 min. **Risk:** Medium (thread safety — Dataset objects are read-only after creation).

---

### I. Skip Regime + Feature Val on Warm Retrain (lines 2353, ~2478)

```python
# Line 2353:
if os.environ.get("SKIP_REGIMES") == "1" or _warm_retrain:

# Before feature validation block (~2478):
if _warm_retrain:
    logger.info("  Skipping feature-group validation (warm retrain)")
elif len(val_set) < 2000 or val_dates < 7:
    ...
```

**Save:** ~4 min. **Risk:** Low.

---

### J. Reduce 7d Optuna Rounds (lines 1644–1648)

```python
_num_rounds = 100 if horizon == 7 else 200
model = lgb.train(params, dtrain, num_boost_round=_num_rounds, ...)
```

**Save:** ~1 min. **Risk:** Low (pruning already stops early).

---

## Time Budget (After All Changes)

| Phase | After | Notes |
|-------|:-----:|-------|
| Data loading | ~2 min | Fixed cost |
| Feature engineering | ~1.5 min | Fixed cost |
| Optuna (7d only, 15×3) | ~2 min | Hyperband prunes bad trials, 100 rounds |
| Ensemble (parallel 2-wide) | ~6 min | 36 models → 18 sequential groups × 2 parallel |
| Regime models | ~0.5 min | Skipped on warm retrain |
| CV + calibration | ~0 | Skipped on warm retrain |
| **Full retrain** | **~14 min** | First time or forced |
| **Warm retrain** | **~10 min** | Cached HP + skip regime/CV |

---

## Accuracy Risk

| Change | Est. DA Impact | Rationale |
|--------|:-------------:|-----------|
| E. Fix pruning | +0 to +0.3pp | Hyperband finds better params faster |
| F. Freeze 3d params | -0.1 to -0.3pp | May miss slightly better combos |
| G. GOSS | +0 to -0.5pp | LGBM paper: "almost same accuracy" |
| H. Parallel ensemble | 0pp | Identical training |
| I. Skip regime/val | -0.1 to -0.3pp | Rare regimes have limited impact |
| J. 7d rounds 100 | -0.1pp | Early stopping covers this |
| **Total** | **-0.3 to -1.1pp** | |

---

## Refs

- `backend/models/forecaster.py` — all changes in this file
- LightGBM GOSS: https://lightgbm.readthedocs.io/en/latest/Parameters.html#data_sample_strategy
- Optuna HyperbandPruner: https://optuna.readthedocs.io/en/stable/reference/generated/optuna.pruners.HyperbandPruner.html
- Optuna LightGBMPruningCallback: https://optuna.readthedocs.io/en/stable/reference/generated/optuna.integration.LightGBMPruningCallback.html
