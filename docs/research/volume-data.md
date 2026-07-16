# Volume Data Source Research

**Last updated: 2026-07-16**

## Current State

The Parquet archive has **404,563 price rows with non-zero volume** from the `STEAMCOMMUNITY` source (Jan–Mar 2026 historical Steam backfill). **July 2026 has all zeros** — the daily aggregator (`CSGOTraderAggregator`) only collects prices, **not** volume.

| Time Period | Data | Status |
|---|---|---|
| Jan–Mar 2026 | 404,563 rows with non-zero STEAMCOMMUNITY volume | ✅ Historical |
| Apr–Jun 2026 | No volume data (gap) | ❌ Missing |
| Jul 2026 onward | All aggregator sources = volume=0 | ❌ Zeros |
| CSMarketAPI backfill DB | `csmarketapi.db` — not present on disk | ❌ Missing |

The CSMarketAPI backfill database (`runtime/csmarketapi.db`) that would have OHLCV sales history for 4,940 items across 7 markets does not exist on the current machine (it was in `.gitignore` and likely lived on a different runner or was cleaned up).

The supply scraper collects `sell_listings` (active listings) but this is **not** trade volume — it's supply-side only.

The forecaster already has volume features (`volume_lag_1d`, `volume_mean_7d`, `volume_zscore_30d`, etc.), but they receive zero for recent days, degrading 7d and 14d window features.

## Requirements

- No Steam cookie/session management
- Bulk calling preferred but not required
- Free tier preferred
- Daily volume updates to keep features fresh
- Must cover backfilled items (at minimum the tracked ~5.5K items, ideally all Steam items)

## Sources Evaluated

### CSGOTrader (already used)
- Endpoints: `prices.csgotrader.app/latest/steam.json` etc.
- Data: `last_24h`, `last_7d`, `last_30d`, `last_90h` — **prices only, no volume**
- Free, bulk (all items in one endpoint)
- Already integrated; cannot add volume from this source

### CS2Cap
- **Free** ($0/mo): `GET /prices/candles` — OHLCV with `v` (estimated trade volume) and `q` (active listings). 1K req/month, 20 req/min. Per-item.
- **Starter** ($19/mo): `POST /prices/batch` — listing count (`quantity`) for 100 items/req. 50K req/month.
- **Pro** ($79/mo): `GET /market/items` — ALL items in one call, returns `sales_1d/7d/30d`, `total_volume_24h`, `supply`, `liquidity`.
- No cookies needed. API key auth.

### CSMarketAPI (csmarketapi.com — already used for backfill)
- **Free** ($0/mo): 1K req/month. `GET /v1/sales/latest/aggregate` returns `volume` (sales count). Per-item (requires `market_hash_name`).
- **Pro** ($9.99/mo): 1M req/month.
- 5 keys available (all currently exhausted this month at 1,000/1,000 each)
- Not bulk — per-item, so even 5 keys × 950 safe req = ~158 items/day

### Skinstrack
- **Free**: 50 req/month — too few for production.
- **Paid** ($24.99/mo): Volume data across 34+ marketplaces.

### SteamWebAPI
- **Item Small** (€15/mo ≈ $16.50): `GET /steam/api/items` — **ALL items in one call**. Returns `sold24h`, `sold7d`, `sold30d`, `offervolume`, `buyordervolume`. Best value option for paid.
- Free plan cannot access the bulk items endpoint.

### cs2.sh
- **Developer** ($75/mo): Prices only.
- **Scale** ($200/mo): Includes `/v1/archive/csfloat` (daily completed-sale volume since 2022). Too expensive.

### Steam Community Market (priceoverview endpoint — undocumented)
- `GET https://steamcommunity.com/market/priceoverview/?appid=730&market_hash_name=...`
- Returns `volume` (items sold in last 24h), `lowest_price`, `median_price`
- **No auth required** (no cookies, no API key)
- **Per-item** (not bulk), rate-limited to ~10-15 req/min
- Risk of IP ban under sustained load
- At 10 req/min: ~600 items/hour, ~9 hours for 5.5K items
- Free but too slow for daily full-catalog coverage

