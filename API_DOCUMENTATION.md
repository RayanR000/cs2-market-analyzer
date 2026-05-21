# CS2 Market Intelligence API Documentation

## Overview

The CS2 Market Intelligence API provides comprehensive endpoints for tracking CS2 in-game economy data, analyzing market trends, and identifying investment opportunities.

**Base URL:** `http://localhost:8000/api`  
**API Docs:** `http://localhost:8000/api/docs` (Swagger UI)

---

## Items Endpoints

### List Items
```
GET /items/
```

List all items with optional filtering by type.

**Query Parameters:**
- `type` (string, optional): Filter by item type (`skin`, `case`, `sticker`)
- `skip` (integer, default: 0): Number of items to skip (pagination)
- `limit` (integer, default: 50, max: 100): Number of items to return

**Example Response:**
```json
{
  "items": [
    {
      "id": 1,
      "item_id": "dragon-lore-souvenir",
      "name": "Dragon Lore Souvenir",
      "type": "skin",
      "release_date": "2023-01-15T00:00:00"
    }
  ],
  "total": 245,
  "skip": 0,
  "limit": 50
}
```

### Search Items
```
GET /items/search
```

Search items by name (case-insensitive).

**Query Parameters:**
- `q` (string, required, min: 1 character): Search query

**Example Request:**
```
GET /items/search?q=dragon
```

**Example Response:**
```json
{
  "results": [
    {
      "id": 1,
      "item_id": "dragon-lore-souvenir",
      "name": "Dragon Lore Souvenir",
      "type": "skin"
    }
  ],
  "total": 1
}
```

### Get Trending Items
```
GET /items/trending
```

Get trending items by price movement.

**Query Parameters:**
- `limit` (integer, default: 10, max: 50): Number of items to return
- `days` (integer, default: 7, range: 1-365): Time period for trend calculation

**Example Response:**
```json
{
  "trending": [
    {
      "item_id": "m4a1-s-neon-rider",
      "name": "M4A1-S Neon Rider",
      "type": "skin",
      "latest_price": 45.67
    }
  ],
  "timestamp": "2024-01-15T10:30:00",
  "period_days": 7
}
```

### Get Item Details
```
GET /items/{item_id}
```

Get detailed information about a specific item.

**Path Parameters:**
- `item_id` (string, required): The item identifier

**Example Response:**
```json
{
  "id": 1,
  "item_id": "dragon-lore-souvenir",
  "name": "Dragon Lore Souvenir",
  "type": "skin",
  "release_date": "2023-01-15T00:00:00"
}
```

### Get Price History
```
GET /items/{item_id}/price-history
```

Get historical price data for an item.

**Path Parameters:**
- `item_id` (string, required): The item identifier

**Query Parameters:**
- `days` (integer, default: 30, range: 1-365): Number of days of history
- `skip` (integer, default: 0): Number of records to skip
- `limit` (integer, default: 1000, max: 10000): Number of records to return

**Example Response:**
```json
{
  "item_id": "m4a1-s-neon-rider",
  "history": [
    {
      "id": 100,
      "timestamp": "2024-01-15T10:00:00",
      "price": 45.50,
      "volume": 1200,
      "median_price": 45.67
    }
  ],
  "total": 30
}
```

### Get Trend Analysis
```
GET /items/{item_id}/trends
```

Get comprehensive trend analysis including technical indicators.

**Path Parameters:**
- `item_id` (string, required): The item identifier

**Example Response:**
```json
{
  "item_id": "m4a1-s-neon-rider",
  "item_name": "M4A1-S Neon Rider",
  "current_price": 45.50,
  "trend_direction": "bullish",
  "confidence": "medium",
  "trend_score": 0.642,
  "indicators": {
    "sma_7": 44.23,
    "sma_30": 43.15,
    "volatility": 0.0856,
    "rsi": 62.34,
    "bollinger_upper": 47.12,
    "bollinger_middle": 44.50,
    "bollinger_lower": 41.88,
    "macd": 1.2340,
    "macd_signal": 1.1956,
    "support": 42.00,
    "resistance": 48.00
  },
  "factors": [
    "7-day MA above 30-day MA (bullish)",
    "Price above lower Bollinger Band"
  ],
  "timestamp": "2024-01-15T10:30:00"
}
```

**Indicators Explained:**
- **SMA (7/30):** Simple Moving Average over 7 and 30 days
- **Volatility:** Standard deviation of returns (0.0-1.0 scale)
- **RSI:** Relative Strength Index (0-100, >70 overbought, <30 oversold)
- **Bollinger Bands:** Upper/middle/lower bands showing price volatility ranges
- **MACD:** Moving Average Convergence Divergence momentum indicator
- **Support/Resistance:** Key price levels

