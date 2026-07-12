# CS2 Market Analyzer — Pipeline State (2026-07-12)

## Architecture Overview

```
CSGOTrader / Steam / Skinport / Buff163 / CSFloat
    │
    ▼
price_history (DB)  ◄── aggregator pipeline.py
    │
    ▼
Parquet Archive (price-archive/prices-YYYY.parquet)
    │  9.9M rows, 8,691 items, 2013–2026
    │  schema: item_slug, day, mean_price (as price), volume
    │  source-filtered to STEAMCOMMUNITY-backfilled items
    │
    ▼
ItemForecaster (36 LightGBM models)
    ├── 4 horizons × 3 quantiles × 3 ensemble seeds
    ├── 70+ engineered features (price, temporal, event, cross-sectional)
    ├── Optuna Bayesian HP search (30 trials per quantile)
    ├── Walk-forward validation (60-day steps, 21-day validation windows)
    ├── Concept drift monitoring (auto-retrain if accuracy < 60%)
    └── Predictions → item_forecasts table
    │
    ▼
Accuracy Evaluation
    ├── evaluate_forecaster.py (walk-forward on parquet, 50 items)
    ├── backtest_accuracy.py (mature forecasts vs realized prices)
    └── accuracy_alerts (drift detection)
    │
    ▼
FastAPI + Next.js 16 Dashboard
```

---

## Current State

### Database
- **Local SQLite:** `backend/cs2_market.db` — items (8,691), events (79), item_forecasts (22,168)
- **Production:** Supabase PostgreSQL (not yet migrated)

### Models
- **36 trained model files** in `backend/models/saved_models/`
- Model version: `lgbm-v1`
- Last trained: 2026-07-12 19:57:46 UTC
- Quantiles: p10 (price_low), p50 (price_mid), p90 (price_high)
- Horizons: 3d, 7d, 14d, 30d
- Ensemble: 3 seeds per quantile (42, 73, 91)

### Forecasts
- **22,168 active forecasts** in `item_forecasts` table
- 5,542 items × 4 horizons
- Generated: 2026-07-12
- All forecasts are from today — none have matured yet for backtesting

### Accuracy (Walk-Forward, Post-Fix)

| Horizon | Directional Accuracy | vs 50% Baseline | Interval Coverage | MAE  | Fold Std Dev |
|---------|:-------------------:|:---------------:|:-----------------:|:----:|:------------:|
| 3d      | **60.2%**           | +10.2pp         | 85.6%             | $0.20| 5.0%         |
| 7d      | **61.3%**           | +11.3pp         | 86.0%             | $0.25| 7.5%         |
| 14d     | **61.3%**           | +11.3pp         | 86.1%             | $0.34| 9.5%         |
| 30d     | **65.8%**           | +15.8pp         | 82.8%             | $0.52| 12.0%        |

All horizons show genuine predictive signal (9-16pp above 50% random baseline).
Pre-fix illusory accuracy was 86-88% due to target leakage.

---

## Bug Fixes (Applied 2026-07-12)

### 1. Target Inversion (Critical)
- **File:** `backend/models/forecaster.py:542-565`
- **Symptom:** Models showed 86-88% directional accuracy — too good to be true
- **Root Cause:** Row-based `shift(-horizon)` on irregular time series. When data had gaps (missing days), the shift landed on wrong dates, causing the model to predict past returns from current features (look-ahead leakage)
- **Fix:** Date-based merge — create a `future` DataFrame, shift its `date` backward by horizon days, merge on `(item_id, date)`. This guarantees the target is the price exactly N days ahead, regardless of data gaps

### 2. SQLite Batch Size
- **File:** `backend/scripts/forecast_prices.py:141`
- **Symptom:** `sqlite3.OperationalError: too many SQL variables` with 5,542 forecasts
- **Root Cause:** PostgreSQL supports thousands of bind params per query; SQLite has a hard limit of 999. With 11 columns per row, batch_size=5000 produced 55,000 variables
- **Fix:** Set batch_size=90 for SQLite (999 ÷ 11 = 90 rows max), keep 5000 for PostgreSQL

### 3. Date String Parsing in Backtest
- **File:** `backend/scripts/backtest_accuracy.py:160`
- **Symptom:** `TypeError: can only concatenate str (not "datetime.timedelta") to str`
- **Root Cause:** SQLAlchemy/SQLite returns `forecast_date` as a string, not a `date` object
- **Fix:** Add `isinstance` check: parse with `date.fromisoformat()` if it's a string

---

## Pipeline Scripts

### `forecast_prices.py` — Main training + prediction
```
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/forecast_prices.py
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/forecast_prices.py --train-only
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/forecast_prices.py --predict-only
```
- Trains 36 LightGBM models (4 horizons × 3 quantiles × 3 seeds)
- Loads price history from parquet via DuckDB (1.4M rows, 8,691 items)
- Filters to 5,542 items with ≥14 days history for predictions
- Applies spike smoothing (3d median, >10% deviation → smoothed)
- Bulk-upserts to `item_forecasts` in batches

### `init_local_db.py` — Initialize SQLite from parquet
```
python3 backend/scripts/init_local_db.py
```
- **Forces** `DATABASE_URL = "sqlite:///backend/cs2_market.db"`
- Reads distinct item slugs from `prices-*.parquet` via DuckDB
- Reads events from `backend/data/cs2_events.json`
- Logs final table counts

