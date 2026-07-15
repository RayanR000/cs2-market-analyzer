# Player Count — Bug Fix & Test Coverage

## Bug Fix

**File:** `backend/collectors/player_counts.py:11`

Added missing `import sys`. The `__main__` block called `sys.exit(1)` when the Steam API returned no data, but `sys` was never imported — causing a `NameError` that crashed the hourly CI workflow (`player-count-hourly.yml`).

## Test Coverage Added

### `tests/test_player_counts.py` (17 tests)

| Class | Tests |
|---|---|
| `TestFetchCurrentCS2Players` | success, missing key, HTTP error, int cast, request exception |
| `TestCollectAndAppend` | single/multiple appends, fetch failure, header-once |
| `TestReadDailyCSV` | missing file, reads back rows |
| `TestSummarizeDailyCSV` | no data, correct stats, key presence |
| `TestMainBlock` | `sys.exit(1)` on failure, no exit on success |
| `TestGetDailyCSVPath` | path format |

### `tests/test_forecaster.py` — `TestPlayerCountFeatures` (5 tests)

Empty Parquet fallback, all feature columns added, zero-fill when empty, 1d/7d change computation, MA7/z-score/ratio availability.

## Remaining Gaps (not fixed)

1. **Historical backfill siloed** — `csmarketapi_backfill.py` stores 10k+ rows in `csmarketapi_reference.db` but the forecaster only reads from Parquet. No conversion path exists.
2. **Path mismatch** — `forecaster.py` expects `price-archive/` at repo root; CI nests it under `archive/price-archive/`.
3. **No error handling for HTTP errors in `fetch_current_cs2_players`** — exceptions propagate up uncaught. `collect_and_append` only handles `None` returns, not raised exceptions.
4. **Outdated docs** — `2026-07-14-remaining-accuracy-improvements.md` claims player count features are "never wired" but `_add_player_count_features` is called in both `build_training_data` and `predict_future`.
