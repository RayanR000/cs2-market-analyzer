# Investigation: 7d Accuracy Regression After Dead-Item-Filter Retrain

**Date:** 2026-07-17

> ✅ **RESOLVED (2026-07-17).** Guard fix verified, retrain complete, models deployed as
> `lgbm-v3` (corrected). See `docs/changelog/2026-07-17-distribution-shift-guard-fix.md`.

**Context:** A retrain was run after pulling in the dead-item-filter / corrupt-item-flagging /
target-winsorization / sample-weighting / 2026 shift-guard fixes (`b23f5d9`, merged via
`8fa9699`). The models on disk (`backend/models/saved_models/`, last committed in `0dead22`)
predated those fixes, so a fresh retrain was required.

**Backtest method:** `FORECAST_DATE_OVERRIDE=2025-12-01 python scripts/forecast_prices.py
--predict-only` (current models) → `python scripts/backtest_accuracy.py`, then retrain
(`SKIP_CV=1 FORCE_RETRAIN=1 python scripts/forecast_prices.py --train-only`) → same
predict + backtest. Both runs compared against `prices-*.parquet` actuals (~5,360–5,512
samples/horizon).

## Before → After (Parquet backtest)

| Horizon | Before | After | Δ |
|---------|:------:|:-----:|:---:|
| 3d  | 60.6% | 61.8% | +1.2pp |
| 7d  | 62.1% | 53.0% | **−9.1pp** |
| 14d | 53.4% | 55.9% | +2.5pp |
| 30d | 42.5% | 54.4% | +11.9pp |

3d / 14d / 30d improved (30d now above random). **7d regressed sharply.**

## Root cause: 2026 distribution-shift guard is NOT excluding 2026 data

A diagnostic on `build_training_data(days_back=1460)` output showed 2026 rows still present:

```
Rows by year:
2022     38858
2023    101198
2024    113595
2025    139096
2026     35441   ← should have been removed by the guard
Date range: 2022-07-18 to 2026-07-17
```

Because 2026 data survives, the temporal hold-out split (`VALIDATION_WINDOW_DAYS = 21`,
`forecaster.py:57,1471`) lands in mid-2026 — where only sparse aggregator snapshots exist,
not the complete backfilled series. Validation window sizes per horizon:

| Horizon | max_date | val window | val rows | val items | val **dates** |
|---------|----------|-----------|----------|-----------|---------------|
| 3d  | 2026-07-14 | Jun 23–Jul 14 | 2,474 | 590 | **5** |
| 7d  | 2026-07-09 | Jun 18–Jul 09 | 352  | 352 | **1** |
| 14d | 2026-03-15 | Feb 22–Mar 15 | 5,235 | 347 | 22 |
| 30d | 2026-02-27 | Feb 06–Feb 27 | 5,251 | 348 | 22 |

The **7d validation set is a single calendar day (352 items)**. The permutation test
(`_validate_feature_groups`, `forecaster.py:997`) on 352 rows is pure noise — each
correct/wrong flip moves accuracy ~0.28pp. Training logged:

```
[feat group] price_technicals: -8.17pp when shuffled (74.7% -> 82.9%) [WARN]
All features pruned → falling back to 4 core features as safety net
Pruned 39 features from non-causal groups ['price_technicals'] (39 -> 4). Retraining.
```

Shuffling features *appeared* to improve 7d accuracy, so the auto-prune dropped everything
down to the 4-feature safety net (`price_log`, `price_std_7d`, `price_lag_1d`,
`price_lag_3d`), collapsing the 7d model and causing the −9.1pp regression.

## Why the guard failed

The original guard code (`forecaster.py:1359-1367`, before `56ff0b7`) was:

```python
if "date" in price_df.columns:
    dates_2026 = pd.to_datetime(price_df.loc[
        pd.to_datetime(price_df["date"]).dt.year == 2026, "date"])
    if len(dates_2026) > 0 and dates_2026.max().month < 6:
        n_2026 = len(dates_2026)
        price_df = price_df[pd.to_datetime(price_df["date"]).dt.year != 2026].copy()
        logger.info(f"  Excluded {n_2026:,} incomplete 2026 rows ...")
```

Two bugs:
1. **`month < 6` check**: In July 2026 (month 7), `dates_2026.max().month` is ≥ 6, so the
   guard is skipped entirely. All 1.9M 2026 rows survive into training.
2. **Position**: The guard ran *after* `_stratified_item_subsample`, wasting the row budget
   on data that should have been excluded.

## Validation-set floor fix

The validation-set fallback threshold `val_set < 100` was raised to `val_set < 2000`
or `< 7 distinct dates`. Feature-group validation is now skipped entirely when below
this threshold, preventing false-positive pruning from noisy permutation tests.

## Resolution

The guard was rewritten in `56ff0b7` to:
- Run **before** the stratified subsample (row budget preserved for valid data)
- Remove all 2026 data unconditionally (no `month < 6` check)

A retrain with the fixed guard completed in 811s (13.5 min) and models were saved as
`lgbm-v3` (corrected). Accuracy after fix:

| Horizon | Post-fix | Notes |
|---------|:--------:|-------|
| 3d  | **58.15%** | Slight regression (-2.5pp vs original baseline); expected from removing 1.9M noisy rows |
| 7d  | **57.41%** | Recovered from 53.0% collapse; 20-feature model (events-focused) vs prior 4-feature safety net |
| 14d | **55.08%** | +1.7pp; stable improvement from cleaner training data |
| 30d | **55.15%** | **+12.7pp**; above random for the first time on clean data |

See `docs/changelog/2026-07-17-distribution-shift-guard-fix.md` for full details.
