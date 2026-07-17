# Data Quality Audit & Training Data Fixes

**Date:** 2026-07-17

**Files changed:**
- `models/forecaster.py` — `_filter_dead_items()`, `_flag_corrupt_items()`, `_compute_sample_weights()`, target winsorization in `prepare_targets()`, 2026 distribution-shift guard in `build_training_data()`
- `tests/test_forecaster.py` — updated winsorization expectation (700→500)

---

## Background

During a retraining session, the entire training dataset was audited for data quality issues using DuckDB queries across all 13 years of Parquet archive data (~9.8M rows). The audit found three critical issues and two moderate issues in the STEAMCOMMUNITY backfill data.

---

## 1 — Audit Findings

### 🔴 Critical: 41.5% of Training Rows Are Dead Items at Steam Floor Price

**Query:** `prices-*.parquet WHERE source = 'STEAMCOMMUNITY' AND mean_price <= 0.04`

- **2,936 of 5,542 items (53%)** are at the Steam minimum price of $0.03-0.04
- **4,081,983 rows (41.5%)** are these floor-price items
- They have never moved >5% in their entire lifetime
- These items add zero predictive signal — the model learns "predict no change" for nearly half its training data

**Root cause:** The CSMarketAPI backfill includes all items regardless of trading activity. Items that nobody trades sit at the Steam floor forever but still occupy rows in the training set.

### 🔴 Critical: 11,044 Extreme Price Jumps >1000% (Data Corruption)

**Query:** Daily `pct_change` per item, filtered for >1000% jumps

- **84.4% (9,321 of 11,044)** extreme jumps revert to the original price the **next day** — definitive API corruption
- **905 items** affected, 151 items with **10+ corrupt events**
- Worst offender: `Souvenir Sawed-Off | Parched (Battle-Scarred)` — 175 corrupt jumps
- These jumps cluster on specific dates (up to 21 on a single day), suggesting API batch failures
- Most jumps originate from the $0.03 floor (6,385 jumps, avg 8,912%), followed by $0.05-1.00 items (4,617 jumps, avg 4,794%)

**Root cause:** The CSMarketAPI returns corrupt price spikes that are not real market events. The cause is unknown (API bug, Steam rate limiting, or data pipeline error) but the signature is unmistakable: price jumps 100x-8,000x and returns to normal the next day.

### 🟡 Moderate: 2026 Backfill Incomplete

**Query:** Max date per year for STEAMCOMMUNITY source

- 2026 data ends **March 29** — only 88 days of the year
- Aggregator (live prediction data) starts **July 9**
- **3-month gap** means the model trains on Jan-Mar prices but predicts on Jul+ prices, with a potential distribution shift
- Every other year (2013-2025) has complete 365/366-day coverage

### 🟢 Passed: Internal Consistency Checks

- No negative or zero prices
- No `min > mean` or `max < mean` violations
- No zero-volume price changes
- No gap days (time series is contiguous per item)
- Mean always equals median (expected — API returns single daily price, not OHLC)

---

## 2 — Implemented Fixes

### Fix 1: Dead Item Filter — `_filter_dead_items()`

Removes items where `max_price <= $0.05` AND lifetime price range < 5%.

Called early in `build_training_data()`, **before** feature engineering, so the 41% row reduction also makes downstream processing ~1.7x faster.

```python
item_stats = price_df.groupby("item_id")["price"].agg(["min", "max"])
dead_mask = (item_stats["max"] <= 0.05) & ((item_stats["max"] - item_stats["min"]) / item_stats["min"] < 0.05)
```

### Fix 2: Target Winsorization — `prepare_targets()`

Clips `target_return_{horizon}d` at ±500% after computation.

The 11,044 >1000% jumps were polluting gradient estimates. Winsorization preserves the directional signal (up/down) while capping the magnitude so corrupt 800,000% returns don't dominate the loss.

```python
winsorized = df[f"target_return_{horizon}d"].clip(-500.0, 500.0)
```

Only 0.1% of targets are actually clipped (the corrupt ones), so normal price action is unaffected.

### Fix 3: Corrupt Item Flagging — `_flag_corrupt_items()`

Counts how many times each item's daily price jumps exceed 500%. Items with **10+** such events are excluded from training entirely.

Excluded items are the 151 worst offenders (55 items with 50+ corrupt events each). These items are fundamentally unreliable — the API consistently returns corrupt data for them and fixing individual rows would be impractical.

### Fix 4: Sample Weighting — `_compute_sample_weights()`

Assigns training weight proportional to 30-day rolling std of daily returns. Volatile items get higher weight (capped at 99th percentile); flat items get down-weighted to ~0.1x.

Implemented via LightGBM's `weight` parameter on `Dataset`. Applied in both the main training loop and expanding-window CV evaluation for consistency.

### Fix 5: 2026 Distribution-Shift Guard — `build_training_data()`

Excludes all 2026 rows from training when the archive doesn't cover past June 1. Currently active — the 2026 backfill ends March 29, so ~400K 2026 rows are excluded.

Once the backfill is re-run to cover the full year (including the July+ period that matches prediction data), this guard will automatically deactivate.

---

## 3 — Remaining: Training Bottleneck in `_apply_multi_source_voting()`

The `_apply_multi_source_voting()` method uses `groupby(["item_id", "date"]).apply(vote)` on 5.5M rows after the DuckDB query. This is notoriously slow:

- The `vote()` function creates a `pd.Series` per group (Python-level overhead)
- 5.5M rows produce ~500K+ groups after the DuckDB query
- Estimated time: **2-5 minutes** for this single step
- Total `fetch_price_history` time: ~3-5 min (2s DuckDB + 3-5 min voting)

**Recommended fix:** Replace `groupby().apply()` with a vectorized approach using `transform` and `numpy` operations, or use DuckDB's native median aggregation before loading into pandas. This would reduce the step from ~3 min to ~5s.

**Estimated accuracy impact of this bottleneck:** Zero (voting logic is correct, just slow).

---

## 4 — Combined Impact

| Fix | Rows Removed | Est. Accuracy Gain |
|-----|-------------|-------------------|
| Dead item filter | ~4M (41%) | +2-5pp |
| Target winsorization | ~11K corrupt targets clipped | +1-3pp |
| Corrupt item exclusion | 151 items removed | +0.5-1pp |
| Sample weighting | N/A (weights, not removal) | +1-2pp |
| 2026 shift guard | ~400K (4%) | +1-2pp |
| **Total** | ~45% of raw rows | **+3-8pp cumulative** |

All gains are independent of feature engineering or model architecture improvements — they make the existing model train on higher-quality signal.
