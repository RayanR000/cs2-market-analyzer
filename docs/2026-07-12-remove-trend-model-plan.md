# Remove Trend Model — Plan

Date: 2026-07-12

## Current State

Two independent prediction systems run daily on the same 5,525 backfilled items:

### 1. Forecast Model (ML)
- **File:** `backend/models/forecaster.py`
- **Algorithm:** LightGBM quantile regression, 27 ensemble models (3 horizons × 3 quantiles × 3 seeds)
- **Features:** 65 engineered features (price lags, rolling stats, Bollinger, RSI, MACD, volume, temporal, events, cross-sectional market features)
- **Training:** Optuna Bayesian search, correlation pruning at 0.95, 21-day walk-forward validation
- **Input:** 365 days of price history from Parquet archive (STEAMCOMMUNITY source)
- **Outputs:** `item_forecasts` table — `price_low/mid/high`, `direction` (up/down/flat), `confidence` (low/medium/high)
- **Accuracy:** 85.4% directional (7d), 77.1% (30d) — measured offline via `evaluate_forecaster.py`
- **Coverage:** All 5,525 backfilled items, 2 horizons (7d + 30d + 1d recently added)

### 2. Trend Model (Rule-Based)
- **File:** `backend/analytics/trend_analyzer.py`, `backend/scripts/analyze_trends.py`
- **Algorithm:** Simple moving average crossover — MA-7 vs MA-30 with a hardcoded 2% threshold
- **Input:** 90 days of price history
- **Outputs:** `daily_analysis` table — `trend_direction`, `opportunity_score`, `momentum_score`, `volatility`, SMAs
- **Accuracy:** ~42% directional (live DB across 300k+ samples)
- **Coverage:** All items in DB, but recent runs show only 2,376 of 5,525 items processed (incomplete)

### Key Finding
The two systems are **completely independent** — zero cross-references. The forecast model never reads `daily_analysis`. The trend model's outputs serve only the frontend API.

---

## Problem

1. **Trend model is redundant** — both systems compute overlapping signals from the same price data; the forecast model does it better with 65 features vs. a 2-line MA crossover
2. **Low accuracy** — 42% directional accuracy is barely above random (33% for 3-class) and provides no value as a signal
3. **Maintenance burden** — requires running and monitoring `analyze_trends.py`, `long_term_trend_analyzer.py`, `backtest_accuracy.py` (trend + opportunity + historical modes), and their associated GitHub Actions workflows
4. **Confusing dual signals** — frontend shows `trend_direction` (42% accurate) alongside forecast direction (85% accurate); users see two potentially conflicting views

---

## Proposed Solution

Route the forecast model's outputs to the frontend endpoints that currently consume `daily_analysis`. Drop the trend model entirely.

### What Changes

| Current | → | New |
|---------|---|-----|
| `GET /items/{id}/trends` reads `daily_analysis` | → | Reads `item_forecasts` (latest forecast direction + confidence) |
| `GET /opportunities/*` uses `daily_analysis.opportunity_score` | → | Queries `item_forecasts` for forecast-based signals |
| `GET /items/trending` uses `daily_analysis` | → | Uses forecast direction + predicted return |
| `daily_analysis` populated by `analyze_trends.py` | → | Deleted |
| Daily `analyze_trends.py` + `long_term_trend_analyzer.py` | → | Removed from schedule |
| Backtest types `trend_direction`, `opportunity`, `historical` | → | Removed |
| `DailyAnalysis` ORM model + table + migration | → | Dropped |

### What Stays the Same

- RSI, Bollinger Bands, MACD, support/resistance on the trends endpoint — these are computed from raw `price_history` on-the-fly, not from `daily_analysis`
- The forecast model and its accuracy tracking remain untouched
- `PredictionAccuracy` table continues to hold forecast metrics only
- `ForecastOutcome` / `AccuracyAlert` migrations still need to be applied

---

## Pros vs. Cons