### Steam Community Market (pricehistory endpoint)
- Returns per-item price history with volume.
- **Requires valid Steam session cookie** — user does not want to manage cookies.

### CSFloat (direct API)
- Public listing endpoint returns 403 without API key.
- API requires key for read access; not a free bulk option.

### CSMarketCap API (csmarketcap.com — distinct from CSMarketAPI)
- **Standard** ($9.99/mo): 10K requests/month, 30 req/min
- **Pro** ($49.99/mo): 50K requests/month, 60 req/min
- `POST /api/v2/rest/get-steam-analytics` — **returns ALL items in one call**
- Returns per-item: `sales { last_24h, last_7d, last_30d, last_90d, avg_daily_volume }`, plus listing and buy order stats
- JWT token auth (expires 2h, auto-refreshable via SDK)
- Website features free; API requires paid subscription
- 1 call/day = 30/month — well within 10K quota
- Cheapest paid option discovered

### SkinWise
- Free, no auth
- `GET /api/v1/price/{slug}` — per-item
- Only prices, **no volume data**

### CSPriceAPI
- Free tier with sensible rate limits (unclear exact limits)
- Per-item pricing, unknown if volume included
- Not thoroughly evaluated

### PriceEmpire (pricempire.com)
- **Free testing tier** (~100 test calls)
- **Hobby** ($30/mo): 1K credits/month, 20 req/min
- **Developer** ($100/mo): 5K credits/month, 100 req/min
- `get_skin_price_history` returns `[timestamp, price, volume]` tuples
- Per-item (1 credit = 1 API call)
- Free tier too limited; paid tiers expensive
- Has unofficial Parse API wrapper (free 100 credits/mo)

### cs2.sh (re-evaluated)
- Free: **2-day developer key only** (not viable for ongoing use)
- Developer ($75/mo): unlimited requests, 10 req/s
- `GET /v1/prices/latest` — truly bulk (all items in 1 call)
- Returns `ask_volume`/`bid_volume` (listing counts, **not trade volume**)
- For actual trade volume: `POST /v1/archive/steam` (daily purchase vol since 2013) — Scale plan ($200/mo)
- Does not provide daily trade volume data on the Developer plan

## Verdict

**No free source provides bulk trade volume data.** Every option that has reliable trade volume charges for API access.

| Source | Cost | Bulk? | Trade Volume Fields | Daily Coverage for 5.5K items |
|--------|:----:|:-----:|:-------------------|:------------------------------|
| Steam `priceoverview` | Free | ❌ per-item | 24h sales count | ~600 items/hr (too slow) |
| CSMarketCap API | **$9.99/mo** | ✅ 1 call | `last_24h/7d/30d/90d` | ✅ All items, 1 call |
| SteamWebAPI Item Small | €15/mo | ✅ 1 call | `sold24h/7d/30d/90d` | ✅ All items, 1 call |
| CSMarketAPI (your keys) | Free | ❌ per-item | sales_history.volume | ~158 items/day (5 keys) |
| CS2Cap Pro | $79/mo | ✅ batch 1K | `sales_1d/7d/30d` | ✅ 1 batch call |
| Pricempire Standard | $99.90/mo | ❌ per-item | trade count metas | ❌ free tier too small |
| cs2.sh Developer | $75/mo | ✅ bulk | ask_volume (listings, not trade vol) | ❌ no trade vol on dev plan |

## Recommendation

**CSMarketCap API at $9.99/mo** is the cheapest option discovered:
- One API call per day returns trade volume (`last_24h/7d/30d/90d`) for every item
- Also returns listing stats and buy order data at no extra cost
- 10K requests/month = 1 call/day for 333 days = essentially unlimited for this use case
- Has an official TypeScript SDK with auto token refresh

If even $9.99/mo is a blocker, the fallback is to accept the volume gap. As the previous research noted, the volume zeros mainly affect 7d/14d window features; 30d/60d features still have signal from Jan–Mar data, and LightGBM handles NaN/zeros gracefully.
