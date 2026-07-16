#!/usr/bin/env python3
"""
Coordinate-wise grid search over event decay constants (tau per event type).
Compares directional accuracy before vs after optimization.

Uses a single train/val split (not full walk-forward) for speed.

Usage:
    python scripts/optimize_event_decay.py --max-items 30
"""

import sys
import json
import logging
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import lightgbm as lgb

from database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("optimize_event_decay")

ARCHIVE_DIR = Path(__file__).parent.parent.parent / "price-archive"

DEFAULT_TAUS = {
    "major": 60,
    "operation": 21,
    "case_drop": 14,
    "update": 7,
    "game_update": 7,
}

TAU_GRIDS = {
    "major": [30, 45, 60, 90, 120, 180],
    "operation": [7, 10, 14, 21, 30, 45, 60],
    "case_drop": [3, 5, 7, 10, 14, 21, 30, 45],
    "update": [2, 3, 5, 7, 10, 14, 21],
    "game_update": [1, 2, 3, 5, 7, 10, 14],
}

EVENT_TYPES = ["major", "operation", "case_drop", "update", "game_update"]


def _load_parquet_items(con, min_rows=90, backfilled_only=False):
    where_clause = ""
    if backfilled_only:
        where_clause = f"""
            WHERE item_slug IN (
                SELECT DISTINCT item_slug
                FROM read_parquet('{ARCHIVE_DIR}/prices-*.parquet')
                WHERE source = 'STEAMCOMMUNITY'
            )
        """
    rows = con.sql(f"""
        SELECT item_slug,
               MIN(day) AS first_day,
               MAX(day) AS last_day,
               COUNT(*) AS row_count
        FROM read_parquet('{ARCHIVE_DIR}/prices-*.parquet')
        {where_clause}
        GROUP BY item_slug
        HAVING row_count >= {min_rows}
        ORDER BY row_count DESC
    """).fetchall()
    return rows


def _eval_with_taus(base_df, events_df, taus):
    """Single-split evaluation: train on first 2/3, evaluate on last 1/3.

    Returns {horizon: directional_accuracy}.
    Much faster than full walk-forward.
    """
    from models.forecaster import ItemForecaster

    db = SessionLocal()
    try:
        forecaster = ItemForecaster(db_session=db)
        forecaster.event_decay_constants = dict(taus)

        df = forecaster._add_event_features(base_df.copy(), events_df)

        non_event_cols = [c for c in base_df.columns if not c.startswith("event_")]
        all_feature_cols = [c for c in non_event_cols if c not in {
            "item_id", "date", "timestamp", "price", "volume", "name", "release_date"
        } and base_df[c].dtype in (np.float64, np.float32, np.int64, int, float)]
        event_cols = [c for c in df.columns if c.startswith("event_")]
        feature_cols = all_feature_cols + event_cols

        results = {}
        for horizon in forecaster.HORIZONS:
            tdf = forecaster.prepare_targets(df, horizon)
            tdf = tdf.dropna(subset=[f"target_return_{horizon}d"]).copy()
            tdf = tdf.sort_values(["item_id", "date"])

            if tdf.empty:
                continue

            dates = sorted(tdf["date"].unique())
            split_idx = len(dates) * 2 // 3
            train_dates = set(dates[:split_idx])
            val_dates = set(dates[split_idx:])

            train_df = tdf[tdf["date"].isin(train_dates)]
            val_df = tdf[tdf["date"].isin(val_dates)]

            if len(val_df) < 50 or len(train_df) < 100:
                continue

            if len(train_df) > 200000:
                train_df = train_df.sort_values("date").tail(200000)

            fcols = [c for c in feature_cols if c in tdf.columns]

            if len(fcols) > 2:
                corr = train_df[fcols].corr().abs()
                upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
                to_drop = set()
                for col in upper.columns:
                    highly_corr = upper[col][upper[col] > 0.95].index
                    to_drop.update(highly_corr)
                fcols = [c for c in fcols if c not in to_drop]

            X_train = train_df[fcols].fillna(train_df[fcols].median()).values
            y_train = train_df[f"target_return_{horizon}d"].values
            X_val = val_df[fcols].fillna(train_df[fcols].median()).values
            y_val = val_df[f"target_return_{horizon}d"].values

            model = lgb.train(
                {
                    "objective": "quantile", "alpha": 0.5, "metric": "quantile",
                    "boosting_type": "gbdt", "num_leaves": 31, "max_depth": 5,
                    "min_data_in_leaf": 15, "learning_rate": 0.03,
                    "feature_fraction": 0.7, "bagging_fraction": 0.7,
                    "bagging_freq": 5, "lambda_l1": 0.5, "lambda_l2": 0.5,
                    "verbosity": -1, "random_state": 42, "n_jobs": -1,
                },
                lgb.Dataset(X_train, y_train),
                num_boost_round=100,
                valid_sets=[lgb.Dataset(X_val, y_val)],
                callbacks=[lgb.early_stopping(15, verbose=False), lgb.log_evaluation(0)]
            )

            preds = model.predict(X_val)
            hits = np.sum((preds > 0) == (y_val > 0))
            total = len(y_val)
            results[horizon] = round(hits / total * 100, 2)

        return results
    finally:
        db.close()


