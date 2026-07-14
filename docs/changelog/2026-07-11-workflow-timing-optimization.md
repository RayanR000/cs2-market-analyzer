# Workflow Timing Optimization & Bug Fixes

## Changes Made

### 1. Workflow Timing — 5 YAML files

| File | Before | After | Reason |
|---|---|---|---|
| `daily-trend-analysis.yml` | cron `0 3 * * *` | cron `0 2 * * *` | Tighten data-to-analysis gap from 4h to 2h after aggregator (~23:36 UTC finish) |
| `daily-trend-analysis.yml` | inline `trend_direction` + `opportunity` backtests | removed | Backtesting centralized in `backtest-accuracy.yml` (single source) |
| `price-forecast.yml` | inline `forecast` backtest | removed | Same — centralized backtesting |
| `backtest-accuracy.yml` | cron `0 8 * * 0` | cron `0 8 * * 1-6` | Removed Sunday cron (was duplicating chained trigger) |
| `backtest-accuracy.yml` | `type=historical` on Sunday | `type=sunday` | New mode runs live + historical in one shot when chained on Sunday |
| `backtest-accuracy.yml` | — | conditions updated | `sunday` matches both live and historical steps |
| `long-term-trend-analysis.yml` | cron `0 6 * * 0` | cron `0 4 * * 0` | Runs before event correlation so it uses full-history trends |
| `event-correlation-analysis.yml` | cron `0 4 * * 0` | cron `0 6 * * 0` | Runs after LTT overwrites daily_analysis |
| `event-correlation-analysis.yml` | stale aggregator time comment | fixed | No longer references "Sunday aggregator at 01:00 UTC" |

### Resulting Schedule

```
Mon-Sat:                     Sunday:
23:00 Aggregator             23:00 Sat Aggregator
02:00 Trend Analysis          02:00 Trend Analysis
02:05 Price Forecast          02:05 Price Forecast
02:10 Backtest (live)         02:10 Backtest (live + historical)
08:00 Backtest (fallback)     04:00 Long-Term Trends
                              06:00 Event Correlation
```

### 2. Pre-existing Bug Fixes

| File | Bug | Fix |
|---|---|---|
| `collectors/pipeline.py:707` | `_load_parquet_histories` threw exception when `price-archive/` didn't exist (CI runners only have `main` branch, parquet lives on `data-archive`) | Added directory-exists check + try/except; falls back to DB query gracefully |
| `scripts/analyze_trends.py:48` | `_filter_daily_analysis_row` passed numpy types (`np.float64`) into SQLAlchemy, causing `schema "np" does not exist` | Added numpy type conversion to Python native `float()` |
| `scripts/analyze_trends.py:281` | `calculate_volatility` returned numpy float64 via `min(np_float, 100.0)` | Wrapped return in `float()` |
| `scripts/analyze_trends.py:376` | `price_stability = max(0, 100 - np_float)` returned numpy float64 | Wrapped in `float()` |

### 3. Verified Run Results

| Workflow | Status | Key Evidence |
|---|---|---|
| Daily Trend Analysis | ✅ Passed (27s) | `"Parquet archive not found...falling back to DB"` — graceful fallback; `"Inserting 3 analysis results... Total records: 3"` — numpy fix works; no inline backtest step |
| Price Forecast | ✅ Passed (26s) | Only `forecast.log` in artifact (no backtest.log); `"Wrote 6 forecasts to item_forecasts table"` |
| Backtest Accuracy | ✅ Passed (34s) | `live` mode ran forecast + trend_direction + opportunity; historical skipped (not Sunday); `sunday` mode logic ready for chain trigger |
