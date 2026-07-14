# Workflow Chain Repair — 2026-07-12

## Context

The `price-forecast.yml` workflow was chained off `"Daily Trend Analysis"`, a
workflow that was removed in a prior cleanup (rule-based trend analysis
deleted). This broke the entire automation pipeline: the forecast never ran,
and backtest accuracy depended on the forecast, so it never ran either.

The `docs/operations.md` still documented the removed workflows and their
schedules.

## Changes

### P0 — Fixed `price-forecast.yml` chain target

**File:** `.github/workflows/price-forecast.yml`

- Changed `workflow_run.workflows` from `["Daily Trend Analysis"]` to
  `["Aggregator Market Update"]`.
- Updated the stale `if`-condition comment that referenced "trend analysis."
- Removed `price-forecast.yml`'s dependency on a non-existent workflow,
  restoring the automation chain.

### P1 — Updated `docs/operations.md`

**File:** `docs/operations.md`

- Removed `daily-trend-analysis`, `long-term-trend-analysis`, and
  `event-correlation-analysis` from the workflow table (no longer exist).
- Updated the data flow diagram to reflect the current chain:
  `Aggregator → Forecast → Backtest`.
- Removed obsolete manual testing commands for trend scripts.
- Updated expected patterns and troubleshooting sections.

### P2 — Created event correlation analysis workflow

**New file:** `.github/workflows/event-correlation-analysis.yml`

- Weekly schedule: Sunday 04:00 UTC.
- Manual `workflow_dispatch` support.
- Failure notification via `gh issue create`.
- Log artifact upload.

**New file:** `backend/scripts/event_correlation_analysis.py`

- Queries `events` table for market events (operations, updates, case drops).
- For each event, computes per-item price impacts at 1d/3d/7d horizons.
- Compares against a control group of same-type items for statistical
  significance (z-score).
- Writes results to `event_impacts`, `event_patterns`, and `event_correlations`.
- `event_correlations` applies 6 rigor checks (significance, control group
  diff, pattern consistency, confounding events, lag analysis, holdout
  validation) and computes a weighted confidence score.

**Modified:** `backend/scripts/run_task.py`

- Added `event_correlation` task entry.

### Additional fixes discovered during validation

**File:** `.github/workflows/backtest-accuracy.yml`

- The job's `if` condition was
  `github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success'`.
  This meant the `schedule` trigger (`0 8 * * 1-6`) would fire the workflow
  but the job would always skip itself, because `github.event_name` is
  `'schedule'` (not `'workflow_dispatch'`). The chain from the forecast still
  worked, but the standalone cron fallback was dead.
- **Fix:** Added `github.event_name == 'schedule'` to the condition.

**File:** `.github/workflows/aggregator-update.yml`

- Comment on line 10 still referenced "daily trend analysis (03:00 UTC) /
  forecast (04:00 UTC)."
- **Fix:** Updated to reflect the current chain.

## Result

The full automation chain is restored:

```
Aggregator Market Update (23:00 UTC)
  └─▶ Price Forecast (chained)
        └─▶ Backtest Accuracy (chained + 08:00 UTC fallback)

Event Correlation Analysis (Sunday 04:00 UTC, standalone)
```

All three new files/features are importable or YAML-valid. Pre-existing test
failures (3 `FakeAggregator`-related test failures) are unaffected.
