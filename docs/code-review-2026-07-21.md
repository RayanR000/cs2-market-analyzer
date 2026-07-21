# Code Review — 2026-07-21

## 🔴 High Severity

### 1. Pagination double-slice bug
**Files:** `backend/api/routes/items.py:258,269`
**Impact:** Any request with `skip > 0` returns wrong/misaligned price history.
```
records = all_records[skip:skip + limit]          # line 258 — already slices
records_slice = records[skip:skip + limit]         # line 269 — re-slices the slice
```
Example: `skip=20, limit=50` with 200 records → first slice gives 50 records, second slice indexes into those 50 with offset 20, returning only 30 misaligned records.

---

### 2. Forecast fallback hardcodes 0.0 instead of actual price
**File:** `backend/api/routes/items.py:520-527`
**Impact:** Null Parquet forecast bounds collapse to zero instead of ±10% of current price.
```python
current_price = 0.0                                # hardcoded
fl = r.price_low or current_price * 0.9            # → 0.0 when r.price_low is None
fh = r.price_high or current_price * 1.1           # → 0.0 when r.price_high is None
```
Line 527 uses `r.current_price` correctly, but the low/high fallback paths were never updated to match the non-parquet branch.

---

### 3. Race condition in parallel ensemble training
**File:** `backend/models/forecaster.py:2256-2368`
**Impact:** Concurrent first-touch on a shared `lgb.Dataset` can corrupt bin boundaries, producing silently wrong models or segfaults.
- One `lgb.Dataset` (line 2256) is shared across `ThreadPoolExecutor` workers (line 2354)
- LightGBM Dataset construction is lazy — binning happens on first `train()` call
- 5+ threads racing on the same Dataset creates undefined behavior
- Zero test coverage for this path

---

### 4. CPU oversubscription
**File:** `backend/models/forecaster.py:2138,2346`
**Impact:** ~40 threads on 10 cores — parallelization likely degrades performance rather than improving it.
| Level | Mechanism | Workers | Threads/worker | Total threads |
|-------|-----------|---------|----------------|---------------|
| Horizon | `ProcessPoolExecutor` | 4 | — | 4 processes |
| Ensemble | `ThreadPoolExecutor` | ~5 | — | per process |
| LightGBM | `n_jobs` | — | ~2 | per ensemble |
| **Total** | | | | **~40 threads** |

Each horizon process independently computes its thread budget assuming it owns the machine.

---

### 5. Supply scraper 10x over-fetch
**File:** `backend/collectors/supply_scraper.py:48,158,173`
**Impact:** 10x more Steam Market requests than necessary, raising rate-limit/ban risk.
```
_fetch_steam_page(session, offset):  params = {"count": 100, "start": offset}
...
current_offset += 10                               # advances by 10, but fetched 100
```
Pages are [0-99], [10-109], [20-119] — 90% overlap. ~1,000 requests instead of ~100 for 10K items.

---

### 6. Silent transaction death in social sentiment collector
**File:** `backend/collectors/social_sentiment.py:193-238`
**Impact:** A failed INSERT aborts the PostgreSQL transaction. Subsequent statements silently fail. `db.commit()` fails. Parquet write succeeds, but DB data is lost — run reports fake success.
```python
try:
    db.execute(...)             # fails → transaction aborted
    parquet_rows.append(...)
    inserted += 1
except Exception as e:
    logger.warning(...)          # caught, but no rollback
                                  # loop continues on aborted transaction
db.commit()                      # fails — transaction was aborted
```
Returns `{"status": "success"}` regardless.

---

### 7. Hardcoded default secret key
**File:** `backend/config.py:59`
**Impact:** Session tokens forgeable on any deployment that forgot to set `SECRET_KEY` env var.
```python
secret_key: str = "your-secret-key-for-sessions"
```

---

### 8. SQL injection via string interpolation
**Files:**
- `backend/api/routes/events.py:20`
- `backend/api/routes/accuracy.py:53,239-244`
- `backend/api/routes/items.py:341-345,614-616,637-639`
**Impact:** Manual quote-escaping against DuckDB instead of the existing parameterized path (`ParquetQuery.query(sql, params=...)` from `db/parquet.py:169`).
```python
# events.py:20 — minimal escaping
where.append(f"type = '{type_filter.replace(chr(39), chr(39)+chr(39))}'")
# items.py:344 — no escaping at all, {item_id} may be user-controlled
df = q.query(f"SELECT * FROM item_forecasts WHERE item_id = {item_id} ...")
```
DuckDB connections have no `enable_external_access=false`, so `LOAD` extensions or filesystem reads are reachable.