### Pros
- **One less system to maintain** — no daily trend analysis workflow, no `analyze_trends.py`, no historical backtest
- **Frontend shows 85% accurate signals** instead of 42%
- **No duplicate compute** — 65-feature model powers both prediction and UI
- **Simpler mental model** — one source of truth for item outlook
- **Fewer GitHub Actions workflows** to run and monitor
- **Fewer database tables** to manage

### Cons
- **Loss of opportunity score heuristic** — the undervalued/overheated/momentum browse lists need to be rebuilt on forecast data (behavior changes, but can be more accurate)
- **New items with <14 days of history** have no forecast, so frontend trend badge disappears (irrelevant currently — all items have years of data)
- **Bollinger/RSI/MACD stay the same** — this change doesn't simplify that part of the codebase

---

## Implementation Plan

### Phase 1: Rewrite Frontend Data Sources (API changes)

**Step 1.1 — Update `GET /items/{id}/trends`**

File: `backend/api/routes/items.py:323-411`

Replace the `daily_analysis` query with `item_forecasts`:

```python
# Before
latest_analysis = db.query(DailyAnalysis).filter(
    DailyAnalysis.item_id == item.id
).order_by(desc(DailyAnalysis.analysis_date)).first()
trend_dir = latest_analysis.trend_direction if latest_analysis else "neutral"

# After (conceptual)
latest_forecast = db.query(ItemForecast).filter(
    ItemForecast.item_id == item.id,
    ItemForecast.forecast_date == date.today(),
    ItemForecast.horizon_days == 7
).first()
# map forecast.direction → "bullish"/"bearish"/"neutral"
# map forecast.confidence → "high"/"medium"/"low"
```

Keep raw-price computations (RSI, Bollinger, MACD, support/resistance, factors) unchanged.

Drop `sma_7`, `sma_30`, `volatility`, `trend_score` from the response schema (or compute them from raw prices like everything else).

**Step 1.2 — Update `TrendAnalysisOut` schema**

File: `backend/api/schemas.py:44-63`

Remove fields that came from `daily_analysis`:
- `sma_7`, `sma_30`, `volatility`, `trend_score`

Or re-source them from `price_history` directly (minimal cost — just mean/std of recent prices).

**Step 1.3 — Rewrite opportunities endpoints**

File: `backend/api/routes/opportunities.py`

Replace with forecast-based queries:

- **Undervalued** → `item_forecasts` with `direction = 'up'` and `confidence = 'high'`, sorted by predicted % change descending
- **Overheated** → `item_forecasts` with `direction = 'down'` and `confidence = 'high'`, sorted by predicted % change descending
- **Momentum** → `item_forecasts` with largest absolute predicted return regardless of confidence, sorted by return magnitude

Define a threshold for what counts as "significant" (e.g., top 10% of predicted returns, or >5% predicted change).

**Step 1.4 — Update `GET /items/trending`**

File: `backend/api/routes/items.py:65-100`

Replace with a query across latest `item_forecasts`, ranking by forecast confidence + predicted return magnitude.

### Phase 2: Remove Trend Model Code

**Step 2.1 — Delete trend analysis scripts**
- `backend/analytics/trend_analyzer.py` (the `TrendAnalyzer` and `OpportunityDetector` classes)
- `backend/analytics/__init__.py` (update if needed)
- `backend/scripts/analyze_trends.py`
- `backend/scripts/long_term_trend_analyzer.py`

**Step 2.2 — Remove trend/opportunity backtesting**
- Remove `backtest_trends()`, `backtest_opportunities()`, `backtest_historical()` from `backend/scripts/backtest_accuracy.py`
- Remove `trend_direction`, `opportunity`, `historical` types from the main dispatcher
- Update the `--type` argument to only accept `forecast`

**Step 2.3 — Remove event analysis (if trend-dependent)**
- `backend/scripts/event_analyzer.py` — check if it depends on `daily_analysis`; if so, remove or refactor

