#!/usr/bin/env python3
"""
Compare event decay constants using full walk-forward evaluation.
Runs with default taus, then with optimal taus, then prints comparison.

Usage:
    python scripts/compare_event_decay.py --max-items 30
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import lightgbm as lgb

from database import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("compare_event_decay")

ARCHIVE_DIR = Path(__file__).parent.parent.parent / "price-archive"

DEFAULT_TAUS = {"major": 60, "operation": 21, "case_drop": 14, "update": 7, "game_update": 7}
OPTIMAL_TAUS = {"major": 60, "operation": 45, "case_drop": 14, "update": 7, "game_update": 7}


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


def run_walkforward_eval(prices_df, events_df, taus, max_items=30):
    """Full walk-forward evaluation. Returns {horizon: {directional_accuracy, ...}}"""
    from models.forecaster import ItemForecaster
    db = SessionLocal()
    try:
        forecaster = ItemForecaster(db_session=db)
        forecaster.event_decay_constants = dict(taus)
        forecaster.feature_cols = []

        results_by_horizon = {}
        for horizon in forecaster.HORIZONS:
            df = forecaster.engineer_features(prices_df, events_df)


            tdf = forecaster.prepare_targets(df, horizon)
            tdf = tdf.dropna(subset=[f"target_return_{horizon}d"]).copy()
            tdf = tdf.sort_values(["item_id", "date"])

            if tdf.empty:
                continue

            dates = sorted(tdf["date"].unique())
            split_idx = len(dates) * 2 // 3

            directional_hits, directional_total = 0, 0
            VAL_WINDOW_DAYS, step = 21, 60

            for window_end in range(split_idx + 1, len(dates), step):
                train_dates = dates[:window_end]
                val_dates = dates[window_end:window_end + VAL_WINDOW_DAYS]
                if len(val_dates) < 7:
                    continue

                train_df = tdf[tdf["date"].isin(train_dates)]
                val_df = tdf[tdf["date"].isin(val_dates)]
                if len(val_df) < 50:
                    continue
                if len(train_df) > 200000:
                    train_df = train_df.sort_values("date").tail(200000)

                feature_cols = [c for c in forecaster.feature_cols if c in tdf.columns]
                if not feature_cols:
                    exclude = {"item_id", "date", "timestamp", "price", "volume", "name", "release_date"}
                    exclude |= {f"target_{h}d" for h in forecaster.HORIZONS}
                    exclude |= {f"target_return_{h}d" for h in forecaster.HORIZONS}
                    feature_cols = [c for c in tdf.columns if c not in exclude
                                    and tdf[c].dtype in (np.float64, np.float32, np.int64, int, float)]

                if len(feature_cols) > 2:
                    corr = train_df[feature_cols].corr().abs()
                    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
                    to_drop = set()
                    for col in upper.columns:
                        highly_corr = upper[col][upper[col] > 0.95].index
                        to_drop.update(highly_corr)
                    feature_cols = [c for c in feature_cols if c not in to_drop]

                X_train = train_df[feature_cols].fillna(train_df[feature_cols].median())
                y_train = train_df[f"target_return_{horizon}d"]
                X_val = val_df[feature_cols].fillna(train_df[feature_cols].median())
                y_val = val_df[f"target_return_{horizon}d"]

                models = {}
                for q in [0.1, 0.5, 0.9]:
                    params = {
                        "objective": "quantile", "alpha": q, "metric": "quantile",
                        "boosting_type": "gbdt", "num_leaves": 31, "max_depth": 5,
                        "min_data_in_leaf": 15, "min_gain_to_split": 0.1,
                        "learning_rate": 0.03, "feature_fraction": 0.7,
                        "bagging_fraction": 0.7, "bagging_freq": 5,
                        "lambda_l1": 0.5, "lambda_l2": 0.5,
                        "verbosity": -1, "random_state": 42, "n_jobs": -1,
                    }
                    dtrain = lgb.Dataset(X_train.values, y_train.values)
                    dval = lgb.Dataset(X_val.values, y_val.values, reference=dtrain)
                    model = lgb.train(
                        params, dtrain, num_boost_round=100,
                        valid_sets=[dval],
                        callbacks=[lgb.early_stopping(15, verbose=False), lgb.log_evaluation(0)]
                    )
                    models[q] = model.predict(X_val.values)

                p50_ret = models[0.5]
                y_val_a = y_val.values
                for i in range(len(val_df)):
                    mr = p50_ret[i]
                    ar = y_val_a[i]
                    actual_dir = "up" if ar > 0 else "down" if ar < 0 else "flat"
                    pred_dir = "up" if mr > 0 else "down" if mr < 0 else "flat"
                    if pred_dir == actual_dir:
                        directional_hits += 1
                    directional_total += 1

            if directional_total > 0:
                dir_acc = directional_hits / directional_total * 100
                results_by_horizon[horizon] = {
                    "directional_accuracy": round(dir_acc, 2),
                    "sample_count": directional_total,
                }
        return results_by_horizon
    finally:
        db.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items", type=int, default=30)
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

        items = _load_parquet_items(con, backfilled_only=True)[:args.max_items]
        logger.info(f"  {len(items)} items")

        all_rows = []
        for item_slug, *_ in items:
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

        logger.info("Running default taus (walk-forward)...")
        before = run_walkforward_eval(prices_df, events_df, DEFAULT_TAUS, args.max_items)

        logger.info("Running optimal taus (walk-forward)...")
        after = run_walkforward_eval(prices_df, events_df, OPTIMAL_TAUS, args.max_items)

        print("\n" + "=" * 60)
        print("EVENT DECAY OPTIMIZATION — BEFORE vs AFTER (Walk-Forward)")
        print("=" * 60)
        print(f"Default taus: {DEFAULT_TAUS}")
        print(f"Optimal taus: {OPTIMAL_TAUS}")
        print()

        print(f"{'Horizon':>8} | {'Before %':>9} | {'After %':>9} | {'Delta':>7} | {'Samples':>8}")
        print("-" * 50)
        before_accs, after_accs = [], []
        for h in sorted(before):
            b = before[h]["directional_accuracy"]
            a = after[h]["directional_accuracy"]
            n = after[h]["sample_count"]
            before_accs.append(b)
            after_accs.append(a)
            print(f"{h:>8}d | {b:>8.2f}% | {a:>8.2f}% | {a-b:>+6.2f}pp | {n:>8,}")
        print("-" * 50)
        mean_b = np.mean(before_accs)
        mean_a = np.mean(after_accs)
        print(f"{'MEAN':>8} | {mean_b:>8.2f}% | {mean_a:>8.2f}% | {mean_a - mean_b:>+6.2f}pp")

    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