### Get Price Prediction
```
GET /items/{item_id}/prediction
```

Get price forecast for an item over 7 or 30 days.

**Path Parameters:**
- `item_id` (string, required): The item identifier

**Query Parameters:**
- `period` (string, default: "7_days", options: "7_days", "30_days"): Forecast period

**Example Response:**
```json
{
  "item_id": "m4a1-s-neon-rider",
  "item_name": "M4A1-S Neon Rider",
  "current_price": 45.50,
  "forecast": {
    "low": 42.10,
    "mid": 44.80,
    "high": 47.50
  },
  "period_days": 7,
  "period_label": "7_days",
  "trend_direction": "bullish",
  "confidence": "medium",
  "volatility": 0.0856,
  "methodology": "Linear regression with volatility-adjusted bands",
  "timestamp": "2024-01-15T10:30:00"
}
```

### Get Item Events
```
GET /items/{item_id}/events
```

Get market events related to a specific item.

**Path Parameters:**
- `item_id` (string, required): The item identifier

**Query Parameters:**
- `limit` (integer, default: 20): Maximum number of events to return

**Example Response:**
```json
{
  "item_id": "m4a1-s-neon-rider",
  "events": []
}
```

---

## Opportunities Endpoints

### Get All Opportunities
```
GET /opportunities/
```

Get top opportunities across all types (undervalued, overheated, momentum).

**Query Parameters:**
- `type` (string, optional): Filter by opportunity type (`undervalued`, `overheated`, `momentum`)
- `limit` (integer, default: 20, range: 1-100): Maximum items to return

**Example Response:**
```json
{
  "opportunities": [
    {
      "item_id": "ak-47-phantom-disruptor",
      "item_name": "AK-47 Phantom Disruptor",
      "item_type": "skin",
      "current_price": 28.50,
      "opportunity_type": "undervalued",
      "opportunity_score": 7.5,
      "reason": "Trading 7.5% below 90-day trend",
      "trend": "bullish",
      "confidence": "medium",
      "volatility": 0.0654
    }
  ],
  "total": 15,
  "filtered_type": null
}
```

### Get Undervalued Items
```
GET /opportunities/undervalued
```

Get items trading below their 90-day historical trend (buy opportunities).

**Query Parameters:**
- `limit` (integer, default: 10, range: 1-50): Maximum items to return
- `min_discount` (float, default: 5.0, range: 0-100): Minimum discount percentage

**Example Response:**
```json
{
  "items": [
    {
      "item_id": "ak-47-phantom-disruptor",
      "item_name": "AK-47 Phantom Disruptor",
      "item_type": "skin",
      "current_price": 28.50,
      "baseline_price": 30.75,
      "discount_percent": 7.3,
      "trend": "bullish",
      "confidence": "medium",
      "volatility": 0.0654,
      "opportunity_score": 10.95
    }
  ],
  "total": 8,
  "min_discount_filter": 5.0
}
```

### Get Overheated Items
```
GET /opportunities/overheated
```

Get items trading above their 90-day trend (sell opportunities).

**Query Parameters:**
- `limit` (integer, default: 10, range: 1-50): Maximum items to return
- `min_premium` (float, default: 10.0, range: 0-500): Minimum premium percentage

**Example Response:**
```json
{
  "items": [
    {
      "item_id": "m4a1-s-neon-rider",
      "item_name": "M4A1-S Neon Rider",
      "item_type": "skin",
      "current_price": 48.99,
      "baseline_price": 43.50,
      "premium_percent": 12.6,
      "trend": "bearish",
      "confidence": "medium",
      "volatility": 0.0856,
      "risk_score": 10.08
    }
  ],
  "total": 5,
  "min_premium_filter": 10.0
}
```

### Get Momentum Items
```
GET /opportunities/momentum
```

Get items with strong directional movement (trending items).

**Query Parameters:**
- `limit` (integer, default: 10, range: 1-50): Maximum items to return
- `min_change` (float, default: 5.0, range: 0-100): Minimum price change percentage

**Example Response:**
```json
{
  "items": [
    {
      "item_id": "operation-alpha-case",
      "item_name": "Operation Alpha Case",
      "item_type": "case",
      "current_price": 3.75,
      "change_percent_7d": 15.8,
      "direction": "upward",
      "trend": "bullish",
      "confidence": "high",
      "volatility": 0.1234,
      "momentum_score": 12.64
    }
  ],
  "total": 12,
  "min_change_filter": 5.0
}
```

---

## Events Endpoints

### List Market Events
```
GET /events/
```

List all market events with optional filtering.

