# CS2 Market Analyzer

Counter-Strike 2 market intelligence — collect, analyze, and visualize item price data.

## Overview

Full-stack analytics platform. Daily pipeline pulls multi-source prices from 7 markets (Steam, Skinport, Buff163, CSFloat, CSMoney, CSGOTrader, Youpin), writes to a Parquet archive, and serves through a FastAPI REST API to a Next.js dashboard. ML price forecasts (LightGBM quantile ensembles) replace traditional trend analysis.

```
CSGOTrader API ──▶ API / DB (FastAPI) ──▶ Dashboard (Next.js)
      │                     │                     │
      ▼                     ▼                     ▼
Parquet Archive         Supabase PG             Recharts
(data-archive branch)   (daily closes)          + Framer
```

## Features

- **Multi-Source Collection** — daily aggregator from 7 markets
- **Parquet Price Archive** — 13 years of history, queryable via DuckDB
- **ML Price Forecasts** — LightGBM quantile regression (q10/q50/q90) across 3/7/14/30d horizons, 6-member diversified ensemble, walk-forward validation, Optuna tuning
- **Regime-Switching** — separate models per market regime (bear/range/bull)
- **Accuracy Tracking** — automated daily backtesting with MAE, MAPE, directional accuracy, drift alerts
- **Model Explainability** — per-item feature importance
- **Event Impact Analysis** — quantified market-event price impacts
- **Market Opportunities** — undervalued, overheated, momentum signals
- **Interactive Dashboard** — responsive charts, grouped market views, item detail

## Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Framer Motion |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings |
| **Data** | PostgreSQL / Supabase, DuckDB, Parquet, Pandas, NumPy, SciPy |
| **ML** | LightGBM, Optuna |
| **Automation** | GitHub Actions (7 workflows) |

## Project Structure

```
backend/            — FastAPI server, routes, collectors, models, tests
frontend/           — Next.js app router, components, API client
docs/               — Architecture, research, changelog, reference
price-archive/      — Parquet price data (13 years)
.github/workflows/  — 7 scheduled workflows
```

## Getting Started

### Prerequisites
- Python 3.11+, Node.js 18+, PostgreSQL 14+ (or Supabase)

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # configure DATABASE_URL
python scripts/run_task.py migrate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

## Commands

### Backend Tasks (`python scripts/run_task.py <task>`)
| Task | Description |
|------|-------------|
| `aggregate` | Full aggregator collection (all items, all sources) |
| `priority` | Top 2000 items collection |
| `migrate` | Run pending Alembic migrations |
| `backtest` | Run forecast accuracy backtest |
| `backtest_historical` | Run historical walk-forward backtest |

### Frontend
```bash
npm run dev     # Development server (http://localhost:3000)
npm run build   # Type-check + production build
npm run lint    # ESLint
```

### Testing
```bash
cd backend && source venv/bin/activate && pytest
```

## Data Flow

```
22:00  Supply Scraper → listing supply depth → Supabase
23:00  Aggregator → 7 source prices → Parquet (data-archive) + Supabase
Every 2h  Player Count → Steam active players → Supabase + Parquet
Chained  Forecast → LightGBM ensemble → item_forecasts
Chained  Backtest → accuracy tracking → prediction_accuracy
Weekly   Event Correlation → event-impact analysis
```

## Scheduled Workflows

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `aggregator-update` | Daily 23:00 UTC | Multi-source collection + Parquet archive commit |
| `supply-scraper` | Daily 22:00 UTC | Listing supply-depth per item |
| `player-count-hourly` | Every 2h | Steam player-count tracking |
| `price-forecast` | Chained off aggregator | LightGBM predictions (predict-only Tue–Sun, full retrain Mon) |
| `backtest-accuracy` | Chained + cron 08:00 UTC Mon–Sat | Daily forecast accuracy evaluation |
| `event-correlation-analysis` | Weekly Sun 04:00 UTC | Market-event price impacts |

## Security

- Never commit `.env` files — use `.env.example` as template
- Replace default `SECRET_KEY` in production
- Enable GitHub Secret Scanning

## License

MIT
