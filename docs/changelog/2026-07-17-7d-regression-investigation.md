# Investigation: 7d Accuracy Regression After Dead-Item-Filter Retrain

**Date:** 2026-07-17

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

## Why the guard fails (NOT yet confirmed)

The guard code (`forecaster.py:1359-1367`) is:

```python
if "date" in price_df.columns:
    dates_2026 = pd.to_datetime(price_df.loc[
        pd.to_datetime(price_df["date"]).dt.year == 2026, "date"])
    if len(dates_2026) > 0 and dates_2026.max().month < 6:
        n_2026 = len(dates_2026)
        price_df = price_df[pd.to_datetime(price_df["date"]).dt.year != 2026].copy()
        logger.info(f"  Excluded {n_2026:,} incomplete 2026 rows ...")
```

Hypotheses (unverified — diagnostic was interrupted before the fetch→filter→subsample
2026 check completed):
1. `price_df["date"]` dtype after `_stratified_item_subsample` may not support `.dt.year`
   (string vs timestamp), so the `== 2026` mask is empty and nothing is excluded.
2. The guard runs *after* the subsample; if the subsample's 590 items happen to carry
   2026 rows, those persist into feature engineering.
3. The `dt.year == 2026` comparison silently no-ops on a non-datetime column.

Need to re-run the aborted diagnostic to confirm which of these is the actual failure.

## Secondary issue: validation-set floor too low

`forecaster.py:1483` only falls back to a percentage split when `len(val_set) < 100`.
Even the healthy 3d window (2,474 rows / 5 dates) is small for reliable permutation
testing. A higher floor (e.g. ≥ 2,000) and/or a percentage-based holdout would make the
prune decision robust regardless of calendar sparsity.

## Not fixed yet — next steps

1. Confirm why the 2026 guard doesn't exclude 2026 rows (finish the interrupted diagnostic:
   `fetch_price_history` → `_filter_dead_items` → `_stratified_item_subsample` → inspect
   `pd.to_datetime(price_df["date"]).dt.year == 2026`).
2. Fix the guard so 2026 data is actually dropped (data ends 2026-03-29, incomplete).
3. Raise the `val_set < 100` fallback threshold and/or switch to a percentage-based split.
4. Re-run the retrain (guard fix alone should move the 7d val window back into complete
   2025 data, giving a proper multi-date validation set and preventing the safety-net
   collapse) and re-backtest.
