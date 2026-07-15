# Player Count — Historical Backfill & A/B Test

## Historical Backfill

**Problem:** `_fetch_player_counts()` looked for `price-archive/player-counts-*.parquet` files. The hourly collection pipeline (`player-count-hourly.yml` + `aggregator-update.yml`) appends new daily data to Parquet going forward, but ~10K historical rows (2011–2026) sat siloed in `csmarketapi_reference.db`.

**Fix:** `scripts/backfill_player_counts_to_parquet.py` reads the SQLite `player_counts` table, groups by day (mean, peak, min, count, last), and writes `player-counts-{year}.parquet` files into `price-archive/`, matching the schema that `append_to_parquet.py` produces.

**Result:** 5,110 unique days of player count history (2011-11-30 to 2026-07-05) now available to the forecaster.

## A/B Test: Impact on Accuracy

Walk-forward evaluation on 100 backfilled items, comparing control (no player count features) vs treatment (all 9 player count features).

| Horizon | Control (w/o) | Treatment (w/) | Delta |
|---------|:------------:|:-------------:|:-----:|
| 3d      | 63.2% (+13.2pp) | 63.6% (+13.6pp) | **+0.4pp** |
| 7d      | 63.5% (+13.5pp) | 63.5% (+13.5pp) | +0.0pp |
| 14d     | 62.5% (+12.5pp) | 66.2% (+16.2pp) | **+3.7pp** |
| 30d     | 63.2% (+13.2pp) | 70.9% (+20.9pp) | **+7.7pp** |
| **Avg** | **63.1%** | **66.1%** | **+3.0pp** |

### Interpretation

- Short horizons (3d, 7d) are essentially flat — market micro-structure dominates at these windows, player count adds little.
- 14d sees solid improvement (+3.7pp), exceeding the doc's estimate of +1-3pp.
- 30d gains +7.7pp (70.9% directional accuracy) — player count is a strong medium-term demand signal.
- Average improvement of +3.0pp across all four horizons.

### Features Added

9 derived features from daily player counts:
- `players_mean`, `players_peak`, `players_min`, `players_last`, `players_readings` — raw daily values
- `players_change_1d`, `players_change_7d` — day-over-day and week-over-week deltas
- `players_ma7` — 7-day moving average
- `players_z_score_30d` — z-score over 30-day rolling window
- `players_mean_ratio_7d` — ratio of current to 7-day MA

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/backfill_player_counts_to_parquet.py` | One-time: SQLite DB → `player-counts-*.parquet` |
| `scripts/ab_test_player_counts.py` | Reusable A/B harness (use `--max-items` to control eval size) |
| `collectors/player_counts.py` | Ongoing hourly/daily collection from Steam API |
| `.github/workflows/aggregator-update.yml` | Daily append to Parquet (via `--player-counts-csv`) |

## Remaining Items

- **Path mismatch in CI** — `forecaster.py` expects `price-archive/` at repo root; CI nests it under `archive/price-archive/`. This affects prediction runs (not training, which runs locally).
- **HTTP error handling** — `fetch_current_cs2_players` raises exceptions uncaught; `collect_and_append` only handles `None` returns.
