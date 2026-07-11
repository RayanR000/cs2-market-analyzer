# 2026-07-11: Added 3 new CSGOTrader price sources + exchange rates

## What changed

### 1. New daily data sources (`backend/collectors/csgotrader_aggregator.py`)

Added 3 new market endpoints + exchange rates, bringing the total from 4 to 7 sources:

| Source | Endpoint | Doppler phases | Items |
|---|---|---|---|
| `csmoney` | `prices.csgotrader.app/latest/csmoney.json` | ✅ | ~39,549 |
| `csgotrader` | `prices.csgotrader.app/latest/csgotrader.json` | ✅ | ~39,549 |
| `youpin` | `prices.csgotrader.app/latest/youpin.json` | ❌ | ~39,549 |

Previously: `steam` (~34k), `skinport` (~39k), `buff163` (~39k), `csfloat` (~39k)

### 2. Exchange rates (`backend/collectors/csgotrader_aggregator.py`)

- New endpoint: `prices.csgotrader.app/latest/exchange_rates.json`
- Fetches ~50 currency rates + BTC/ETH daily

### 3. Source labels (`backend/collectors/pipeline.py`)

New source labels added to `SOURCE_LABELS` dict:

```python
"csmoney": "aggregator_csmoney",
"csgotrader": "aggregator_csgotrader",
"youpin": "aggregator_youpin",
```

### 4. Parquet archive (`backend/scripts/append_to_parquet.py`)

- Added `--exchange-rates-csv` argument
- Writes `exchange-rates-YYYY.parquet` keyed on `(currency, day)`

### 5. GitHub Actions (`.github/workflows/aggregator-update.yml`)

- Passes `--exchange-rates-csv /tmp/exchange-rates-$(date -u +%F).csv` to append script
- Updated commit message

## Data flow

```
CSGOTrader endpoints (7) → pipeline.run_full_aggregator_collection()
  ├── /tmp/aggregator-snapshots-{date}.csv   (all sources, all items)
  ├── /tmp/aggregator-backfilled-{date}.csv  (backfilled items only)
  └── /tmp/exchange-rates-{date}.csv         (currency rates)
         ↓
  append_to_parquet.py
  ├── price-archive/prices-YYYY.parquet       (OHLCV by item_slug/day/source)
  ├── price-archive/snapshots-YYYY.parquet    (raw snapshots by item_slug/day/source)
  └── price-archive/exchange-rates-YYYY.parquet (currency rates by currency/day)
         ↓
  data-archive git branch (daily commit)
```

## No Supabase writes

Daily data is CSV → Parquet only. The Supabase price_history write path was removed in this session.
