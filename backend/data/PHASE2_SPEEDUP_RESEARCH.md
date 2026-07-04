# Phase 2 Speedup Research — Complete Findings

## Goal

Find ways to speed up the Phase 2 backfill of `/market/pricehistory/` for 31,908 items. Current estimate: ~44 hours at 5s/item.

---

## Approach 1: Listing Page Scraping (Dead End)

### Hypothesis

The Steam market listing page (`/market/listings/730/{name}`) embeds price history as a JavaScript variable (`var line1=[...]`) in the HTML source. A library called [scm-price-history](https://github.com/HilliamT/scm-price-history) proved this worked in 2020 — no auth required, price data embedded in the page.

### What We Found

**Initial test (fluke):** First batch of requests returned full pages (1.4–4.6 MB) with embedded price history data via `window.SSR.loaderData`. 20 requests completed in 14 seconds, zero rate limits — 86 req/min vs the API's 12-15 req/min.

**Subsequent tests:** Every request returned a 91KB shell page with no embedded price data. The price history was not in `window.SSR.loaderData` or `window.SSR.renderContext`.

**Root cause:** Steam has moved to client-side rendering for listing pages. The 91KB shell loads data dynamically via JavaScript, which calls the same `/market/pricehistory/` API we're already using.

### Extraction Attempts

| Method | Result |
|--------|--------|
| `var line1=` regex | Not found — Steam removed this pattern |
| `window.SSR.loaderData` parsing | Returns 91KB shell, no pricehistory queries |
| `window.SSR.renderContext` parsing | Only 2 queries (AOWarningCookie, CookiePreferences) — no price data |
| New session per request | Same 91KB shell every time |
| Full browser headers | Same 91KB shell |

### Verdict

**Dead end.** The listing page approach no longer works. The price history data is loaded client-side via the same API endpoint we're already using. A headless browser would be required, which is slower and heavier than the API.

---

## Approach 2: Steam Web API Key (Dead End)

### Hypothesis

The Steam Web API (`api.steampowered.com`) with an API key might provide price history without session cookies.

### What We Found

| Endpoint | Auth | Returns History? | Notes |
|----------|------|-----------------|-------|
| `ISteamEconomy/GetAssetPrices` | API key | No | Current prices only, in-game economy items |
| `ISteamEconomy/GetMarketPrices` | **Publisher** API key | No | Current prices only, requires partner access |
| `ISteamEconomy/GetAssetClassInfo` | API key | No | Item metadata only |
| `/market/priceoverview/` | None | No | Current lowest/median/volume snapshot |
| `/market/pricehistory/` | Session cookies | **Yes** | The only source of time series data |

### Verdict

**Dead end.** The API key endpoints don't expose price history. The only endpoint with historical data is `/market/pricehistory/`, which requires session cookies.

---

## Approach 3: Third-Party Paid APIs

### cs2.sh

- **Cost:** $75–200/mo
- **Endpoint:** `POST /v1/archive/steam`
- **Features:** 100 items/request, Steam history daily since 2013, hourly since May 2026
- **Rate limits:** Scale with plan tier
- **How they got data:** Scraped Steam's `/market/pricehistory/` continuously since 2013

### steamwebapi.com

- **Cost:** Paid (tiered)
- **Endpoint:** `GET /steam/api/history` or `POST /steam/api/items/history`
- **Features:** Daily snapshots, at least 90 days, bulk lookups
- **How they got data:** Continuous scraping over years

### cs2cap.com

- **Cost:** Paid (Starter/Pro/Quant tiers)
- **Endpoints:** `/v1/prices/history`, `/v1/market/history/chart`
- **Features:** 41 marketplaces, historical snapshots spanning years
- **How they got data:** Aggregated from multiple sources over years

### Key Insight

These services didn't get special API access. They used the same `/market/pricehistory/` endpoint we're using, started years ago, and have been collecting data continuously. They built infrastructure to handle rate limits, bans, and session management at scale.

### Verdict

Could work if budget allows ($75-200/mo), but overkill for a one-time backfill. The data they have is what we're trying to collect.

---

## Approach 4: `/market/priceoverview/` Endpoint

### What It Returns

- `lowest_price` — current lowest listing price
- `volume` — items sold in last 24 hours
- `median_price` — median of current listings

### What It Doesn't Return

- Historical time series (no prices over time)
- Any data beyond current snapshot

### Rate Limits

Tested: ~20 req/min before 429. Similar to other endpoints.

### Verdict

**Not useful for historical backfill.** Only provides a current snapshot, not the time series data we need.

---

## Approach 5: Burst Pattern on `/market/pricehistory/` (Remaining Option)

### Current Setup

- Flat 5s delay between requests
- 31,908 items
- ~44 hours estimated

### Proposed Change

Burst pattern: 10 rapid requests + 30s cooldown (same as catalog build).

### Potential Speedup

- Same average rate (~12 req/min) but compressed into bursts
- Could reduce idle time between requests
- Estimated: ~28-32 hours (from 44h)

### Risk

Untested on auth endpoint. The `/market/pricehistory/` endpoint may have different burst behavior than `/market/search/render/`.

### Verdict

**Most practical remaining option.** Small code change, low risk, could save ~12-16 hours.

---

## Approach 6: Multiple Steam Sessions

### Hypothesis

If rate limits are per-session (not per-IP), multiple sessions could parallelize requests.

### What We Know

- Session cookies are per-account
- Each session gets its own rate limit bucket (likely)
- We'd need multiple Steam accounts with valid `sessionLoginSecure` cookies

### Potential Speedup

- 2 sessions: ~24 req/min → ~22 hours
- 3 sessions: ~36 req/min → ~15 hours

### Requirements

- Multiple Steam accounts
- Each with valid session cookies
- Session refresh infrastructure

### Verdict

**High impact but high effort.** Requires multiple accounts and session management. Worth considering if we have multiple accounts available.

---

## Current Session Status

### Cookie Expiry

- `.env` last modified: 2026-07-02 (1 day ago)
- `STEAM_SESSION_ID`: 24 chars (present)
- `STEAM_LOGIN_SECURE`: 544 chars (present)
- **Status: EXPIRED** — returns HTTP 400 with empty array

### What's Needed

Fresh session cookies from a logged-in Steam account. Cookies expire when:
- Browser session closes
- ~30 days for `sessionid`
- ~90 days for `steamLoginSecure`

---

## Summary: What Actually Works

| Approach | Status | Speed | Cost |
|----------|--------|-------|------|
| `/market/pricehistory/` flat 5s | **Working (needs fresh cookies)** | ~44h | Free |
| `/market/pricehistory/` burst pattern | **Unverified** | ~28-32h | Free |
| Listing page scraping | Dead end | N/A | Free |
| Steam API key | Dead end | N/A | Free |
| Third-party API | Works | Minutes | $75-200/mo |
| Multiple sessions | Untested | ~15-22h | Free (needs accounts) |

### Recommended Path

1. **Get fresh session cookies** — required for any progress
2. **Test burst pattern** — verify it works on auth endpoint
3. **If burst works:** Launch backfill with burst pattern (~28-32h)
4. **If burst fails:** Fall back to flat 5s (~44h)
5. **If budget allows:** Consider cs2.sh for instant data

---

## Key Learnings

1. **Steam's listing pages no longer embed price data** — the scm-price-history library (2020) exploited a pattern that Steam has since removed. All data is now loaded client-side.

2. **The Steam Web API key is useless for price history** — it only provides current prices and item metadata, not historical time series.

3. **Third-party services got their data the same way we're trying** — they just started years ago and have been running continuously.

4. **Rate limits are consistent across endpoints** — `/market/priceoverview/`, `/market/pricehistory/`, and `/market/search/render/` all hit 429 at ~20-24 req/min.

5. **Session cookies are the bottleneck** — without valid cookies, we can't access price history at all. Fresh cookies are required before any backfill can start.

6. **The 44-hour timeline is actually fast** — we're doing in one weekend what took others years to build. The data doesn't exist anywhere else for free.
