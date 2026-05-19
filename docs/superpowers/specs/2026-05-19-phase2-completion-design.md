# Phase 2 Completion: End-to-End Real Data Pipeline

**Date**: 2026-05-19  
**Scope**: Complete the data pipeline to collect real Steam API data, seed historical context, and make trend analysis operational  
**Goal**: Get real price data flowing hourly into the database and served via API

---

## Current State

**What works:**
- Backend server starts and connects to Supabase
- Database schema initialized
- 8 sample items in database with 240 synthetic price records
- API endpoints defined and returning data
- Trend analyzer implemented
- Pipeline scheduler initialized

**What's broken:**
- Steam API data collection failing (0/8 items returning data)
- Root cause: hash name mismatch - Steam requires specific market hash names, not item names
- Only 8 items in catalog (need 100+)
- No synthetic historical data for context/testing
- New data source files (cs2_data_sources.py, comprehensive_loader.py) not integrated

**Result**: Pipeline is running hourly but collecting 0 real data points.

---

## Solution Architecture

### Data Sources
1. **cs2_data_sources.py** - Authoritative catalog
   - 100+ real CS2 items (weapon skins, cases, stickers)
   - Complete game events database
   - Synthetic historical price generator (realistic random walk patterns)

2. **Steam Community Market API** - Real ongoing data
   - Market listing endpoint (to resolve item names → hash names)
   - Price history endpoint (current prices, volume)
   - Rate limited (1 req/sec to be safe)

### Initialization Flow (Startup)
```
app.startup():
  1. Load cs2_data_sources.CS2ItemCatalog.get_all_items() 
     → 100+ items into Item table
  
  2. Run comprehensive_loader.load_complete_catalog(generate_history=True, days=365)
     → For each item, generate 365 days of synthetic prices
     → Insert into price_history table
     → Load cs2_data_sources.CS2GameEvents into Event table
  
  3. Start DataPipeline scheduler
     → Schedule hourly collection job
     → First run immediately, then every 3600s
```

### Collection Flow (Every Hour)
```
pipeline.run_daily_collection():
  1. Get all items from database
  
  2. For each item:
     a. Use improved steam_market.py to:
        - Query Steam market listing API to find the item's market hash name
        - Get current price & volume from price history endpoint
        - Validate data (check for nulls, outliers, reasonable ranges)
        - Create PriceHistory record with current timestamp
     
     b. On error: log warning, continue to next item
  
  3. After collection:
     - Run trend_analyzer on collected data
     - Compute RSI, moving averages, momentum
     - Store TrendIndicator records
     - Log collection stats (X items collected, Y failures)
```

---

## Component Changes

### 1. `collectors/steam_market.py` (MODIFY)

**Problem**: Current implementation assumes item names work directly with Steam API. They don't.

**Solution**: Add hash name resolution using Steam's market listing API.

**Changes**:
- Add `resolve_hash_names()` method that:
  - Queries Steam's `/market/search/render` endpoint
  - Searches for each item by name
  - Caches hash name mappings to avoid repeated lookups
  - Returns dict mapping `item_name → market_hash_name`

- Update `get_item_price_history()` to:
  - Accept either item name or hash name
  - Look up hash if needed using cache/API
  - Query price history with correct hash name format

- Add caching layer (simple dict) to avoid hammering Steam API

**Implementation detail**: Hash names on Steam look like:
```
"AK-47%20%7C%20Phantom%20Disruptor-Factory%20New"
```
vs our item name:
```
"AK-47 | Phantom Disruptor"
```

---

### 2. `collectors/cs2_data_sources.py` (INTEGRATE)

**Status**: Already written, just needs to be imported and used.

**Usage**:
- On startup: `CS2ItemCatalog.get_all_items()` → load into Item table
- On startup: `CS2GameEvents.get_all_events()` → load into Event table  
- During collection: `HistoricalDataGenerator.generate_historical_prices()` → synthetic history

**No changes needed** — it's ready to use.

---

### 3. `collectors/comprehensive_loader.py` (INTEGRATE)

**Status**: Already written, just needs to be called on startup.

**Usage**:
```python
from collectors.comprehensive_loader import load_all_cs2_data

# In main.py startup:
stats = load_all_cs2_data()
logger.info(f"Loaded {stats['items_added']} items, {stats['price_records_added']} price records")
```

**What it does**:
1. Loads all items from CS2ItemCatalog
2. For each item, generates 365 days of realistic price history
3. Loads all game events
4. Handles duplicates (skips items already in DB)
5. Returns statistics dict

