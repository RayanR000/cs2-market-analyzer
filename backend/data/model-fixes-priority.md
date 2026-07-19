# Prediction Model — Priority Fixes

**Created:** 2026-07-17
**Status:** Items 1–3 resolved; items 4–6 planning
**Context:** Warm retrain is ~5.7 min against a 20–30 min budget. The model is **not time-constrained — it is correctness-constrained.** Spend the headroom on robustness, not more boosters.

## Current state (trustworthy numbers only)

Only the post-column-order-bug numbers from `docs/changelog/2026-07-17-retrain-and-backtest-baseline.md` are valid. Everything before 2026-07-17 was trained on `volume` mislabeled as `price`.

| Metric | Value |
|---|---|
| Training (warm, HP cached) | ~5.7 min |
| Training (cold, full Optuna) | ~30–45 min |
| 6-fold CV dir. accuracy | ~68% all horizons |
| Real backtest 3d / 7d / 14d / 30d | **60.6 / 62.1 / 53.4 / 42.5%** |
| MAE | $0.74–0.77 |
| Interval coverage | 43–60% |

Three problems drive this plan:
1. **7d regression is live and unfixed** — 62.1% → 53.0% after the dead-item-filter retrain.
2. **14d/30d models pruned to just 4 features** — same root cause as the 7d collapse.
3. **CV (68%) vs backtest (42–62%) gap** — CV is over-optimistic; last run had `fold_count=0` (silent fallback to single split).

Root cause common to #1 and #2: **the model makes pruning/calibration decisions off validation sets too small to be trustworthy.**

---

## Tier 1 — Fix what is actively broken (biggest wins, ~zero training-time cost)

### ~~1. Fix the 2026 distribution-shift guard~~ RESOLVED

Applied in two commits:
- `56ff0b7` — moved guard before subsampling, removed `month < 6` check
- Follow-up (2026-07-18) — switched to `pd.DatetimeIndex().year` to eliminate `.dt` dtype instability

Guard now correctly excludes all incomplete 2026 data. Investigation confirmed all three hypotheses were addressed.

### ~~2. Raise the validation-set floor~~ **RESOLVED** (commit `56ff0b7`)
Changed `val_set < 100` to `len(val_set) < 2000 or val_dates < 7` in both the temporal-split fallback (`forecaster.py:1641`) and the feature-group validation skip (`forecaster.py:1843`).

### ~~3. Gate permutation-pruning conservatively~~ **RESOLVED** (commit `56ff0b7`)
Permutation pruning is now skipped entirely when the validation window is thin (same ≥2000 rows / ≥7 dates threshold). The retrain-after-prune safety net (7 core features) was already present.

---

## Tier 2 — Close the CV ↔ backtest gap (spend the time budget here)

### 4. Make CV the metric we trust
`meta.json` showed `fold_count=0` last run — CV silently produced no folds and calibration fell back to a single split.

- **File:** `backend/models/forecaster.py` (`_compute_cv_splits` ~1070, `_cv_evaluate_horizon` ~2017)
- **Change:** run more/larger expanding-window folds; make a **zero-fold CV a hard failure**, not a silent fallback.
- **Cost:** more folds add time but stay well within the 20–30 min budget.

### 5. More Optuna trials on cold retrains
- **File:** `backend/models/forecaster.py` (`_optuna_search_params` ~1089)
- **Change:** 20 → 50 trials. HP results are cached, so this only costs time on the Monday cold run.
- **Expected impact:** +0.5–1pp (per `docs/research/2026-07-14-remaining-accuracy-improvements.md`).

---

## Tier 3 — Genuine accuracy levers (after Tier 1/2 land)

### 6. Regime-switching models
- Docs' top remaining item: +1–2pp avg, +2–4pp in volatile periods.
- **Cost:** ~+200% training time — still within 30 min.
- **Ref:** `docs/research/accuracy-opportunities.md` (#7)

### Do NOT pursue (docs already ruled these out)
- No neural models (N-BEATS/PatchTST) unless plateaued.
- Never revisit CatBoost (−18 to −20pp).
- Never add trade/sales volume (|r| < 0.002).
- Remember the calibration reality-check: proxied signals deliver ~10–20% of estimated gains; don't over-invest.

---

## Suggested order

1. Fixes **1 → 2 → 3** — **done** (commit `56ff0b7`, follow-up `b165476`). Ready for retrain to confirm 7d recovery and 14d/30d feature restoration.
2. Next: **4 → 5** to align CV with reality.
3. Only then evaluate **6**.

**Bottom line:** Don't add model capacity. Fix the validation/pruning pipeline first — it likely recovers several points across horizons at essentially no training-time cost.
