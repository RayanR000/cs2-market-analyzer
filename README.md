<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/CS2%20Market%20Analyzer-121212?style=for-the-badge&logo=counter-strike&logoColor=white">
    <img alt="CS2 Market Analyzer" src="https://img.shields.io/badge/CS2%20Market%20Analyzer-FFFFFF?style=for-the-badge&logo=counter-strike&logoColor=black" width="320">
  </picture>
</p>

<p align="center">
  <em>Counter-Strike 2 market intelligence — collect, analyze, and visualize item price data.</em>
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#features">Features</a> •
  <a href="#stack">Stack</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#usage">Usage</a> •
  <a href="#deployment">Deployment</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/node-18%2B-339933?style=flat-square&logo=node.js&logoColor=white" alt="Node">
  <img src="https://img.shields.io/badge/next.js-16-000000?style=flat-square&logo=next.js&logoColor=white" alt="Next.js">
  <img src="https://img.shields.io/badge/fastapi-0.115%2B-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/postgresql-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/license-MIT-yellow?style=flat-square" alt="License">
</p>

---

## Overview

CS2 Market Analyzer is a full-stack analytics platform that collects, validates, and visualizes Counter-Strike 2 skin market data. The backend runs scheduled data pipelines (collection, trend analysis, pruning) and exposes a REST API consumed by the frontend dashboard.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Collectors   │────▶│    API / DB   │────▶│   Dashboard  │
│  (Python)     │     │  (FastAPI)   │     │  (Next.js)   │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                       │
       ▼                                       ▼
  GitHub Actions                          Recharts + Framer
  (scheduled jobs)                        (interactive UI)
```

## Features

- **Automated Collection** — scrapes all CS2 items via priority and full-aggregator pipelines
- **Trend Analysis** — 90-day and full-history trend computation with opportunity detection
- **Database Maintenance** — automated pruning, downsampling, and schema migrations
- **Interactive Dashboard** — responsive charts, market views, and portfolio tracking
- **Scheduled Automation** — GitHub Actions workflows for recurring collection and maintenance
- **Price Forecasting** — ML-based price predictions (LightGBM)
- **Event Correlation** — tracks how game updates and major events affect skin prices

## Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Framer Motion |
| **Backend** | Python, FastAPI, SQLAlchemy, Alembic, Pydantic Settings |
| **Data** | PostgreSQL / Supabase, Pandas, NumPy, SciPy |
| **ML** | LightGBM (price forecasting) |
| **Automation** | GitHub Actions (7 scheduled workflows) |

## Repository Structure

```
├── backend/
│   ├── analytics/        # Trend computation, opportunity detection
│   ├── api/              # FastAPI route handlers
│   ├── collectors/       # Steam, aggregator, and market data collectors
│   ├── models/           # SQLAlchemy ORM models
│   ├── migrations/       # Alembic migration scripts
│   ├── scripts/          # Task runners, analyzers, maintenance
│   ├── tests/            # pytest suite
│   ├── main.py           # FastAPI app entry point
│   └── config.py         # Pydantic settings
├── frontend/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components
│   └── lib/              # API client, utilities
├── .github/workflows/    # 7 CI/CD workflows
├── PRODUCT.md             # Product positioning & audience
├── DESIGN.md              # Visual direction & UX principles
└── WORKFLOW_MONITORING.md # Scheduled job operational guide
```

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL 14+ (or Supabase account)

### 1. Clone

```bash
git clone https://github.com/RayanR000/cs2-market-analyzer.git
cd cs2-market-analyzer
```

### 2. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit with your database URL
```

Configure `backend/.env`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `ENVIRONMENT` | `development` or `production` |
| `DEBUG` | Enable debug logging |
| `STEAM_API_KEY` | (Optional) Steam Web API key |
| `CS2SH_API_KEY` | (Optional) CS2 secondary market key |
| `FRONTEND_URL` | Frontend origin for CORS |
| `SECRET_KEY` | Session signing secret (rotate in production) |

### 3. Database Migrations

```bash
cd backend
source venv/bin/activate
python scripts/run_task.py migrate
```

### 4. Frontend Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API base URL |

### 5. Start Development

```bash
# Terminal 1 — Backend API
cd backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Usage

### Backend Tasks

```bash
cd backend
source venv/bin/activate
python scripts/run_task.py <task>
```

| Task | Description |
|------|-------------|
| `aggregate` | Full collector run (all items) |
| `priority` | Scrape top 2000 priority items |
| `prune` | Database pruning & downsampling |
| `trends` | 90-day trend analysis & opportunity detection |
| `long_term_trends` | Full-history trend analysis |
| `migrate` | Run pending Alembic migrations |

### Frontend Commands

```bash
cd frontend
npm run dev     # Development server
npm run build   # Production build
npm run start   # Start production server
npm run lint    # Run ESLint
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/items/` | List items (paginated) |
| GET | `/items/search?q=` | Search items |
| GET | `/items/trending` | Trending items |
| GET | `/items/{id}/price-history` | Price history for an item |
| GET | `/items/{id}` | Item details |
| GET | `/trends` | Trend analysis results |
| GET | `/prediction` | Price predictions |
| GET | `/opportunities/` | Market opportunities |
| GET | `/opportunities/undervalued` | Undervalued items |
| GET | `/opportunities/momentum` | Momentum items |
| GET | `/events/` | Market events |
| GET | `/events/recent` | Recent events |
| GET | `/auth/me` | Current user |
| GET | `/portfolio/inventory` | User portfolio |

### Testing

```bash
cd backend && source venv/bin/activate && pytest
```

### Pre-commit Checks

```bash
pip install pre-commit detect-secrets
pre-commit install
detect-secrets scan > .secrets.baseline  # optional
```

## Deployment

### Frontend

Deploy as a standard Next.js application (Vercel recommended):

```bash
cd frontend
npm run build
npm run start   # or deploy via Vercel CLI / GitHub import
```

### Backend

The backend runs on-demand via scheduled GitHub Actions. For a persistent API server:

```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Scheduled Workflows

Seven GitHub Actions workflows handle recurring operations:

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `aggregator-update` | Every 6h | Full item data collection |
| `daily-trend-analysis` | Daily | 90-day trend computation |
| `long-term-trend-analysis` | Weekly | Full history analysis |
| `db-maintenance` | Daily | Pruning & downsampling |
| `discover-new-items` | Daily | Detect new market items |
| `event-correlation-analysis` | Weekly | Game event impact analysis |
| `price-forecast` | Weekly | ML price predictions |

### Database

Point `DATABASE_URL` to your production PostgreSQL or Supabase instance. Run migrations:

```bash
python scripts/run_task.py migrate
```

## Security

- Never commit `.env` files — the repository includes `.env.example` as a template
- Replace the default `SECRET_KEY` in production
- Enable [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning) for your repository
- Restrict database credentials to the minimum required permissions

## Contributing

1. Keep changes focused and well-documented.
2. Update Alembic migrations when the schema changes.
3. Run `pytest` and `npm run lint` before opening a PR.
4. Update docs when behavior changes.

## License

MIT — see [LICENSE](LICENSE) for details.
