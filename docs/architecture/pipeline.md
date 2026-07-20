# CSGOTrader Multi-Market Pipeline

## What Was Done

### Data Sources (from `prices.csgotrader.app/latest/`)
| Endpoint   | Source Label (DB/Parquet)    | Fields Used                              |
|------------|------------------------------|------------------------------------------|
| steam.json | `aggregator_sync`            | `last_24h`, `last_7d`, `last_30d`, `last_90d` |
| skinport.json | `aggregator_skinport`     | `starting_at`                            |
| buff163.json  | `aggregator_buff163`      | `starting_at.price`                      |
| buff163.json  | `aggregator_buff163_buy`  | `highest_order.price`                    |
| csfloat.json  | `aggregator_csfloat`      | `price`                                  |
| csmoney.json  | `aggregator_csmoney`      | `price`                                  |
| csgotrader.json | `aggregator_csgotrader` | `price`                                  |
| youpin.json    | `aggregator_youpin`      | `price`                                  |

### Files Changed
- **`backend/collectors/csgotrader_aggregator.py`** — Fetches all 4 endpoints in one session; returns `Dict[str, SourceData]` per item with `{source: (price, volume, timestamp)}`. Logs failed endpoint counts, match rates, and warns on low match rate.
- **`backend/collectors/pipeline.py`** — Maps sources to DB labels; writes all sources to snapshot CSV for Parquet archive (no prices written to Supabase — only `CollectionRun` records). Logs `"ZERO items collected"` error when nothing is returned.
- **`backend/scripts/append_to_parquet.py`** — Accepts `--snapshot-csv` for all-source flat data (new) and `--backfilled-csv` (legacy). Writes `prices-YYYY.parquet` (OHLCV) and `snapshots-YYYY.parquet` (all sources). Warns on missing/empty CSV files.
- **`backend/scripts/run_task.py`** — Exits with code 1 when `items_collected == 0`, triggering GitHub failure notification.
- **`.github/workflows/aggregator-update.yml`** — Added `--snapshot-csv` flag to the `append_to_parquet.py` invocation. Failure notifications already exist for scheduled runs.

### Storage Strategy
- **Supabase**: Only `CollectionRun` tracking records are written — the pipeline currently writes all price data to CSV → Parquet only. (Price data in Supabase is stale.)
- **Parquet** (`archive/price-archive/`):
  - `prices-{YYYY}.parquet` — Steam daily OHLCV (from `aggregator_sync` rows in snapshot CSV)
  - `snapshots-{YYYY}.parquet` — Flat rows of all sources (`item_slug`, `day`, `source`, `price`, `volume`)

### Coverage Per Run
- ~18K `aggregator_sync` rows + ~30K multi-market rows = ~48K total/day (~1.2 MB/day) — all written to CSV/Parquet

### Test Coverage
- ~170 tests passing — 11 unit tests for aggregator fuzzy matching, integration tests for pipeline + DB flow, plus fallback recovery and full workflow tests.
