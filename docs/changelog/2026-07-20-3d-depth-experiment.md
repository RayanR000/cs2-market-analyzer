# 3d horizon depth experiment + Optuna trial budget fix

**Date:** 2026-07-20

**Files changed:**
- `backend/models/forecaster.py` — added `N_TRIALS_MAP` with 50 trials for 3d horizon
- `backend/scripts/3d_depth_experiment.py` — A/B walk-forward CV comparison (added, can be removed after confirming)
- `backend/scripts/optuna_3d_search.py` — focused 50-trial Optuna search for 3d (added, can be removed after confirming)

---

## What

Investigated whether the 3d model's shallow depth (max_depth=3, no regularization) was a genuine optimum or an artifact of Optuna's 15-trial budget across a 6-dimensional search space (~40k combinations).

### Phase 1: Walk-forward CV A/B comparison

26-fold expanding-window CV on 200 items (109k samples), comparing shallow (depth=3, leaves=15, no reg) vs deep (depth=6, leaves=47, reg=0.5):

| Metric | Shallow | Deep | Δ |
|--------|---------|------|---|
| Weighted DirAcc | 67.3% | 67.9% | +0.56pp (SD=3.00pp) |
| Pinball@50 | 2.404 | 2.365 | −0.039 |
| Interval Coverage | 86.7% | 85.6% | −1.0pp |
| **$5–20 tier DirAcc** | 58.0% | 60.7% | +2.7pp |
| **$20–100 tier DirAcc** | 60.5% | 61.7% | +1.2pp |

Deep won 15/26 folds (57.7%). Per-fold SD of 3.00pp means the paired difference is ~1σ — suggestive but not conclusive on its own. The $5–100 tier breakdown (+2.7pp) was the strongest signal but is a subgroup finding from a marginal overall effect.

### Phase 2: Optuna with a proper trial budget

Ran the full HP search for the 3d horizon with 50 trials (vs 15 previously):

| Quantile | max_depth | num_leaves | l1 | l2 | lr |
|----------|-----------|------------|----|----|----|
| p10 | **8** | 31 | 0.5 | 0.5 | 0.010 |
| p50 | **5** | 47 | 0.0 | 1.5 | 0.010 |
| p90 | **7** | 23 | 2.0 | 1.0 | 0.054 |

None chose depth=3. All three quantiles converged to depths 5–8 with non-zero regularization. The search trajectories showed TPE finding depth=3 in early random samples but consistently beating it as the surrogate model learned.

## Why

15 trials is insufficient for a 6-parameter search with ~40k valid combinations. The TPE sampler starts with quasi-random initialization — with 15 trials, the initial random batch (~10 trials) may not cover the high-depth region, and the remaining ~5 trials lack the budget to escape the initial local neighborhood.

## Key findings

1. **Depth=3 was a config accident** — not a signal ceiling. With 50 trials, Optuna consistently chose deeper trees.
2. **p50 settled at depth=5** with strong L2=1.5 — exactly the depth the evaluation scripts had hardcoded as their "fixed tuned params."
3. **The original "no regularization" choice was also an artifact** — all three quantiles chose non-zero l1/l2.
4. **No hardcoding needed** — 50 trials is enough for the search to find deeper structures on its own.

## Code change

Added `N_TRIALS_MAP` to `ItemForecaster`:

```python
N_TRIALS_MAP = {3: 50, 7: 15, 14: 15, 30: 15}
```

Threaded `n_trials` through `_optuna_search_params()` and updated the call site in `train()`. 3d now gets 50 trials; other horizons keep 15.
