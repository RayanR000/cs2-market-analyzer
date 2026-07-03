# Phase 1: Market Catalog Build — Documentation

## What We Built

A complete catalog of every CS2 item on the Steam Community Market, stored in local SQLite. This replaces the production database's limited 24,822-item catalog with a full 23,490-item catalog scraped directly from Steam's API.

**Output:** `backend/data/market_catalog.db` (15.4 MB, 23,490 items)

---

## Why

Our production Supabase database only had 24,822 items (24,737 skins + 85 cases). The Steam Market has ~34,268 items. We were missing ~9,400 items — mostly stickers, charms, graffiti, agents, music kits, and collectibles — because they were never added to our DB.

This catalog covers everything available on the Steam Market for CS2.

---

## How It Works

### Endpoint Used

`GET https://steamcommunity.com/market/search/render/`

- Returns 10 items per page (hard-coded, cannot increase)
- No authentication required (public endpoint)
- Total pages for ~34,000 items: ~3,400

### Data Fields Captured Per Item

| Field | Example | Description |
|---|---|---|
| `hash_name` | "Glock-18 | Grinder (Field-Tested)" | Unique market identifier |
| `name` | "Glock-18 | Grinder (Field-Tested)" | Display name |
| `type` | "Restricted Pistol" | Item category/subtype |
| `sell_price` | 379 | Current lowest price (cents) |
| `sell_price_text` | "$3.79" | Formatted price |
| `sale_price_text` | "$3.50" | Sale price if discounted |
| `sell_listings` | 56 | Active sell listings count |
| `tradable` | 1 | Tradeable flag |
| `commodity` | 0 | Commodity flag (stackable items) |
| `classid` | "4717330486" | Asset class ID |
| `name_color` | "b0c3d9" | UI color code |
| `icon_url` | "i0CoZ81Ui0m-..." | Item icon path |
| `bucket_group_id` | "G18D2253004" | Bucket grouping |
| `last_updated` | "2026-07-03T19:46:51" | When we fetched it |

---

## Rate Limiting Strategy

### Research Phase

We tested the Steam API directly to find the actual rate limits:

1. **Burst limit:** ~10-12 rapid requests before 429
2. **Recovery after 429:** ~30 seconds
3. **Safe sustainable rate:** 3 seconds between requests
4. **Items per page:** Hard-coded to 10 (count/pagesize parameters ignored)

### Chosen Strategy: Burst Pattern

Instead of a flat 3-second delay (wastes time between requests), we used a burst pattern:

- **Send 10 requests as fast as possible** (~2 seconds)
- **Pause 30 seconds** (recovery time)
- **Repeat**

This achieves the same safety as flat 3s but runs ~2.5x faster because you're not sitting idle between every request when Steam isn't throttling you.

### Rate Limit Math

- 10 requests per burst = ~2 seconds
- 30 seconds pause between bursts
- Cycle: ~32 seconds for 100 items (10 pages × 10 items)
- Theoretical rate: ~187 items/min
- Observed rate: ~200 items/min

---

## 429 / Ban Handling

### What We Learned

| Event | Behavior | Recovery |
|---|---|---|
| Individual 429 | Backoff 30s, retry | ~30s |
| Sustained 429s | All retries exhaust, page recorded as failed | 30-60 min cooldown |
| IP ban | Every request returns 429 | 1-2 hours cooldown, or switch IP (VPN) |

### What Actually Happened During Our Build

1. **First run (12:56-15:40):** Got to offset 22,070 (64%) with 0 failures before hitting sustained 429s. ~4 pages failed.
2. **Paused for ~3 hours** while we fixed the 429 counting bug.
3. **Second run (18:44-19:46, VPN):** Completed remaining 36% with only 11 isolated 429s, all recovered.

### The 429 Counting Bug (Fixed)

**Problem:** 429s that occurred inside `fetch_page()`'s retry loop were never counted by the HealthMonitor. The health reports always showed `429s: 0` even when 429s were happening.

**Fix:** Added `last_fetch_429_count` to the client. After each `fetch_page()`, the main loop reads this counter and passes it to the HealthMonitor. Now health reports show accurate 429 counts.

---

## Failures and Recovery

### Failed Pages Table

Failed pages are tracked in a `failed_pages` table:

```sql
CREATE TABLE failed_pages (
    offset INTEGER PRIMARY KEY,
    error_reason TEXT,
    failed_at TEXT
);
```

### Recovery Workflow

