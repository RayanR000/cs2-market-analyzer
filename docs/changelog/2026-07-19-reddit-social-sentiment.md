# Reddit social sentiment collector

**Date:** 2026-07-19

**Files changed:**
- `collectors/social_sentiment.py` — new collector: fetches Reddit posts, regex-matches skin names, scores with VADER, upserts to DB
- `database.py` — added `SocialMention` model (composite PK: item_id, source, post_id)
- `migrations/versions/0018_add_social_mentions.py` — new migration
- `scripts/run_task.py` — added `reddit_social` task
- `models/forecaster.py` — added `_fetch_social_mentions()` + `_add_social_features()`, wired into `engineer_features()`
- `requirements.txt` — added `vaderSentiment>=3.3.2`
- `.github/workflows/reddit-sentiment.yml` — new workflow

---

## What

6-hourly Reddit mention tracker for CS2 skin names. Monitors 3 subreddits with per-subreddit post limits, scores sentiment via VADER, and feeds 5 new features into the daily forecast pipeline.

## Subreddits monitored

| Subreddit | Focus | Posts/run |
|-----------|-------|-----------|
| `GlobalOffensiveTrade` | Active trading, price talk | 150 |
| `csgomarketforum` | Market discussion, speculation | 50 |
| `CSGOSkinInvesting` | Investment-oriented | 25 |
| ~~`GlobalOffensive`~~ | ~~General CS2~~ — removed (too noisy) | — |

## Collection flow

1. Fetch posts from each subreddit via `old.reddit.com/r/{sub}/new/` HTML (150 / 50 / 25 posts per sub)
2. Build compiled regex from all ~2000 item names (sorted by descending length for specificity)
3. Match post titles against regex → collect matched item IDs
4. Run VADER polarity scoring on matched post titles
5. Upsert to `social_mentions` with `ON CONFLICT DO NOTHING`

## New forecaster features

| Feature | Description |
|---------|-------------|
| `social_mentions_1d` | Reddit mention count in last 24h |
| `social_mentions_7d` | Reddit mention count in last 7 days |
| `social_mention_velocity` | `mentions_1d / max(mentions_7d, 1)` (acceleration signal) |
| `social_sentiment_7d` | Rolling 7d avg VADER compound score |
| `social_score_7d` | Rolling 7d avg Reddit post score (upvotes) |

## Schedule

`0 5,11,17,23 * * *` — 6-hourly. The 23:00 UTC run aligns with the aggregator so social features are fresh for that night's forecast chain.

## Design rationale

- **VADER over HuggingFace:** Trade listing titles are formulaic (`[H] Item X [W] Price Y`), not emotional. The real signal is mention velocity (how many people are talking about a skin), not nuanced sentiment. VADER is zero-dependency, instant, and correctly scores formulaic titles as neutral (~0.00).
- **HTML over .json:** Reddit killed its public `.json` API in May 2026 (all endpoints return 403). `old.reddit.com` HTML rendering still works and is parseable with BeautifulSoup.
- **6-hourly over daily:** Matches the player-count cadence pattern and catches intraday hype events without over-fetching. Sub-60 req/min from a single IP stays well under rate limits.