---

### 9. Session token leaked into redirect URL
**File:** `backend/api/routes/auth.py:105`
**Impact:** Token appears in browser history, server logs, `Referer` headers, and analytics.
```python
redirect_url = f"{settings.frontend_url}/portfolio?session={token}"
resp.set_cookie(key="session", value=token, ...)   # also set as httponly cookie
```
The cookie is sufficient — the query param is redundant and leaks the token outside the httponly boundary.

---

### 10. Non-atomic Parquet writes, no backup
**Files:**
- `backend/db/parquet.py:80-90` (`append_table`)
- `backend/db/parquet.py:196-197` (ParquetQuery context manager write)
- `backend/scripts/append_to_parquet.py:178-195`
- `backend/scripts/migrate_to_parquet.py:159-169`
- `backend/scripts/merge_hf_dataset.py:150-172`
**Impact:** Crash mid-write corrupts the only copy of source-of-truth data.
```python
con.execute(f"COPY (...) TO '{path}' (FORMAT PARQUET)")  # writes directly to final path
```
Fix pattern: write to `{path}.tmp` → `os.replace()` for atomic rename.

---

### 11. `export_historical_parquet.py` unconditional overwrite
**File:** `backend/scripts/export_historical_parquet.py:78-86`
**Impact:** Running after live appends have happened destroys the newly appended rows — no merge or row-count check.

---

## 🟡 Medium Severity

| # | Issue | Files | Impact |
|---|-------|-------|--------|
| 12 | Duplicated auth logic | `auth.py` vs `portfolio.py` | One returns `None`, other raises 401. Callers get inconsistent error handling. Should be a shared `Depends`. |
| 13 | Unused validators | `data_validation.py` | `pipeline.py:141` only checks `price > 0`. A misparsed `$50,000` flows straight through. All validation infra is dead code. |
| 14 | 429 handling inconsistency | `csmarketapi_backfill.py` | 429 skips exponential backoff and immediately burns a key rotation — makes rate-limit recovery worse. |
| 15 | Copy-pasted retry/session logic | 8+ collector/script files | A fix in one (e.g., the `count=100` bug) won't propagate. Bug fix surface is fragmented. |
| 16 | Destructive scripts no confirmation gate | `migrate_historical_data.py`, `import_steam_items.py` | `--dry-run` is the only guard. One accidental run in prod = bulk DELETE with no undo. |
| 17 | Unsafe `joblib.load` for Ridge models | `forecaster.py:3695` | Pickle-based deserialization of arbitrary objects. Fine for self-produced models, but no trust-boundary comment. |

## 🟢 Test Coverage Gaps

| Missing tests for | What's at risk |
|---|---|
| All 9 API route files | Pagination bug, auth drift, SQL injection — completely untested |
| `test_price_history.py` | Not a real test — makes 5 live Steam API calls + opens DB at import time, zero assertions. Should be deleted or moved out of `tests/`. |
| `social_sentiment.py` | Transaction death bug has no regression safety |
| `supply_scraper.py` | 10x over-fetch bug has no regression safety |
| `csmarketapi_backfill.py` | 429 handling bug can't be caught without tests |
| `db/parquet.py` | Atomicity bug invisible to CI |
| `item_parser.py` / `steam_types.py` | Dead code paths have no guard |
| Parallel ensemble training | Race condition is timing-dependent — no test exercises `ThreadPoolExecutor` path |

## Simplification Opportunities

| Item | Files | Effort |
|------|-------|--------|
| Deduplicate `QualityVariantOut`/`GroupedMarketItemOut` | `schemas.py` + route files | ~40 lines removed |
| Delete dead code block | `steam_types.py:137-147` | ~10 lines removed (Souvenir prefix strip runs twice, second is unreachable) |
| Shared HTTP/retry helper | 4 collector files | ~200 lines consolidated |