**Query Parameters:**
- `type` (string, optional): Filter by event type (`major`, `update`, `case_drop`, `operation`)
- `skip` (integer, default: 0): Number of events to skip
- `limit` (integer, default: 50, range: 1-100): Number of events to return

**Example Response:**
```json
{
  "events": [
    {
      "id": 1,
      "type": "case_drop",
      "timestamp": "2024-01-15T08:00:00",
      "description": "New weapon case released: Operation Alpha Case"
    }
  ],
  "total": 48
}
```

### Get Events Timeline
```
GET /events/timeline
```

Get events in chronological order.

**Query Parameters:**
- `skip` (integer, default: 0): Number of events to skip
- `limit` (integer, default: 100, range: 1-500): Number of events to return

**Example Response:**
```json
{
  "events": [
    {
      "id": 1,
      "type": "case_drop",
      "timestamp": "2024-01-15T08:00:00",
      "description": "New weapon case released: Operation Alpha Case"
    }
  ],
  "total": 48
}
```

### Get Recent Events
```
GET /events/recent
```

Get most recent market events.

**Query Parameters:**
- `days` (integer, default: 30, range: 1-365): Number of days to look back
- `limit` (integer, default: 20, range: 1-100): Maximum events to return

**Example Response:**
```json
{
  "events": [
    {
      "id": 2,
      "type": "update",
      "timestamp": "2024-01-14T16:30:00",
      "description": "Game balance update: AK-47 recoil reduced by 5%"
    }
  ],
  "total": 3
}
```

---

## Health & Status Endpoints

### Health Check
```
GET /health
```

Check API status.

**Example Response:**
```json
{
  "status": "ok",
  "service": "cs2-market-api"
}
```

### Root
```
GET /
```

Get API information.

**Example Response:**
```json
{
  "message": "CS2 Market Intelligence API",
  "version": "0.1.0",
  "docs": "/api/docs"
}
```

---

## Error Responses

All endpoints follow standard HTTP status codes:

- **200 OK:** Successful request
- **400 Bad Request:** Invalid parameters
- **404 Not Found:** Resource not found
- **500 Internal Server Error:** Server error

**Error Response Format:**
```json
{
  "detail": "Item not found"
}
```

---

## Authentication

Currently, all endpoints are publicly accessible. Authentication will be added in Phase 5.

---

## Rate Limiting

Rate limiting will be implemented in Phase 5. Currently, no limits apply.

---

## Pagination

List endpoints support offset/limit pagination:

- `skip`: Number of items to skip (default: 0)
- `limit`: Number of items to return (default: 50, max varies by endpoint)

---

## Data Formats

### Timestamp Format
All timestamps are in ISO 8601 format (UTC): `2024-01-15T10:30:00`

### Price Format
Prices are returned as floats with up to 2 decimal places.

### Trend Direction
- `bullish`: Price likely to increase
- `bearish`: Price likely to decrease
- `neutral`: No clear direction
- `insufficient_data`: Not enough data for analysis

### Confidence Levels
- `low`: <50% confidence
- `medium`: 50-75% confidence
- `high`: >75% confidence

---

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/items/` | List items |
| GET | `/items/search` | Search items |
| GET | `/items/trending` | Get trending items |
| GET | `/items/{item_id}` | Get item details |
| GET | `/items/{item_id}/price-history` | Get price history |
| GET | `/items/{item_id}/trends` | Get trend analysis |
| GET | `/items/{item_id}/prediction` | Get price prediction |
| GET | `/items/{item_id}/events` | Get item events |
| GET | `/opportunities/` | Get all opportunities |
| GET | `/opportunities/undervalued` | Get undervalued items |
| GET | `/opportunities/overheated` | Get overheated items |
| GET | `/opportunities/momentum` | Get momentum items |
| GET | `/events/` | List events |
| GET | `/events/timeline` | Get events timeline |
| GET | `/events/recent` | Get recent events |
| GET | `/health` | Health check |
| GET | `/` | API info |

---

## Implementation Status

**Phase 3 (API Development) - Complete:**
- ✅ All 8 Items endpoints implemented with Phase 2 analytics integration
- ✅ All 4 Opportunities endpoints with undervalued/overheated/momentum detection
- ✅ All 3 Events endpoints with filtering and timeline views
- ✅ Health check and status endpoints
- ✅ Comprehensive error handling
- ✅ Request validation with FastAPI Query parameters

**Next Steps (Phase 4+):**
- Authentication & Authorization
- Advanced filtering & sorting
- API pagination optimization
- Rate limiting
- Caching layer
- WebSocket support for real-time updates
- OpenAPI documentation generation
- API versioning