def compute_score(results):
    """Unweighted average across horizons."""
    if not results:
        return 0.0
    return sum(results.values()) / len(results)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Optimize event decay constants")
    parser.add_argument("--max-items", type=int, default=30,
                        help="Number of items for evaluation")
    args = parser.parse_args()

    if not ARCHIVE_DIR.exists():
        logger.error(f"Parquet archive not found at {ARCHIVE_DIR}")
        return 1

    import duckdb
    con = duckdb.connect()

    try:
        db = SessionLocal()
        from models.forecaster import ItemForecaster
        forecaster = ItemForecaster(db_session=db)
        events_df = forecaster.fetch_events()
        db.close()

        items = _load_parquet_items(con, backfilled_only=True)
        items = items[:args.max_items]
        logger.info(f"  {len(items)} items for evaluation")

        all_rows = []
        for item_slug, first_day, last_day, row_count in items:
            rows = con.sql(f"""
                SELECT item_slug AS item_id, day AS timestamp, mean_price AS price, volume
                FROM read_parquet('{ARCHIVE_DIR}/prices-*.parquet')
                WHERE item_slug = ?
                ORDER BY day
            """, params=[item_slug]).fetchall()
            item_df = pd.DataFrame(rows, columns=["item_id", "timestamp", "price", "volume"])
            item_df["timestamp"] = pd.to_datetime(item_df["timestamp"])
            item_df["date"] = item_df["timestamp"].dt.date
            all_rows.append(item_df)

        prices_df = pd.concat(all_rows, ignore_index=True)

        # Pre-build base features once (everything except event decay columns)
        logger.info("Building base features...")
        base_df = forecaster.engineer_features(prices_df, events_df)


        # Baseline
        logger.info("=" * 60)
        logger.info("BASELINE (default taus)")
        logger.info("=" * 60)
        baseline = _eval_with_taus(base_df, events_df, DEFAULT_TAUS)
        baseline_score = compute_score(baseline)
        logger.info(f"  Score: {baseline_score:.2f}%")
        for h in sorted(baseline):
            logger.info(f"    {h}d: {baseline[h]:.2f}%")

        best_taus = dict(DEFAULT_TAUS)
        best_score = baseline_score

        # Coordinate-wise search
        logger.info(f"\n{'=' * 60}")
        logger.info("COORDINATE-WISE SEARCH")
        logger.info(f"{'=' * 60}")

        for event_type in EVENT_TYPES:
            event_best = (best_taus[event_type], best_score)
            for tau in TAU_GRIDS[event_type]:
                if tau == best_taus[event_type]:
                    continue
                candidate = dict(best_taus)
                candidate[event_type] = tau
                res = _eval_with_taus(base_df, events_df, candidate)
                score = compute_score(res)

                delta = score - baseline_score
                marker = ""
                if score > event_best[1]:
                    marker = " <<< BEST"
                    event_best = (tau, score)
                elif score > best_score:
                    marker = " (above baseline)"

                logger.info(
                    f"  {event_type}: tau={tau:3d} -> "
                    f"mean={score:.2f}% ({delta:+.2f}pp){marker}"
                )
                for h in sorted(res):
                    d = res[h] - baseline[h]
                    logger.info(f"           {h}d: {res[h]:.2f}% ({d:+.2f}pp)")

            if event_best[0] != best_taus[event_type]:
                delta = event_best[1] - baseline_score
                logger.info(f"  >> Best {event_type}: tau={event_best[0]} "
                            f"(mean={event_best[1]:.2f}%, {delta:+.2f}pp)")
                best_taus[event_type] = event_best[0]
                best_score = event_best[1]

        # Final result
        final = _eval_with_taus(base_df, events_df, best_taus)
        final_score = compute_score(final)

        print("\n" + "=" * 60)
        print("FINAL RESULT")
        print("=" * 60)
        print(f"\nDefault taus: {DEFAULT_TAUS}")
        print(f"Optimal taus: {best_taus}")
        print(f"Mean directional accuracy: {baseline_score:.2f}% -> {final_score:.2f}% "
              f"({final_score - baseline_score:+.2f}pp)\n")

        print(f"{'Horizon':>8} | {'Before %':>9} | {'After %':>9} | {'Delta':>7}")
        print("-" * 42)
        for h in sorted(baseline):
            b = baseline[h]
            a = final[h]
            print(f"{h:>8}d | {b:>8.2f}% | {a:>8.2f}% | {a-b:>+6.2f}pp")
        print("-" * 42)
        print(f"{'MEAN':>8} | {baseline_score:>8.2f}% | {final_score:>8.2f}% | "
              f"{final_score - baseline_score:>+6.2f}pp")

        summary = {
            "default_taus": DEFAULT_TAUS,
            "optimal_taus": best_taus,
            "baseline_mean": round(baseline_score, 2),
            "optimal_mean": round(final_score, 2),
            "improvement_pp": round(final_score - baseline_score, 2),
            "per_horizon": {},
        }
        for h in sorted(baseline):
            summary["per_horizon"][h] = {
                "before": baseline[h],
                "after": final[h],
                "delta": round(final[h] - baseline[h], 2),
            }
        print(f"\nJSON: {json.dumps(summary, indent=2)}")

    finally:
        con.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
