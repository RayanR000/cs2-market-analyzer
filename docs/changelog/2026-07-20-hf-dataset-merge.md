# Hugging Face CS2 dataset merge — fills 17 gap days, +32K items

**Date:** 2026-07-20

**Files changed:**
- `backend/scripts/merge_hf_dataset.py` — new script: download HF Parquet, map to archive schema, append
- `backend/requirements.txt` — added `huggingface_hub>=0.24.0`
- `price-archive/prices-2026.parquet` — 2.09M OHLCV rows appended (was 2.02M, now 4.11M)
- `price-archive/snapshots-2026.parquet` — 2.09M snapshot rows appended (was 1.61M, now 3.70M)
- `docs/references/data-sources.md` — added HF dataset source entry + merge details
- `docs/architecture/data.md` — updated file sizes, data flow, storage breakdown

---

## What

Merged the [HF CS2 Historical Item Price Dataset](https://huggingface.co/datasets/idomanteu/cs2-historical-item-prices-hourly-march-april-2026) (CC BY 4.0) into the Parquet archive to fill the Mar 30 – Apr 15 2026 data gap and expand item coverage for Mar 22–29.

### Source
- **Provided by:** cs2.sh (published as CC BY 4.0 on Hugging Face)
- **Format:** Parquet (zstd), 668 MB, 69.2M hourly rows
- **Markets:** BUFF (`aggregator_buff163`), CSFloat (`aggregator_csfloat`), YouPin (`aggregator_youpin`)
- **Items:** 32,848 unique `market_hash_name`
- **Period:** 2026-03-22 → 2026-04-15 (25 days)
- **Schema:** OHLC ask/bid, ask/bid volume, sample_count — hourly

### Coverage impact

| Date range | Before | After |
|------------|--------|-------|
| Mar 22 (overlap) | 2,724 items, 1 source | **32,437 items, 4 sources** |
| Mar 30 – Apr 15 (gap) | **zero data** | **~32,500 items/day, 3 sources** |
| Jul 11+ | 41,125 items, 11 sources | unchanged |

The remaining gap (Apr 16 – Jul 8, 84 days) is still unfilled.

### Merge strategy

The script maps HF columns directly to the archive schema:

| HF column | Archive column |
|-----------|---------------|
| `market_hash_name` | `item_slug` (direct, same format) |
| `bucket` (hourly) | `day` (aggregated to daily) |
| `close_ask` | `mean_price` / `median_price` (daily mean/median) |
| `high_ask` | `max_price` (daily max) |
| `low_ask` | `min_price` (daily min) |
| `ask_volume` | `volume` (daily sum) |
| `source` (`buff`/`csfloat`/`youpin`) | `aggregator_buff163` / `aggregator_csfloat` / `aggregator_youpin` |

Uses the same `_append_parquet` logic and dedup keys as `append_to_parquet.py` (`[item_slug, day, source]`).

### File sizes

| File | Before | After |
|------|--------|-------|
| `prices-2026.parquet` | 19 MB | 44.6 MB |
| `snapshots-2026.parquet` | 7.6 MB | 21.2 MB |

### Why this dataset existed

cs2.sh (paid CS2 price API) released this as a free CC BY 4.0 dataset for publicity — it's a 25-day sample of their hourly archive. No other free bulk historical dataset covering the gap period exists as of July 2026.

### Remaining gap

Sources evaluated for **Apr 16 – Jul 8** (84 days):
- CS2Cap free tier (free signup, historical snapshots + OHLCV, 40+ markets) — most promising
- CSPriceAPI (same cs2.sh backend as HF dataset, free tier, hourly history) — same column mapping
- CSMarketAPI free tier (already integrated, 6×1K req/mo) — key exhaustion
- No free no-auth bulk Parquet source covers this window
