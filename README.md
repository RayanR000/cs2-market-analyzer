# CS2 Market Intelligence Platform

A full-stack web application for tracking, analyzing, and visualizing Counter-Strike 2 in-game economy data (skins, cases, stickers).

## Project Overview

This platform provides:
- **Full price history charts** from item release date or earliest available data
- **Event overlay system** to show market-moving events
- **Trend scoring engine** with bullish/neutral/bearish classifications
- **Lightweight prediction layer** using moving averages and linear regression
- **Opportunity detection** (undervalued, overheated, momentum items)
- **Interactive dashboards** and discovery interfaces

See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for detailed feature descriptions.

## Tech Stack

- **Frontend**: Next.js 15+ with TypeScript and Tailwind CSS
- **Backend**: FastAPI (Python) with SQLAlchemy ORM
- **Database**: Supabase (PostgreSQL)
- **Data Pipeline**: Python scheduled jobs for daily market data ingestion

## Project Structure

```
cs2-market-analyzer/
├── backend/              # FastAPI backend
│   ├── main.py          # Application entry point
│   ├── database.py       # SQLAlchemy models
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── config.py         # Configuration management
│   ├── routers/          # API route handlers
│   │   ├── items.py      # Item endpoints
│   │   ├── opportunities.py
│   │   ├── events.py
│   │   └── __init__.py
│   ├── requirements.txt  # Python dependencies
│   └── venv/            # Virtual environment
│
├── frontend/             # Next.js frontend
│   ├── app/             # Next.js app directory
│   ├── components/      # React components
│   ├── lib/
│   │   └── api.ts       # API client
│   ├── public/          # Static assets
│   ├── package.json
│   └── tsconfig.json
│
├── .env.example         # Environment variables template
├── PROJECT_OVERVIEW.md  # Detailed project overview
└── README.md           # This file
```

## Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL (or Supabase account)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
cp ../.env.example .env

# Update .env with your database URL
# DATABASE_URL=postgresql://user:password@localhost:5432/cs2_market

# Run the server
python main.py
```

The API will be available at `http://localhost:8000` with docs at `http://localhost:8000/api/docs`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env.local (copy environment variables)
cp ../.env.example .env.local

# Update .env.local with your API URL
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## API Endpoints (MVP)

### Items
- `GET /items/` - List all items
- `GET /items/search?q=...` - Search items
- `GET /items/trending` - Get trending items
- `GET /items/{item_id}` - Get item details
- `GET /items/{item_id}/price-history` - Get price history
- `GET /items/{item_id}/trends` - Get trend analysis
- `GET /items/{item_id}/prediction` - Get price prediction
- `GET /items/{item_id}/events` - Get related events

### Opportunities
- `GET /opportunities/` - Get all opportunities
- `GET /opportunities/undervalued` - Get undervalued items
- `GET /opportunities/overheated` - Get overheated items
- `GET /opportunities/momentum` - Get momentum items

### Events
- `GET /events/` - List market events
- `GET /events/recent` - Get recent events
- `GET /events/timeline` - Get events timeline

## Implementation Plan

The project is being developed in phases:

**Phase 1: Foundation & Data Infrastructure** (In Progress)
- ✅ Backend scaffold with FastAPI
- ✅ Database models designed
- ✅ API routers structured
- ✅ Frontend initialized with Next.js
- ✅ API client created

**Phase 2-8: Core Features** (Planned)
- Data pipeline and ingestion
- Analytics & feature engineering
- Frontend UI development
- Testing & optimization
- Deployment

See [plan.md](/plan.md) for detailed phase breakdown.

## Development Guidelines

- Use TypeScript in frontend, Python with type hints in backend
- Follow REST API conventions
- Add tests for critical paths (target >70% coverage)
- Document APIs using OpenAPI/Swagger

## Future Enhancements

- Advanced ML forecasting (XGBoost, ARIMA)
- Sentiment analysis from community
- Automated alerts
- Portfolio tracking
- Mobile app

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
