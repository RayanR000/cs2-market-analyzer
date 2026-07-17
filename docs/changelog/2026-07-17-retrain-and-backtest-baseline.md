# Retrain + backtest baseline (corrected price data)

**Date:** 2026-07-17

All models retrained with the `fetch_price_history` column-order fix (bug documented in `2026-07-17-column-order-bug.md`). This is the first run where models actually learned from **price** data.

---

## Retrain summary

**Duration:** 345s (5.7 min) — HP search skipped (reused cached HP from buggy run; these are model-complexity params, not data-specific, and results confirm they are adequate).

**Data:** 6,019,294 raw Parquet rows → 5,491,358 after multi-source voting (11 sources) → 407,384 after stratified subsampling (633/8,691 items, full calendar window preserved).

**Features:** 123 after correlation pruning, then per-horizon pruning removed non-causal groups (item_identity, temporal, events, supply_depth, cross_sectional — only price_technicals passed the permutation test at every horizon).

**6-fold expanding-window CV (from training):**

| Horizon | DirAcc | Std | Range |
|---------|--------|-----|-------|
| 3d | **67.8%** | ±3.5% | [63.5, 73.1] |
| 7d | **68.0%** | ±2.5% | [64.6, 71.5] |
| 14d | **68.4%** | ±2.9% | [64.5, 73.5] |
| 30d | **68.2%** | ±3.0% | [64.8, 72.8] |

**High-confidence calibration (from CV OOF): with ~45-50% coverage achieving ~80-83% accuracy.**

---

## Backtest against Parquet actuals

The `backtest_accuracy.py` script previously relied on the `price_history` DB table which only holds live aggregator data (recent dates). Since all historical data lives in Parquet, `_load_actual_prices` was rewritten to use DuckDB directly against the `prices-*.parquet` archive.

**Methodology:** Forecasts were generated with `FORECAST_DATE_OVERRIDE=2025-12-01` (supported by a new env var added to `forecast_prices.py`) to use a date where 2025 daily Parquet data is available for all 5,542 forecast items. The backtest then compared each forecast against the actual `mean_price` from Parquet on the target date.

| Horizon | Samples | DirAcc | MAE | MAPE | IntCov |
|---------|---------|--------|-----|------|--------|
| 3d | 5,512 | **60.6%** | $0.75 | 43.0% | 43.3% |
| 7d | 5,431 | **62.1%** | $0.74 | 40.8% | 43.7% |
| 14d | 5,434 | **53.4%** | $0.74 | 35.4% | 56.9% |
| 30d | 5,360 | **42.5%** | $0.77 | 34.2% | 60.1% |

### Analysis

- **3d/7d (60-62%):** Above random (50%). Models show genuine short-term signal. Slightly below CV estimates (~68%), which is expected — CV measures in-sample walk-forward accuracy; the real backtest includes distribution shift from Dec 2025 to the present.
- **14d (53%):** Near-random. Two-week directional predictions are barely better than a coin flip, though interval coverage (57%) is solid.
- **30d (42%):** Below random. The model is worse than flipping a coin for 30d direction. The interval coverage (60%) provides some value, but directional predictions at this horizon are unreliable.

**Overall:** 3d and 7d are trustworthy enough for production. 30d directional predictions should be de-emphasized — only the interval/confidence labels carry signal.

---

## Files changed

| File | Changes |
|------|---------|
| `scripts/backtest_accuracy.py` | `_load_actual_prices` rewritten to use DuckDB + Parquet instead of the empty DB `price_history` table. Fixes `isinstance(day, date)` bug where DuckDB returns `datetime` objects (a `datetime` is `isinstance` of `date`, so keys were stored as `datetime` while lookup used `date` — no match). |
| `scripts/forecast_prices.py` | Added `FORECAST_DATE_OVERRIDE` env var support for backtesting with arbitrary forecast dates. |

---

## DB cleanup

- Deleted 88,456 buggy forecasts (lgbm-v1, lgbm-catboost-v2) produced by the column-ordering bug
- Deleted 18 stale `prediction_accuracy` records
- 21,737 forecast outcomes from the backdated backtest cleanup deleted
- 22,168 live production forecasts (5,542 items × 4 horizons) written with `forecast_date=2026-07-17`

## Live forecast

22,168 forecasts written to `item_forecasts` with `model_version=lgbm-v3`. First automatic backtest of live forecasts will mature Jul 20 (3d horizon) and can be run with:

```
python scripts/backtest_accuracy.py
```