### `evaluate_forecaster.py` — Walk-forward accuracy measurement
```
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/evaluate_forecaster.py
```
- Runs on 50 sampled backfilled items (not all 8,691 — keep evaluation fast)
- Expanding window walk-forward (60-day steps, 21-day validation)
- No Optuna, no ensemble — fixed params to measure architecture quality
- Reports per-fold accuracy, MAE, interval coverage
- ~12 min runtime for all 4 horizons

### `backtest_accuracy.py` — Mature forecast evaluation
```
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/backtest_accuracy.py
```
- Compares stored forecasts against realized prices in DB
- Filters for matured forecasts (forecast_date + horizon <= today)
- Groups by (horizon, model_version)
- Writes to `prediction_accuracy` and `forecast_outcomes` tables

---

## Key Files

| File | Lines | Role |
|------|-------|------|
| `backend/models/forecaster.py` | 1,231 | Core ML: ItemForecaster class, feature engineering, training, predict |
| `backend/scripts/forecast_prices.py` | 193 | Entry point: train + predict pipeline |
| `backend/scripts/evaluate_forecaster.py` | 366 | Walk-forward accuracy evaluation |
| `backend/scripts/backtest_accuracy.py` | 360 | Mature forecast backtesting |
| `backend/scripts/init_local_db.py` | 144 | SQLite bootstrap from parquet |
| `backend/database.py` | ~120 | SQLAlchemy ORM models (11 tables) |
| `backend/data/cs2_events.json` | — | 79 market events (major/operation/case/update) |
| `price-archive/prices-*.parquet` | 9.9M rows | Authoritative price history source |

---

## Model Details

### Feature Engineering (70+ features)
- **Price features:** Lags (1/3/7/14/30/60d), returns, winsorized returns (±500%), rolling stats (7/14/20/30/60d windows), Bollinger Bands (20d), RSI (14d), MACD, support/resistance
- **Volume features:** Lags, log-change, Z-score, volume-price confirmation
- **Temporal:** Day-of-week/month/quarter/year, weekend, sin/cos encoding, item age
- **Event:** Exponential decay features (major/operation/case_drop/update), event density 30d/90d, events next 30 days
- **Cross-sectional:** Market return, item vs market, market volatility/volume/regime
- **Pruning:** Removes features with correlation > 0.95

### Training
- **Algorithm:** LightGBM quantile regression
- **HP Search:** Optuna (30 trials, TPE sampler, MedianPruner)
- **Ensemble:** 3 seeds per quantile (42, 73, 91), prediction = median of ensemble
- **Validation:** Last 21 days held out per training window
- **Max rows:** 200,000 (subsampled from ~1.4M for speed)

### Prediction
- **Eligibility:** ≥14 days of price history
- **Spike smoothing:** Items with latest price >10% from 3d median get smoothed (~33% of items)
- **Quantile crossing fix:** If p10 > p50 or p90 < p50, use average half-width imputation
- **Sanitization:** NaN/INF/negative prices → flat prediction; high confidence downgraded for zero-volume items

### Confidence
- Binary: `high` or `low`
- Threshold-calibrated per horizon from validation set
- Criteria: range_pct (interval tightness) AND change_pct (non-trivial movement)
- Targets ≥80% directional accuracy within high-confidence bucket

---

## How to Run End-to-End

```bash
# 1. Initialize SQLite (one-time)
python3 backend/scripts/init_local_db.py

# 2. Train + predict
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/forecast_prices.py

# 3. Measure accuracy (parquet walk-forward)
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/evaluate_forecaster.py

# 4. Backtest matured forecasts (once they age)
DATABASE_URL="sqlite:///backend/cs2_market.db" python3 backend/scripts/backtest_accuracy.py
```

### Environment
- `DATABASE_URL` must be set or default to Supabase
- Local dev: `sqlite:///backend/cs2_market.db`
- Production: PostgreSQL connection string from Supabase

---

## Known Issues & Limitations

1. **Walk-forward eval runs on 50 items only** (not all 8,691) — sampling may miss item-specific variance. Full eval would take ~hours
2. **Fold variance is high** (30d std=12.0%, range 37.2%–86.8%) — model is inconsistent across market regimes
3. **Recent folds degrade** — fold 24 (Oct-Nov 2025) shows 42.3%/45.1%/32.5% accuracy for 3d/7d/14d, coinciding with high market volatility
4. **Interval coverage drops in volatile periods** — 30d fold 24 had only 41.9% coverage (target was 90%)
5. **SQLite only for dev** — Supabase migration pending for production

---

## Terminology

- **Backfilled items:** Items with complete history from Steam Community Market backfill (CSMarketAPI, ~5,542 items with ≥14 days data). Non-backfilled items (e.g., newly discovered) don't have enough history for predictions.
- **Backfilled source:** `steam_daily` — the authoritative source with the longest history.
- **Walk-forward:** Expanding window time-series cross-validation. Train on past data, validate on future data (no leakage).
- **Quantile crossing:** When predicted p10 > p50 or p90 < p50 — physically impossible. Fixed by averaging interval half-widths.
- **Spike smoothing:** Items whose latest price deviates >10% from 3d median get their price replaced with the median, preventing outlier-driven predictions.
