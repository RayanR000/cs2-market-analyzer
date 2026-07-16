# Remaining Accuracy Improvements

Current accuracy (post item-type features): 60-68% directional across horizons (~10-18pp above 50% baseline).

Below are the remaining opportunities, grouped by estimated impact and effort.

---



## Completed

### 1. Player count feature ✅

**Status:** Implemented and backfilled. See `docs/2026-07-15-player-count-backfill-and-ab-test.md`.

**Actual impact:** **Zero** — permutation test showed the +3pp A/B delta was spurious (extra model capacity, not causal signal). See `docs/2026-07-15-player-count-backfill-and-ab-test.md#permutation-test-causality-check`.

**Key files:**
- `scripts/backfill_player_counts_to_parquet.py` — historical DB → Parquet
- `collectors/player_counts.py` — ongoing collection
- `models/forecaster.py` — `_fetch_player_counts()`, `_add_player_count_features()`
- `.github/workflows/aggregator-update.yml` — daily Parquet append

---



### 2. Supply-side features (rarity, weapon_type, weapon-type cross-sectional) ✅

**Status:** Implemented and A/B tested. See `docs/changelog/2026-07-15-supply-side-features.md`.

**Actual impact:** **+0.66pp avg** directional accuracy (3d: +1.92pp, 7d: -0.16pp, 14d: +0.79pp, 30d: +0.08pp). Below the 3-6pp estimate because existing features already capture much of the signal. Impact concentrated at short horizons.

**Key files:**
- `models/steam_types.py` — Steam type field parser (rarity + weapon_type extraction)
- `scripts/backfill_supply_metadata.py` — backfill script (catalog → Parquet + DB)
- `models/forecaster.py` — `_fetch_supply_metadata()`, `_add_supply_side_features()`, `_add_weapon_type_cross_sectional_features()`
- `price-archive/item-metadata.parquet` — 8,691 items, 109 KB

---



### 3. Permutation-based feature validation + auto-prune (DONE ✅)

**Replaces:** the original SHAP-based elimination idea.

Built into `train()`: after CV, `_validate_feature_groups()` runs a fast permutation test on each feature group (e.g., `player_counts`, `price_technicals`, `events`) using the held-out validation set. Groups that drop less than 0.5pp when shuffled are flagged.

`prune_failed_groups=True` (default): when a group fails validation, its features are removed and the horizon is **retrained** without them. This prevents the spurious-accuracy-from-extra-capacity problem automatically.

**Configuration:** `ItemForecaster(db, prune_failed_groups=False)` to disable auto-prune during debugging.

---



### 4. Event decay optimization (DONE ✅)

**Status:** Implemented — coordinate-wise grid search over tau values (major=30-180, operation=7-60, case_drop=3-45, update=2-21, game_update=1-14), then validated via full walk-forward A/B.

**Actual impact:** **Zero** — the walk-forward test showed the "optimal" taus (operation: 21→45) degraded accuracy by -0.57pp mean. The domain-informed defaults were already close to optimal. See `scripts/optimize_event_decay.py` and `scripts/compare_event_decay.py`.

**Key changes:**
- `models/forecaster.py` — `decay_constants` refactored from hardcoded dict inside `_add_event_features()` to instance attribute `self.event_decay_constants`, enabling easy swapping
- `scripts/optimize_event_decay.py` — coordinate-wise tau grid search (fast single-split mode)
- `scripts/compare_event_decay.py` — walk-forward A/B comparison harness

**Costs incurred:** None (defaults unchanged, just added scripts + refactor).

---



## Moderate Impact (~1-4pp potential)

### 5. Multi-horizon consistent training

Currently each horizon (3d, 7d, 14d, 30d) is trained independently. A single model predicting all four horizon returns simultaneously would force shared representations of market dynamics and naturally enforce consistency (e.g., 3d direction ≤ 7d direction ≤ 30d direction).

**Implementation:**
- Multi-output regression target: `[target_return_3d, target_return_7d, target_return_14d, target_return_30d]`
- Sum of quantile losses across horizons as objective
- Or train a single model with horizon as a categorical feature

**Effort:** Medium (restructure target prep, model output, and inference)
**Impact estimate:** +2-4pp

