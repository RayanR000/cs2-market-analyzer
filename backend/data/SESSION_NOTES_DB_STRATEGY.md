# Database Strategy — Session Notes (2026-07-07)

## Current State

### Price History by Source
| Source | Rows | Time Range |
|--------|------|------------|
| `market_csgo` 2024 | 435,680 | Daily |
| `market_csgo` 2025 | 1,123,818 | Daily |
| `market_csgo` 2026 | 222,385 | Daily |
| `steam_historical` 2013-2021 | 564,010 | Weekly |
| `aggregator_sync` 2026 | 466,623 | Live |
| **Total** | **2,812,516** | |

### Database Size
- `price_history` table: 568 MB
  - Table data (heap): ~232 MB
  - Index `uq_price_history_item_timestamp_source` (item_id, timestamp, source): 256 MB
  - Index `price_history_pkey` (id): 80 MB
- Other tables: ~10 MB
- Total DB: **589 MB**
- Supabase Free limit: **500 MB** — 89 MB over

### Phases Completed
| Phase | Task | Status |
|-------|------|--------|
| 1a | Delete stale price_history rows (553K deleted) | ✅ |
| 1b | Deduplicate items (5,103 slug items removed) | ✅ |
| 1c | Enrich items with classid/type (18K enriched) | ✅ |
| 2a | Import MARKETCSGO daily rows (1.78M) | ✅ |
| 2b | Import steam_historical weekly rows (564K) | ✅ |
| 3 | Analysis pipelines (daily_analysis, forecasts, etc.) | ❌ Skipped — tables don't exist yet |

### Analysis Tables Missing
These tables exist in the ORM (`database.py`) but were never created in Supabase via migrations:
- `daily_analysis` (migration `0001_initial_schema.py`)
- `item_forecasts` (migration `0003_add_price_history_unique_and_item_forecasts.py`)
- `trend_indicators`
- `event_impacts`, `event_correlations`, `event_patterns`
- `price_history_unique_constraint` (migration `0003`)

Only migrations `0001_initial_schema` through `0004_add_item_metadata_images` exist as files.
Applied in Supabase: only up to `0004`. The `daily_analysis` table wasn't created despite
`0001` including it — likely the migration ran against the local SQLite DB, not Supabase.

---

## Storage Growth Projections

| Growth Source | Per Month | Per Year |
|--------------|-----------|----------|
| 4K new items × ~227 weekly historical rows | ~908K rows | ~10.9M rows |
| Daily price updates for ~20K items | ~620K rows | ~7.4M rows |
| Analysis tables (daily_analysis, forecasts, etc.) | ~620K rows | ~7.4M rows |
| **Total** | **~2.1M rows** | **~25.7M rows** |
| **Storage (est. at 200 bytes/row)** | **~400 MB** | **~4.8 GB** |

The Free tier (500 MB) cannot sustain this. Even after aggressive pruning, we'd need 2-3 GB+ within a year.

---

## Approaches Considered

### 1. Supabase Pro ($25/mo, 8 GB)
- **Pros**: Zero code changes, same performance, includes auth/storage/realtime/edge functions
- **Cons**: $300/year

### 2. Hybrid: Supabase Auth + Aiven Free (5 GB)
- **Pros**: Free (both), 5 GB for data, real PostgreSQL
- **Cons**: Two connection strings, no cross-DB joins, need to migrate data

### 3. Hybrid: Supabase Auth + CockroachDB Serverless (10 GB free)
- **Pros**: 10 GB storage, PostgreSQL-compatible
- **Cons**: 50M RU/month limit may be hit by daily analysis queries. Scale-to-zero means cold starts (~570ms). Not real PostgreSQL — some features differ (no SERIAL, different system views). RU pricing can spike unpredictably.

### 4. Neon (0.5 GB × 100 projects)
- **Pros**: 100 projects, branching, scale-to-zero (auto-wake in ~570ms)
- **Cons**: Only 0.5 GB per project. Splitting data is impractical (no cross-project queries). 100 CU-hours/month for compute.

### 5. Multiple Supabase Free tiers (500 MB each)
- **Pros**: Free
- **Cons**: No cross-DB queries, complex routing in code, each DB still capped at 500 MB. 2 active project limit.

### 6. Aiven Free (5 GB, always-on, no RU metering)
- **Pros**: 5 GB real PostgreSQL, always-on (no cold starts), unlimited queries
- **Cons**: 1 GB RAM, 1 CPU. Single node only.

---

## Aiven Free Performance Assessment

### Query Patterns by Script

#### `analyze_trends.py` — Moderate
- 1 × `SELECT` all price data for 90 days (~1.3M rows) with index scan
- 2 × COUNT queries for update frequency
- In-memory Python/numpy per-item (app-side, not DB)
- 1 × bulk INSERT 14K+ rows
- **Verdict**: Works. Single scan is slow on 1 CPU but fine for nightly run.

#### `forecast_prices.py` — Heavy read, heavy app-side compute
- `fetch_price_history(365)`: loads 3M+ rows into pandas DataFrame (500+ MB app RAM)
- `train()`: builds feature matrix, trains LightGBM (CPU-bound, runs app-side)
- `predict()`: pulls 90 days, feeds through models
- **Verdict**: DB handles single scan. App-side memory is the concern — 3M+ row DataFrame needs 500+ MB RAM.

#### `long_term_trend_analyzer.py` — The problem (N+1)
- 14K+ individual queries (one per item) for age check + price history
- Each query returns 1-3 years of price data
- At ~10ms/query = 140s overhead alone
- **Verdict**: Unacceptable on 1 CPU. Needs refactoring to bulk query (like analyze_trends does).

### Estimated Runtime Comparison

| Operation | Supabase (shared 2-4 vCPU) | Aiven Free (1 vCPU) |
|-----------|---------------------------|-------------------|
| analyze_trends SELECT (1.3M rows) | 2-5s | 10-20s |
| forecast training query (3M rows) | 5-10s | 30-60s |
| long_term_trend N+1 loop | 30-60s | 3-5 min |
| API lookups (single item) | <10ms | <10ms |
| Daily price INSERT (7K rows) | <1s | 2-5s |

---

## Recommendation

**Supabase Pro ($25/mo, 8 GB)** is the cleanest path:

- Zero migration work
- Zero code changes
- Zero operational complexity
- 8 GB covers 2-3 years at current growth rate
- Same performance as now
- Auth/storage/realtime stay wired up

**Aiven Free** is viable if avoiding $300/year matters more than:
- Refactoring `long_term_trend_analyzer.py` (fix N+1 → bulk query)
- Accepting 2-5x slower nightly analysis
- Managing two databases (or migrating auth away from Supabase)
- No file storage, no realtime, no edge functions

---

## Key Decisions Made

1. **Skip Phase 3 analysis pipelines** for now — the analysis tables (`daily_analysis`, `trend_indicators`, etc.) don't exist. They need migration runs against Supabase first.
2. **Do not downsample price_history to save space** — the tiered retention would ruin daily/weekly granularity needed for accurate short-term analysis.
3. **Do not delete entire years of data** — user needs full time coverage.
4. **Reverted chunked-insert fix** in `analyze_trends.py` — the fix was applied but analysis isn't being run yet, so it doesn't matter.

## Remaining Work (when ready)

1. Run Alembic migrations against Supabase to create analysis tables
2. Run analyze_trends.py → daily_analysis
3. Run forecast_prices.py → item_forecasts
4. Run event_analyzer.py → event_impacts, event_correlations, event_patterns
5. Run long_term_trend_analyzer.py → trend_indicators
6. Resolve database hosting (buy-up or migrate)
