<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/node-20+-339933?logo=nodedotjs&logoColor=white" alt="Node 20+">
  <img src="https://img.shields.io/badge/next.js-16.2-000000?logo=nextdotjs&logoColor=white" alt="Next.js 16">
  <img src="https://img.shields.io/badge/fastapi-latest-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
</p>

<h1 align="center">CS2 Market Analyzer</h1>

<p align="center">
  <em>Counter-Strike 2 market intelligence — collect, analyze, and visualize item price data across 7 markets.</em>
</p>

<br>

---

## Overview

Full-stack analytics platform for the CS2 skin economy. A daily pipeline collects multi-source prices from **7 markets** (Steam, Skinport, Buff163, CSFloat, CSMoney, CSGOTrader, Youpin), archives to **Parquet**, and serves through a **FastAPI** REST API to a **Next.js** dashboard. ML price forecasts via **LightGBM quantile ensembles** replace traditional trend analysis.

```
┌─────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  7 Market APIs  │ ──▶ │  FastAPI / Supabase │ ──▶ │  Next.js Dashboard│
│                 │     │                    │     │                  │
└────────┬────────┘     └──────────┬─────────┘     └────────┬─────────┘
         ▼                         ▼                         ▼
┌─────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│ Parquet Archive │     │   PostgreSQL / PG   │     │ Recharts + Framer│
│ (13 years)      │     │   (daily closes)    │     │ Motion           │
└─────────────────┘     └────────────────────┘     └──────────────────┘
```

<br>

## Features

<table>
  <tr>
    <td width="50%">
      <h4>📊 Multi-Source Collection</h4>
      Daily aggregator polling 7 CS2 skin markets in parallel
    </td>
    <td width="50%">
      <h4>🗄️ Parquet Price Archive</h4>
      13 years of history, queryable via DuckDB
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h4>🤖 ML Price Forecasts</h4>
      LightGBM quantile regression (q10/q50/q90) across 3/7/14/30d horizons.<br>
      6-member diversified ensemble with walk-forward validation &amp; Optuna tuning
    </td>
    <td width="50%">
      <h4>🔄 Regime-Switching</h4>
      Separate models per market regime (bear / range / bull)
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h4>🎯 Accuracy Tracking</h4>
      Automated daily backtesting with MAE, MAPE, directional accuracy, drift alerts
    </td>
    <td width="50%">
      <h4>🔍 Model Explainability</h4>
      Per-item feature importance via SHAP-style analysis
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h4>⚡ Event Impact Analysis</h4>
      Quantified market-event price impacts with correlation scoring
    </td>
    <td width="50%">
      <h4>📈 Market Opportunities</h4>
      Undervalued, overheated, and momentum signals surfaced daily
    </td>
  </tr>
  <tr>
    <td colspan="2">
      <h4>🖥️ Interactive Dashboard</h4>
      Responsive Recharts visualizations, grouped market views, item detail pages, forecast overlays
    </td>
  </tr>
</table>

<br>

## Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Framer Motion |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings |
| **Data** | PostgreSQL / Supabase, DuckDB, Parquet, Pandas, NumPy, SciPy |
| **ML** | LightGBM, Optuna, Joblib |
| **Automation** | GitHub Actions (7 scheduled workflows) |

<br>

## Project Structure

```
cs2-market-analyzer/
├── backend/              # FastAPI server, routes, collectors, models, tests
├── frontend/             # Next.js app router, components, API client
├── docs/                 # Architecture, changelog, references, research
├── price-archive/        # Parquet price data (13-year history)
└── .github/workflows/    # 7 automated CI/CD workflows
```

<br>

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+ (or Supabase account)

### Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # configure DATABASE_URL
python scripts/run_task.py migrate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev              # → http://localhost:3000
```

<br>

## Commands

### Backend Tasks

Run via `python scripts/run_task.py <task>`:

| Task | Description |
|------|-------------|
| `aggregate` | Full aggregator collection (all items, all sources) |
| `priority` | Top 2000 items collection |
| `migrate` | Run pending Alembic migrations |
| `backtest` | Run forecast accuracy backtest |
| `backtest_historical` | Run historical walk-forward backtest |

### Frontend

| Command | Description |
|---------|-------------|
| `npm run dev` | Development server (localhost:3000) |
| `npm run build` | Type-check + production build |
| `npm run lint` | ESLint |

### Testing

```bash
cd backend && source venv/bin/activate && pytest
```

<br>

## Data Flow

```
22:00 UTC     Supply Scraper        → listing supply depth        → Supabase
23:00 UTC     Aggregator            → 7 source prices             → Parquet + Supabase
Every 2h      Player Count          → Steam active players        → Supabase + Parquet
(chained)     Forecast              → LightGBM ensemble           → item_forecasts
(chained)     Backtest              → accuracy tracking           → prediction_accuracy
Weekly Sun    Event Correlation     → market-event price impacts  → analysis tables
```

<br>

## Scheduled Workflows

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `aggregator-update` | Daily 23:00 UTC | Multi-source collection + Parquet archive commit |
| `supply-scraper` | Daily 22:00 UTC | Listing supply-depth per item |
| `price-forecast` | Chained off aggregator | LightGBM predictions (predict-only Tue–Sun, full retrain Mon) |
| `backtest-accuracy` | Chained + Mon–Sat 08:00 UTC | Daily forecast accuracy evaluation |
| `event-correlation-analysis` | Weekly Sun 04:00 UTC | Market-event price impacts |
| `discover-new-items` | Ad hoc | Scan for newly tradable items |
| `reddit-sentiment` | Periodic | Community sentiment analysis |

<br>

## Security

- Never commit `.env` files — use `.env.example` as template
- Replace default `SECRET_KEY` in production deployments
- Enable GitHub Secret Scanning for the repository

<br>

## License

MIT
