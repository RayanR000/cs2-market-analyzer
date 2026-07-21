# CS2 Market Analyzer

Daily pipeline collects multi-source prices from 7 markets, archives to Parquet, serves via FastAPI to a Next.js dashboard, and forecasts via LightGBM quantile ensembles.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Framer Motion |
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, Alembic, Pydantic Settings |
| Data | PostgreSQL / Supabase, DuckDB, Parquet, Pandas, NumPy, SciPy |
| ML | LightGBM, Optuna |
| Automation | GitHub Actions (7 workflows) |

## Project Structure

```
backend/            — FastAPI server, routes, collectors, models, tests
frontend/           — Next.js app router, components, API client
docs/               — Architecture, changelog, references, research
price-archive/      — Parquet price data (13 years)
price-archive/ops/  — Parquet operational data (events, forecasts, accuracy, supply, etc.)
.github/workflows/  — 7 CI/CD workflows
```

## Commands

### Backend (from `backend/`)
- `uvicorn main:app --host 0.0.0.0 --port 8000` — start server
- `pytest` — run all tests
- `pytest tests/test_file.py -k "test_name"` — run specific test
- `python3 -m py_compile main.py` — syntax check
- `alembic upgrade head` — run migrations

## Gotchas

- **`daily_analysis` table was dropped** (migration 0015). Superseded by `item_forecasts` + Parquet.
- **API client lives in `frontend/lib/api.ts`.** Update both backend router and this client when adding routes.
- **Training data comes from Parquet, not Supabase.** `fetch_price_history(backfilled_only=True)` reads `price-archive/*.parquet` via DuckDB. DB is only queried for `is_backfilled` flag + events metadata (~2s).
- **Operational tables migrated to `price-archive/ops/*.parquet`.** Events, forecasts, outcomes, accuracy, supply snapshots, social mentions, collection runs, and event impacts are now dual-written to Parquet. API routes read from Parquet first with DB fallback. Run `python scripts/migrate_to_parquet.py` to initialize. See `backend/db/parquet.py` for the utility module.
- **Retrain bottleneck is Optuna, not I/O.** Data loading ~3 min; Optuna search was ~38 min (64% of total). After optimizing: `N_TRIALS_MAP[3]=20`, `MedianPruner` activated, `bagging_fraction` searched. Quick 3d validation: run `optuna_3d_search.py` with 200 items (~58s).
- **`N_TRIALS_MAP[3]=20, [7]=15`** with `SKIP_HP_HORIZONS=[14,30]`. Warm-start params: depth=5, leaves=47, λ₂=1.5, lr=0.01. `bagging_fraction` is now searched (was fixed at 0.7). `MedianPruner` with `n_startup_trials=3, n_warmup_steps=5` kills unpromising trials early via `trial.report()` + `trial.should_prune()`.
- **DART enabled for 14d/30d** (`BOOSTING_TYPE_MAP[14]=dart, [30]=dart`). Reduces `num_boost_round` from 1000→500 (via `DART_NUM_BOOST_ROUND`). Adds +0.5-2pp accuracy at same/faster speed. Early stopping disabled for DART (incompatible). `drop_rate`, `max_drop`, `skip_drop` searched during Optuna.
- **Warm retrain auto-skips CV.** When `tuned_params` are cached, `_warm_retrain=True` skips the expanding-window CV step (~4 min saved). Confidence thresholds and conformal q_hat are restored from the previous run's `meta.json`.
- **Regime-switching:** `forecaster.py` trains separate models per regime (bear/range/bull). Use `--compare-regime` in `forecast_prices.py` for A/B comparison. Adds ~23 min to retrain.
- **Social sentiment features are non-functional:** VADER scores CS2 jargon as neutral. The 5 social features (`social_mentions_1d`, `social_mentions_7d`, `social_mention_velocity`, `social_sentiment_7d`, `social_score_7d`) don't rank in top 20 by gain importance. Collector runs 4×/day but features won't help prediction until VADER is replaced with ModernFinBERT.

## Workflow Rules

1. Run `pytest` + `python3 -m py_compile` for backend changes.
2. Run `npm run lint` + `npm run build` for frontend changes.
3. When adding API routes, also update `frontend/lib/api.ts`.
4. Keep `frontend/AGENTS.md` in sync if design tokens or API surface changes.
5. For frontend design, see `frontend/AGENTS.md` (OKLCH tokens, typography, styling rules).
6. Use subagents: `@review` after significant work, `@data` for Parquet queries, `@explore` for codebase search, `@document` for changelog/architecture.
7. When adding agents, update `opencode.json` task permissions and this file.
