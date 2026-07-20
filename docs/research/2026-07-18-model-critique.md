# Model & Predictor Critique — Speed, Accuracy, and Priority

**Date:** 2026-07-18  
**Context:** Audit of the LightGBM quantile regression forecasting system after the column-order-bug fix and post-July-17 retrain.

> **Note:** Some issues noted here were fixed shortly after:
> - `fold_count=0` CV bug → hard error added
> - 2026 distribution-shift guard → switched from `.dt.year` to `pd.DatetimeIndex().year`
> - `predict()` timing → instrumented with logs

---

## Training Speed

| Mode | Time | Bottleneck |
|------|------|------------|
| Warm (HP cached) | ~5.7 min | Feature engineering (~2 min), ensemble training (~3 min) |
| Cold (full Optuna) | ~30–45 min | Feature engineering (~25 min), Optuna HP search (~8 min), CV + calibration (~1 min) |

Per the July 16 train log (`19:41 → ~20:16`):
- `fetch_price_history`: ~5 min (Parquet UNION across 12 files, 2.9M rows voted → 2.9M)
- `engineer_features`: ~25 min — **dominant cost**. Includes 90+ features across 8 categories, event decay, rolling stats.
- Optuna per quantile: ~15 sec/trial × 8 trials × 3 quantiles = ~6 min per horizon
- Permutation pruning + retrain: adds ~3 min per horizon when triggered (pruning 81→43 features and retraining all quantile ensembles)

Warm retrain reuses cached Optuna params, so it skips the HP search (~8 min saved) and only runs ensemble training + CV. If pruning is also skipped (via fix), warm could drop to ~4 min.

## Prediction Speed

Not instrumented with timestamps — **should be added.** Estimated breakdown:

| Scenario | Time | Notes |
|----------|------|-------|
| Cache hit (`engineered_data.parquet` fresh) | <10 sec | LGBM inference on 1,500 items × 124 features is sub-second per model (12 model groups × 6 ensembles = 72 predict calls) |
| Cache miss (stale >3d or missing) | ~30 min | Full feature pipeline from scratch — dangerous in `--predict-only` mode |
| DB upsert (regime + global) | ~2 sec | Batch upsert of ~6,000 forecast rows |

The cache dependency is a latent risk: a cold-start predict on a production schedule could stall for 30 minutes with no warning.

## Accuracy — Real Numbers (post-bug-fix, trustworthy)

| Horizon | Dir. Accuracy | Baseline | Improvement | MAE | Interval Coverage | Status |
|---------|-------------|----------|-------------|-----|-------------------|--------|
| **3d** | **60.6%** | 50% | +10.6pp | $0.74 | ~50% | **Usable** |
| **7d** | **53–62.1%** | 50% | +3 to +12pp | $0.75 | ~50% | **Regressed** (was 62.1%, now ~53%) |
| **14d** | **53.4%** | 50% | +3.4pp | $0.76 | ~48% | **Weak** |
| **30d** | **42.5%** | 50% | **-7.5pp** | $0.77 | ~43% | **Worse than random** |

### What's working

- **3d at 60.6%** is genuinely useful (+10.6pp over 3-class baseline). Good for near-term trading signals.
- **7d at 62.1% pre-regression** was a strong signal. Recovering this is the highest-value fix.
- **Confidence calibration** works: "high" confidence predictions hit 80%+ accuracy in CV. If this holds in backtest (unconfirmed), the binary high/low label is trustworthy.
- **MAE of $0.74–0.77** is reasonable for a dataset spanning $0.03–$2,000+ (driven by long tail of cheap skins).
- **Regime-switching** is architecturally sound but unevaluated in production — could add +2–4pp in volatile periods.

### What's broken

1. **30d is worse than random.** The model should be discarded for 30d until fixed. Pruning collapsed it to ~4 features → no signal survives.
2. **7d regressed ~9pp.** The dead-item-filter retrain triggered a cascade: broken 2026 distribution-shift guard → sparse 2026 data in validation → permutation pruning on noise → feature collapse.
3. **CV is over-optimistic.** CV reports ~68% across all horizons, backtest reality is 42–62%. The `fold_count=0` bug meant CV silently fell back to a single train/val split with misleading accuracy. Already called out in the priority doc.
4. **Interval coverage is poor** at 43–60% for nominal 90% intervals. The quantile crossing fix (imputing average half-width) is a band-aid — crossing rates >1% suggest the tail quantiles aren't learning well.
5. **Feature pruning destroys models on thin data.** Permutation importance on ~350 rows is pure noise. 14d/30d went from 43 features → 4 features with no warning that this was pathological.

### Architectural concerns

| Concern | Impact |
|---------|--------|
| **No timing in `predict()`** | Can't confidently say how long inference takes; cache-miss scenario is a production landmine |
| **6 ensemble members** | Adds complexity but only ~1–2pp vs 3 members (unverified); mostly for model-card robustness |
| **forecast blending (0.15 weight)** | Reduces flip-flopping but adds 1-day lag to direction changes; no evaluation of the trade-off |
| **Regime models cost 2x training** | ~+23 min for what may be marginal gains; not yet A/B tested in production |
| **Feature cache staleness (3d)** | If the daily `--predict-only` run hits a stale cache, it silently rebuilds for 30 min — no user-facing notification |
| **CV fold_count=0 not caught** | Months of training with misleading CV metrics. Should be a hard error. |

## Priority vs the model-fixes-priority doc

Agree with the ordering in `model-fixes-priority.md`:

1. ~~**Fix 2026 guard** (one line, zero time cost, recovers 7d ~9pp) — the `.dt.year` dtype issue needs debugging first~~ **RESOLVED** — switched from `.dt.year` to `pd.DatetimeIndex().year` for consistent dtype behavior; see changelog
2. **Raise validation-set floor** — require ≥2000 rows or ≥7 distinct dates before trusting permutation tests
3. **Gate permutation pruning conservatively** — require statistical significance, or skip pruning entirely on thin windows
4. **Hard-fail zero-fold CV** — stop trusting CV numbers that were never computed
5. **Increase Optuna trials** (20→50) for marginal +0.5–1pp on cold retrains only

## Recommendation

- **Drop 30d forecasts from the frontend** until the feature-collapse bug is fixed. They're worse than coin-flip and damage user trust.
- **Instrument `predict()` with timing logs** at the feature-load, inference, and DB-write stages. This is a quick win.
- **Add a cache-freshness warning** that fires when `--predict-only` triggers a full rebuild.
- **After Tier 1 fixes land, re-evaluate whether 14d/30d are worth keeping.** Skin markets past 2 weeks are dominated by unforecastable events (major drops, pro-player wins, trade bans). The ceiling may simply be lower than 50%.
- **A/B test regime-switching** only after 3d/7d are solid. Don't add the ~23 min training cost until you know the base models are trustworthy.
