# Remove Trend Model — Execution Log

Date: 2026-07-12

## Summary

Removed the rule-based trend model (`DailyAnalysis` / MA-crossover) and rewired all consuming endpoints to use the ML forecast model (`ItemForecast`) directly. The trend model achieved ~42% directional accuracy; the forecast model achieves 85.4%.

---

## Files Deleted

| File | Reason |
|------|--------|
| `backend/analytics/trend_analyzer.py` | TrendAnalyzer + OpportunityDetector classes |
| `backend/analytics/__init__.py` | No change needed (was just a comment) |
| `backend/scripts/analyze_trends.py` | Daily MA-crossover analysis script |
| `backend/scripts/long_term_trend_analyzer.py` | Weekly full-history analysis script |
| `backend/scripts/event_analyzer.py` | Event correlation analysis (was independent but unused without trend data) |
| `backend/tests/test_analyze_trends.py` | Tests for deleted script |
| `backend/tests/test_trend_analyzer.py` | Tests for deleted module |
| `.github/workflows/daily-trend-analysis.yml` | Daily trend analysis GH Action |
| `.github/workflows/long-term-trend-analysis.yml` | Weekly long-term trend GH Action |
| `.github/workflows/event-correlation-analysis.yml` | Weekly event correlation GH Action |

## Files Modified

### `backend/api/schemas.py`
- **`TrendAnalysisOut`** — removed `volatility`, `trend_score` fields. `sma_7`/`sma_30` kept (now computed from raw `price_history` instead of `DailyAnalysis`).

### `backend/api/routes/items.py`
- **Import** — removed `DailyAnalysis` from imports.
- **`GET /items/{id}/trends`** — replaced `DailyAnalysis` query with `ItemForecast` (7-day horizon, latest forecast date). Maps `direction` → `bullish`/`bearish`/`neutral` and `confidence` directly. Computes SMA-7/30 from `price_history`. Drops `volatility`, `trend_score` from response.
- **`GET /items/trending`** — replaced `updated_at` sort with forecast confidence + predicted return magnitude ranking.
- **`GET /items/{id}/variants`** — removed `DailyAnalysis` join for `current_price`; now falls through to `price_history` only.
- **`_build_trend_explanation`** — updated copy to reference ML forecast.

### `backend/api/routes/opportunities.py`
- Complete rewrite. All endpoints (`GET /`, `/undervalued`, `/overheated`, `/momentum`) now query `ItemForecast` instead of `DailyAnalysis`.
- Classification: direction=up + confidence=high → undervalued, direction=down + confidence=high → overheated, else → momentum.

### `backend/api/routes/market.py`
- Removed `DailyAnalysis` import and all `daily_analysis` query logic.
- `current_price` now sourced from `price_history` only.
- Removed `volatility` from `GroupedMarketItemOut` response (was from `DailyAnalysis`).
- Removed unused `desc` import.

### `backend/database.py`
- Removed `DailyAnalysis` ORM class entirely.
- Removed `daily_analyses` relationship from `Item`.
- Updated `PredictionAccuracy` docstring to only reference `forecast` type.

### `backend/scripts/backtest_accuracy.py`
- Removed `backtest_trends()`, `backtest_opportunities()`, `backtest_historical()` functions and all their helpers (`_classify_direction`, `_compute_trend_at_date`, `_compute_opportunity_at_date`, `_load_parquet_items`).
- Updated `run_backtest()` and `main()` to only accept `forecast` type.
- Updated module docstring.

### `backend/scripts/run_task.py`
- `trends` and `long_term_trends` tasks are now no-ops with deprecation message.
- Updated help text.

### `backend/collectors/pipeline.py`
- `run_trend_analysis()` replaced with a no-op stub.

### `frontend/app/accuracy/page.tsx`
- Removed `TrendSection` and `OpportunitySection` components.
- Removed `trend_direction` and `opportunity` branches from rendering loop.
- `SourceBadge` simplified to always show "LIVE".
- Removed references to 13-YR WALKFORWARD.

### `frontend/lib/api.ts`
- `TrendAnalysis` interface — removed `sma_7`, `sma_30`, `volatility`, `trend_score` fields.

## Files Created

### `backend/migrations/versions/0015_drop_daily_analysis.py`
- Alembic migration to drop the `daily_analysis` table.
- Includes full downgrade with table recreation.

## GitHub Actions

### `.github/workflows/backtest-accuracy.yml`
- Simplified to only run `--type forecast`.
- Removed `trend_direction`, `opportunity`, `historical` from workflow dispatch options.
- Removed Sunday historical run step.

## Data Flow After Change

```
Price History → ML Forecast Model → ItemForecast table 
                                        ↓
                           GET /items/{id}/trends     (trend_direction + confidence from forecast)
                           GET /opportunities/*        (forecast-based classification)
                           GET /items/trending         (forecast confidence ranking)
                           GET /market/summary         (current_price from price_history only)

Price History → On-the-fly computation 
                                        ↓
                           GET /items/{id}/trends     (SMA-7/30, RSI, Bollinger, MACD, support/resistance)
```

## Verification

- All modified Python files pass `py_compile`.
- Frontend TypeScript passes `tsc --noEmit` with zero errors.