**Already documented in:** `docs/2026-07-11-accuracy-improvement-brainstorm.md` (Item #13)

**Costs:** Training time increases ~4x (one model per quantile vs per horizon×quantile). Inference unchanged.

---



### 6. Listing count feature

Number of active Steam market listings at prediction time is a powerful short-term signal — items with few listings can spike on single buys, while oversupplied items face downward pressure.

**Implementation:**
- CSMarketAPI's `/v1/items` endpoint returns `listing_count`
- Collect during aggregator runs, store in a table
- Join as a daily feature

**Effort:** Medium (requires aggregator changes + new table)
**Impact estimate:** +3-8pp (speculative, depends on data quality)

**Costs:** Adds ~1-2 new columns, negligible training impact. Requires ongoing API calls during aggregator runs.

---



## Deeper Architectural Changes (higher effort)

### 7. Item-type sub-models

Instead of one-hot encoding type as a feature, train separate LightGBM models per item category (skin model, sticker model, case model, etc.). Each model would specialize in its category's dynamics.

**Pros:**
- Captures category-specific feature interactions without global tree splits
- Each model can have its own hyperparameters

**Cons:**
- 5x model count (180 total instead of 36)
- Requires sufficient training data per category
- More complex deployment

**Effort:** High (significant refactor of training/prediction pipeline)
**Impact estimate:** +2-5pp

**Already documented in:** `docs/2026-07-11-accuracy-improvement-brainstorm.md` (Item #14)

**Costs:** 5x more models = 5x training time and 5x memory for inference. Redundant for categories with few items.

---



### 8. Conformal prediction

Replace the ad-hoc quantile monotonicity fix (`np.minimum(p10, p50)`, `np.maximum(p50, p90)`) with proper conformal prediction on the validation set. Gives distribution-free coverage guarantees and avoids distorting quantile identities.

**Implementation:**
- Compute nonconformity scores on validation set
- Calibrate prediction intervals at target coverage levels
- Replace `_enforce_quantile_monotonicity` with conformal intervals

**Effort:** Medium (new calibration logic, integration with existing pipeline)
**Impact:** Better calibrated intervals (not necessarily higher directional accuracy)

**Already documented in:** `docs/2026-07-11-accuracy-improvement-brainstorm.md` (Item #12)

**Costs:** Negligible — calibration runs once per training, adds milliseconds to inference.

---



### 9. Expanded training window (730d → 1460d+)

Currently training on 730 days of data. The parquet archive has data back to 2013. Longer training windows would capture more complete market cycles (multiple operation peaks, summer troughs, etc.), especially for the 30d horizon.

**Implementation:**
- Change `days_back=730` to `days_back=1460` in `train()` and `build_training_data()`
- May need to increase max_rows or add downsampling for old data

**Effort:** Low (single parameter change)
**Impact estimate:** +1-2pp (speculative — more data may not help if patterns have regime-shifted)

**Costs:** Training time increases ~2x (more rows to process). Memory proportional to row count. May need duckdb query performance tuning.

---



### 10. Optuna trial count increase

Currently 15 Optuna trials per quantile per horizon (60 total). Increasing to 30-50 trials would find better hyperparameters, especially for the larger search space.

**Effort:** Trivial (parameter change)
**Impact estimate:** +0.5-1pp (diminishing returns)

**Costs:** Training time increases proportionally (2-3x for 2-3x trials). Training already takes ~5-10 min per quantile×horizon.

---



## Cost summary: accuracy vs training time

| Improvement | Accuracy | Training time | Other costs |
|---

---

---

---

-|:---

---

--:|:---

---

---

---

-:|---

---

---

---

-|
| Player count | 0pp | +2-5% | API collection, Parquet storage |
| Supply-side | +0.66pp | +5-10% | Backfill script, Parquet (109 KB) |
| Auto-prune | Prevents overfit | +10-20% | Validation after each horizon |
| Event decay | 0pp (reverted) | — | None (script-only) |
| Multi-horizon | +2-4pp est. | **+300-400%** | Structural refactor |
| Listing count | +3-8pp est. | +1-2% | New data collection pipeline |
| Sub-models | +2-5pp est. | **+500%** | 5x model count, deployment complexity |
| Conformal pred | Intervals only | Negligible | New calibration logic |
| More training data | +1-2pp est. | +100% | Memory, DuckDB tuning |
| More HP trials | +0.5-1pp est. | +200-300% | None |

Training time is roughly linear in feature count, row count, and model count. Paying the time cost is worth it when the accuracy improvement is real (supply-side: +0.66pp for +5-10% time). Features that fail validation (like player counts) get auto-pruned, so their time cost is only paid during the first training run.

## Summary priority matrix

| # | Improvement | Effort | Impact | Training time penalty | Data needed? | Already noted? | Status |
|---

|---

---

---

---

-|---

---

--|:---

---

:|:---

---

---

---

---

---

---

:|:---

---

---

---

:|:---

---

---

---

--:|:---

---

:|
| 1 | Player count | Low | 0pp | +2-5% | Collected | brainstorm #8 | **Done** |
| 2 | Supply-side features | Medium | +0.66pp | +5-10% | Schema change | No | **Done** |
| 3 | Auto-prune | Low | Prevents overfit | +10-20% | No | **No** | **Done** |
| 4 | Event decay opt | Low | 0pp | None | No | brainstorm #7 | **Done** |
| 5 | Multi-horizon | Medium | +2-4pp est. | +300-400% | No | brainstorm #13 | Pending |
| 6 | Listing count | Medium | +3-8pp est. | +1-2% | New collection | **No** | Pending |
| 7 | Sub-models | High | +2-5pp est. | +500% | No | brainstorm #14 | Pending |
| 8 | Conformal pred | Medium | Intervals only | Negligible | No | brainstorm #12 | Pending |
| 9 | More training data | Low | +1-2pp est. | +100% | Collected | No | Pending |
| 10 | More HP trials | Trivial | +0.5-1pp est. | +200-300% | No | No | Pending |

**Top recommendation:** **#5 (multi-horizon)** or **#6 (listing count)** — highest remaining impact opportunities now that event decay optimization (#4) is done with zero impact.

**Guardrail:** Any new feature group must pass `_validate_feature_groups()` (built-in permutation test during `train()`) or it will be auto-pruned. This applies to all items above.