**No changes needed** — use as-is.

---

### 4. `collectors/pipeline.py` (MODIFY)

**Current state**: Scheduler exists, but `run_daily_collection()` is failing due to steam_market.py issues.

**Changes**:
- Ensure pipeline uses improved steam_market.py with hash name resolution
- Add error handling: if collection returns 0 items, log warning but don't crash
- Add collection stats tracking (items collected, items failed, time elapsed)
- Ensure trend analysis runs AFTER collection completes

---

### 5. `main.py` (MODIFY)

**Current state**: 
- Initializes database
- Seeds 8 sample items
- Starts pipeline

**Changes**:
- Call `comprehensive_loader.load_all_cs2_data()` after database init
  - This loads 100+ items + 365 days of history
  - Skips seeding if items already exist (idempotent)
- Keep pipeline startup as-is
- Log initialization steps clearly

**Order matters**:
```python
@app.on_event("startup")
async def startup():
    init_db()  # Create schema
    load_all_cs2_data()  # Load catalog & history
    pipeline.start()  # Start hourly collection
```

---

## Data Schema (No Changes)

Existing tables work as-is:
- `Item` - name, type, release_date, current_price
- `PriceHistory` - item_id, timestamp, price, volume, median_price
- `Event` - type, timestamp, description
- `TrendIndicator` - item_id, trend_score, signal, computed_at

The comprehensive_loader just populates these with better data.

---

## API Endpoints (No Changes)

All existing endpoints work unchanged:
- `GET /items/` - Returns all items (now 100+)
- `GET /items/{id}/price-history` - Returns both synthetic + real prices
- `GET /items/{id}/trends` - Computed from real data
- `GET /opportunities/*` - Opportunity detection on real data
- `POST /admin/collect-now` - Manually trigger collection (for testing)

---

## Success Criteria

Phase 2 is complete when:

**On Startup:**
- ✅ Logs show "Loaded 100+ items from catalog"
- ✅ Logs show "Generated X price records" (365 × 100+ = 36,500+)
- ✅ Logs show "Loaded Y game events"
- ✅ API `/items/` returns 100+ items
- ✅ API `/items/{id}/price-history` returns 365+ records per item

**During Hourly Collection:**
- ✅ Logs show successful Steam API queries (at least some items returning data)
- ✅ No crashes or unhandled exceptions
- ✅ `price_history` table receives new records every hour
- ✅ Trend indicators compute without errors
- ✅ API `/items/{id}/trends` returns up-to-date scores

**End-to-End:**
- ✅ Start backend → data loads → collection runs → new prices appear in DB → API serves them
- ✅ No manual intervention required
- ✅ Can query `/items/trending` and see items with recent price changes

---

## Timeline & Scope

**In Scope (Phase 2):**
- Fix Steam API collection (hash name resolution)
- Integrate cs2_data_sources.py catalog (100+ items)
- Integrate comprehensive_loader.py (365-day history)
- Update pipeline to use improved collector
- Verify real data is flowing

**Out of Scope (Phase 3+):**
- Frontend UI improvements
- Advanced trend analysis features
- Prediction models
- Portfolio tracking

---

## Error Handling & Resilience

**If Steam API returns no data for an item:**
- Log warning
- Skip to next item
- Continue collection loop
- Don't crash

**If comprehensive_loader finds duplicates:**
- Skip them (idempotent)
- Log count of skipped items

**If database connection fails:**
- Catch exception
- Log error
- Retry on next scheduled run
- Existing behavior (no changes needed)

**If price data looks invalid (NaN, negative, etc.):**
- Data validation in collectors/data_validation.py catches it
- Record is rejected
- Continue to next item

---

## Testing Strategy

After implementation:
1. Start backend locally
2. Check logs for successful load of 100+ items + history
3. Query API: `curl http://localhost:8000/items/` → should return 100+
4. Wait 5 minutes (or call `/admin/collect-now`)
5. Query API: `curl http://localhost:8000/items/{id}/price-history` → should have new prices with recent timestamps
6. Check `/items/{id}/trends` → should have recent trend scores

No new test files needed; existing test suite remains unchanged.

---

## Questions for Clarification

- Should we retry failed Steam API calls, or fail silently? (Recommend: fail silently, log warning)
- How many items should we target in the first collection run? All 100+, or start smaller? (Recommend: all 100+, but rate limit to 1 req/sec = ~1.5 min per run)
- Should synthetic history be generated fresh each startup, or only on first load? (Recommend: only first load, then real data accumulates)