**Step 2.4 — Drop database table and ORM model**
- Create a migration to drop the `daily_analysis` table
- Remove `DailyAnalysis` from `backend/database.py`
- Remove `EventCorrelation`, `EventImpact` tables if dependent on trend data

**Step 2.5 — Remove from API**
- Remove `opportunities` router from the app
- Remove `DailyAnalysis` imports and references from `routes/items.py` and `routes/opportunities.py`
- Update `OpportunityOut` schema or remove it
- Remove `TrendAnalysisOut` SMA/volatility/trend_score fields (or re-source them)

**Step 2.6 — Remove accuracy tracking for trend/opportunity**
- Remove `PredictionAccuracy` records for `trend_direction` and `opportunity` types (stale data)
- Remove the accuracy page sections for trend/opportunity from the frontend (`frontend/app/accuracy/page.tsx`)

**Step 2.7 — Remove related GitHub Actions workflows**
- `.github/workflows/daily-trend-analysis.yml`
- `.github/workflows/long-term-trend-analysis.yml`
- `.github/workflows/event-correlation-analysis.yml`
- Update `.github/workflows/backtest-accuracy.yml` to remove historical run

### Phase 3: Apply Missing Forecast Migrations

**Step 3.1** — Apply migrations 0013 and 0014 to production to enable:
- `accuracy_alerts` table (concept drift monitoring)
- `forecast_outcomes` table (per-forecast correctness tracking)

**Step 3.2** — Update `backtest_accuracy.yml` to run `forecast` type only

### Phase 4: Verify

**Step 4.1** — Run the API and check all affected endpoints return expected data
**Step 4.2** — Check the frontend item detail page renders trend/confidence correctly
**Step 4.3** — Check the accuracy page shows forecast metrics
**Step 4.4** — Verify the forecast backtest still runs and stores data

---

## Files to Modify (Summary)

| File | Action |
|------|--------|
| `backend/models/forecaster.py` | No change |
| `backend/analytics/trend_analyzer.py` | **Delete** |
| `backend/analytics/__init__.py` | Update |
| `backend/scripts/analyze_trends.py` | **Delete** |
| `backend/scripts/long_term_trend_analyzer.py` | **Delete** |
| `backend/scripts/event_analyzer.py` | **Delete** (or refactor) |
| `backend/scripts/backtest_accuracy.py` | Remove 3 of 4 backtest types |
| `backend/scripts/forecast_prices.py` | No change |
| `backend/database.py` | Remove `DailyAnalysis`, related ORM models |
| `backend/api/routes/items.py` | Rewrite trend endpoints |
| `backend/api/routes/opportunities.py` | **Delete** or rewrite on forecast data |
| `backend/api/routes/accuracy.py` | Remove trend/opportunity sections |
| `backend/api/schemas.py` | Update `TrendAnalysisOut`, remove unnecessary fields |
| `backend/migrations/` | Add migration to drop `daily_analysis` table; apply 0013, 0014 |
| `.github/workflows/daily-trend-analysis.yml` | **Delete** |
| `.github/workflows/long-term-trend-analysis.yml` | **Delete** |
| `.github/workflows/event-correlation-analysis.yml` | **Delete** |
| `.github/workflows/backtest-accuracy.yml` | Update (remove historical type) |
| `frontend/app/accuracy/page.tsx` | Remove trend/opportunity sections |
| `frontend/lib/api.ts` | Update types |
| `frontend/app/items/[id]/page.tsx` | Update trend display |

---

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|:----------:|------------|
| Frontend breaks during transition | Medium | Deploy API changes first, verify endpoints, then update frontend |
| Opportunity UX is worse with forecast signals | Medium | Implement with tunable thresholds; default to top-10% predicted return |
| Missing trend data for items under forecast's min history | Low | All 5,525 items have years of historical data |
| Bollinger/RSI/MACD depend on daily_analysis somewhere | Low | Already computed from raw price_history on-the-fly in items/trends endpoint |
