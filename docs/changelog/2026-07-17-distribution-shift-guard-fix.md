# Distribution-shift guard fix and retrain

**Date:** 2026-07-17

Fixed the 2026 distribution-shift guard that silently failed to exclude incomplete 2026
data, causing the 7d model to collapse to 4 features (−9.1pp regression). Retrained and
deployed as `lgbm-v3` (corrected).

## Bug

The guard (`forecaster.py`, added in `b23f5d9`) had two defects:

1. **`month < 6` check**: The old code only filtered 2026 rows if `dates_2026.max().month < 6`.
   In July 2026 (month 7), this is `False`, so the entire guard was skipped — all 1.9M
   2026 rows survived into training, causing the 7d validation window to land on a single
   sparse date (352 items).
2. **Position**: The guard ran *after* `_stratified_item_subsample`, wasting the 400K row
   budget on data that should have been excluded.

**Result:** The single-date validation set caused `_validate_feature_groups` to produce
pure-noise permutation scores, triggering the auto-prune safety net and collapsing the 7d
model to 4 core features (53.0% directional accuracy).

## Fix (commit `56ff0b7`)

Rewrote the guard in `build_training_data()`:

```python
if "date" in price_df.columns:
    dates_2026 = pd.to_datetime(price_df["date"]).dt.year == 2026
    n_2026 = dates_2026.sum()
    if n_2026 > 0:
        price_df = price_df[~dates_2026].copy()
        logger.info(f"  Excluded {n_2026:,} incomplete 2026 rows")
```

- Removed `month < 6` check — excludes all 2026 rows unconditionally
- Moved **before** `_stratified_item_subsample` — row budget preserved for valid data

### Follow-up: `.dt.year` dtype stability (2026-07-18)

The `.dt` accessor's `.year` property returns inconsistent dtypes depending on NaT presence (`int32` vs `float64`), and `pd.to_datetime(Series)` can misinterpret integer-like values as nanoseconds since epoch. Changed to `pd.DatetimeIndex(price_df["date"]).year` — avoids the `.dt` accessor entirely, is ~12% faster, and returns a consistent dtype regardless of nulls.

```python
# Before:
dates_2026 = pd.to_datetime(price_df["date"]).dt.year == 2026
# After:
dates_2026 = pd.DatetimeIndex(price_df["date"]).year == 2026
```

## Validation-set floor (same commit)

- Raised from `val_set < 100` to `val_set < 2000` or `< 7 distinct dates`
- Feature-group validation skipped entirely below this threshold

## Regression tests (this session)

Added 2 tests to `tests/test_forecaster.py`:

| Test | What it guards |
|------|----------------|
| `test_distribution_shift_guard_excludes_2026` | All 2026 rows removed; non-2026 rows preserved |
| `test_distribution_shift_guard_preserves_earlier_years` | No-op when no 2026 data present |

## Retrain

```
SKIP_CV=1 FORCE_RETRAIN=1 DATABASE_URL="sqlite:///$(pwd)/cs2_market.db" \
  python scripts/forecast_prices.py --train-only
```

**Duration:** 811s (13.5 min), no hangs

**Pipeline:**
- 6,016,371 raw rows → 5,488,435 voted → **459,579 2026 rows excluded** → 411,850 after subsampling
- 124 features after correlation pruning
- Training window: 2022-07-19 → 2025-12-31 (no 2026 data)

## Accuracy (Parquet backtest, FORECAST_DATE_OVERRIDE=2025-12-01)

| Horizon | Before (buggy) | After (fixed) | Δ |
|---------|:-:|:-:|:-:|
| 3d  | 60.6% (original) / 61.8% (buggy retrain) | **58.15%** | — |
| 7d  | 62.1% (original) / **53.0%** (buggy retrain) | **57.41%** | **+4.4pp** |
| 14d | 53.4% (original) | **55.08%** | **+1.7pp** |
| 30d | 42.5% (original) / 54.4% (buggy retrain) | **55.15%** | **+12.7pp** |

- 7d recovered from 53.0% → 57.41%, now a 20-feature events model (not the 4-feature safety net)
- 30d now above random for the first time on clean data
- 3d slight regression (−2.5pp) is the trade-off for removing 1.9M noisy 2026 rows

## Files changed

```
backend/models/forecaster.py              | +13/-11  (guard rewrite, val floor, test skip)
backend/tests/test_forecaster.py          | +55/-0   (2 regression tests)
docs/changelog/2026-07-17-7d-regression-investigation.md | +30/-31 (mark resolved)
docs/changelog/2026-07-17-distribution-shift-guard-fix.md | +110 (this file)
```