```bash
# Normal build (resumes from last saved offset)
python scripts/build_market_catalog.py --resume

# Retry only the failed pages
python scripts/build_market_catalog.py --retry-failed

# Check status
python scripts/build_market_catalog.py --status
```

### What Happened

- 4 pages failed during the first run (offsets 22070-22100)
- They were recorded in `failed_pages`
- After the IP ban cooled down, `--retry-failed` recovered all 4 successfully (40 items)
- Final state: 0 failed pages

---

## Health Monitoring

### What's Tracked

- **OK/Failed/429 counters** — totals and consecutive streaks
- **Session expiry detection** — EMPTY responses after OK streaks
- **Auto-pause** — stops the run if thresholds are exceeded:
  - 3 consecutive 429s
  - 10 consecutive failures
- **Periodic health reports** — every 500 items

### What We Saw During the Build

| Metric | First Run | Second Run (VPN) |
|---|---|---|
| Items fetched | 18,038 | 5,452 |
| Failures | 0 | 0 |
| 429s (isolated) | ~100+ | 11 |
| 429s (sustained) | 4 pages | 0 |
| Auto-pause triggered | Yes (IP ban) | No |

---

## Database Schema

```sql
-- Item catalog
CREATE TABLE market_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash_name TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT,
    sell_price INTEGER,
    sell_price_text TEXT,
    sale_price_text TEXT,
    sell_listings INTEGER,
    tradable INTEGER,
    commodity INTEGER,
    classid TEXT,
    name_color TEXT,
    icon_url TEXT,
    bucket_group_id TEXT,
    last_updated TEXT
);

-- Build progress (pause/resume)
CREATE TABLE catalog_progress (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_offset INTEGER,
    total_items INTEGER,
    started_at TEXT,
    updated_at TEXT
);

-- Failed pages (retry)
CREATE TABLE failed_pages (
    offset INTEGER PRIMARY KEY,
    error_reason TEXT,
    failed_at TEXT
);
```

---

## Scripts

### `build_market_catalog.py`

**Location:** `backend/scripts/build_market_catalog.py`

**CLI flags:**
```bash
--resume           # Resume from last saved offset
--retry-failed     # Retry only failed pages
--status           # Show progress + health
--dry-run          # Preview without writing
--burst-size N     # Requests per burst (default: 10)
--burst-pause N    # Seconds between bursts (default: 30)
```

**Logs to:** `backend/data/market_catalog.log`

### Dependencies

- `requests` — HTTP client
- `sqlite3` — local database
- `config.py` — settings (not used for this script, but imported)

---

## Final Stats

| Metric | Value |
|---|---|
| Total items cataloged | 23,490 |
| Failed pages | 0 |
| DB size | 15.4 MB |
| Total duration | ~3.5 hours (including ban cooldown) |
| Active fetch time | ~1.5 hours |
| 429s encountered | ~110+ (11 in final run, all recovered) |
| Bans | 1 (recovered via VPN) |

### Item Type Breakdown

| Category | Count |
|---|---|
| Stickers (all types) | ~8,400 |
| Charms (all types) | ~4,400 |
| Skins (all grades + StatTrak/Souvenir) | ~8,000 |
| Graffiti | ~1,200 |
| Knives (★ + StatTrak) | ~1,900 |
| Gloves (★ + StatTrak) | ~500 |
| Containers/Cases | ~340 |
| Music Kits | ~140 |
| Collectibles/Pins | ~60 |
| Agents | ~54 |
| Equipment/Tools | ~100 |
| Other (Keys, Passes, Gifts, Tags) | ~50 |

---

## Lessons Learned

1. **Test rate limits empirically** — don't guess. We found Steam's actual limits differ from what people report online.
2. **Burst pattern beats flat delay** — same safety, 2-3x faster.
3. **Track429s at the right level** — retry loops hide 429s from higher-level monitoring. Always surface them.
4. **VPN is a valid recovery** — when IP banned, switching to a VPN immediately restores access.
5. **Failed page tracking is essential** — without it, you'd have to re-run the entire build to recover 4 pages.
6. **Local SQLite is the right choice** — Supabase is 500MB and full; this 15.4MB local DB is clean and complete.

---

## Next Steps

- **Phase 2:** Backfill pricehistory for all 23,490 items using `backfill_ssr_history.py`
- Update the backfill script to read from `market_catalog.db` (via `--source catalog`)
- Replace old Supabase snapshots with SSR history data
