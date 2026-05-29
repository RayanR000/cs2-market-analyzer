# CS2 Market Intelligence Platform

A full-stack web application for tracking, analyzing, and visualizing Counter-Strike 2 in-game economy data (skins, cases, stickers).

This README was updated to reflect recent refactors and feature work across the repo. It provides a concise summary and accurate quickstart steps — for a complete history, inspect the git log or relevant CHANGELOG/commits.

## Quick Summary of recent changes

- Repository reorganized and refactored across backend and frontend
- API surface consolidated and documented in this README
- Data collection and pipeline code updated; collection runs on startup
- Frontend bootstrapped with improved discovery and dashboards

(If any detail below looks out-of-date, point to specific files or commits and an updated draft will be applied.)

## Features

- Full price history charts and item timelines
- Event overlays to highlight market-moving events
- Trend scoring (bullish/neutral/bearish) and simple predictive signals
- Opportunity detection: undervalued, overheated, momentum
- Interactive dashboards and search/discovery UI

## Tech Stack

- Frontend: Next.js + TypeScript + Tailwind CSS
- Backend: FastAPI (Python) with SQLAlchemy
- Database: PostgreSQL (Supabase compatible)
- Data sources: Steam Community Market and supplemental collectors (CSFloat)

## Project layout (high level)

- backend/ — FastAPI app, routers, models, and data pipeline
- frontend/ — Next.js app, components, and API client
- .env.example — environment variables template
- PROJECT_OVERVIEW.md, REAL_DATA_COLLECTION.md — documentation

## Getting started (developer)

Prereqs: Python 3.9+, Node.js 18+, PostgreSQL or Supabase

Backend:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env to configure DATABASE_URL and other secrets
python main.py
```

Frontend:

```bash
cd frontend
npm install
cp ../.env.example .env.local
# Update NEXT_PUBLIC_API_URL if required
npm run dev
```

API docs available at: http://localhost:8000/api/docs (after backend starts)

## Important API endpoints (MVP)

- Items: /items/, /items/search, /items/trending, /items/{id}, /items/{id}/price-history
- Opportunities: /opportunities/, /opportunities/undervalued, /opportunities/momentum
- Events: /events/, /events/recent, /events/timeline
- Admin: /admin/collect-now, /admin/collection-status, /admin/data-stats

Refer to backend/routers for exact parameter names and payloads.

## Real-time collection

- Collection starts automatically on backend startup
- Hourly price refreshes for tracked items (configurable)
- Anomaly detection and validation before persisting
- Demo/dev environments include synthetic backfill for UI rendering

## Development guidelines

- Frontend in TypeScript; backend in Python with type hints
- Use REST and document via OpenAPI/Swagger
- Add tests for critical paths; aim for high coverage on core logic

## Troubleshooting & tips

- Backend fails to connect: verify DATABASE_URL in backend/.env
- No data in UI: ensure backend collection is running and check /admin/collection-status
- To inspect recent changes: git log --oneline --decorate --stat

## Contributing & License

- Add contribution guidelines in CONTRIBUTING.md
- Add a LICENSE file (e.g., MIT) and reference it here

---

If this summary looks good, the README has been updated. If specific sections need different wording or more detail (installation, API examples, deployment), specify which sections to expand and sample changes to include.