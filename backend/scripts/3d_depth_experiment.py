#!/usr/bin/env python3
"""
Walk-forward A/B comparison: shallow (Optuna-chosen) vs deep capacity for the 3d horizon.

Tests whether Optuna's selection of max_depth=3 / num_leaves=15 / no regularization
for the 3d model was a genuine optimum or an artifact of under-exploration
(only 15 trials for a 6-dim search space).

Runs expanding-window CV on Parquet archive data, training both configs
on the same folds, and compares directional accuracy, pinball loss, and
interval coverage. Breaks down results by price tier.
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import lightgbm as lgb

from database import SessionLocal
from models.forecaster import ItemForecaster

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("depth_experiment")

ARCHIVE_DIR = Path(__file__).parent.parent.parent / "price-archive"
HORIZON = 3
VAL_WINDOW_DAYS = 21
STEP = 60

# --- Configs to compare ---
SHALLOW = {
    "max_depth": 3,
    "num_leaves": 15,
    "lambda_l1": 0.0,
    "lambda_l2": 0.0,
    "min_data_in_leaf": 20,
}

DEEP = {
    "max_depth": 6,
    "num_leaves": 47,
    "lambda_l1": 0.5,
    "lambda_l2": 0.5,
    "min_data_in_leaf": 10,
}

BASE_PARAMS = {
    "objective": "quantile",
    "metric": "quantile",
    "boosting_type": "gbdt",
    "learning_rate": 0.03,
    "feature_fraction": 0.7,
    "bagging_fraction": 0.7,
    "bagging_freq": 5,
    "min_gain_to_split": 0.1,
    "verbosity": -1,
    "random_state": 42,
    "n_jobs": -1,
}


def build_config_params(name, cfg):
    """Build the LightGBM param dict for one config."""
    return {**BASE_PARAMS, **cfg}


def pinball_loss(y_true, y_pred, alpha):
    """Compute pinball / quantile loss."""
    residual = y_true - y_pred
    return np.mean(np.maximum(alpha * residual, (alpha - 1) * residual))


def load_data(max_items=200):
    """Load items, prices, and features from the parquet archive."""
    import duckdb
    con = duckdb.connect()
    db = SessionLocal()
    try:
        forecaster = ItemForecaster(db_session=db)
        events_df = forecaster.fetch_events()
        db.close()

        items = con.sql(f"""
            SELECT item_slug,
                   MIN(day) AS first_day,
                   MAX(day) AS last_day,
                   COUNT(*) AS row_count
            FROM read_parquet('{ARCHIVE_DIR}/prices-*.parquet')
            GROUP BY item_slug
            HAVING row_count >= 90
            ORDER BY row_count DESC
        """).fetchall()
        items = items[:max_items]
        logger.info(f"Loaded {len(items)} backfilled items")

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

        all_prices = pd.concat(all_rows, ignore_index=True)
        df = forecaster.engineer_features(all_prices, events_df)
        df = forecaster._add_cross_sectional_features(df)

        logger.info(f"Feature matrix: {df.shape[0]} rows, {len(forecaster.feature_cols)} features")
        return df, forecaster
    finally:
        con.close()


def run_fold(name, params, X_train, y_train, X_val, y_val, prices_val):
    """Train a 3-quantile ensemble and return predictions + metrics."""
    models = {}
    for q in [0.1, 0.5, 0.9]:
        p = {**params, "alpha": q}
        dtrain = lgb.Dataset(X_train.values, y_train.values)
        dval = lgb.Dataset(X_val.values, y_val.values, reference=dtrain)
        model = lgb.train(
            p, dtrain,
            num_boost_round=200,
            valid_sets=[dval],
            callbacks=[lgb.early_stopping(20, verbose=False), lgb.log_evaluation(0)]
        )
        models[q] = model.predict(X_val.values)

    p10, p50, p90 = models[0.1], models[0.5], models[0.9]
    low_ret, high_ret = ItemForecaster._fix_quantile_crossing(p10, p50, p90)
    mid_ret = p50

    actual_returns = y_val.values
    current_prices = prices_val

    dir_hits = 0
    total = 0
    mae_sum = 0.0
    int_hits = 0
    losses = {0.1: [], 0.5: [], 0.9: []}
    tier_buckets = defaultdict(lambda: {"hits": 0, "total": 0})

    for i in range(len(val_df := y_val)):
        cr = float(current_prices.iloc[i]) if hasattr(current_prices, 'iloc') else float(current_prices[i])
        ar = float(actual_returns.iloc[i]) if hasattr(actual_returns, 'iloc') else float(actual_returns[i])
        lr, mr, hr = float(low_ret[i]), float(mid_ret[i]), float(high_ret[i])

        actual_future = cr * (1 + ar / 100)
        pred_future = cr * (1 + mr / 100)

        actual_dir = "up" if ar > 0 else "down"
        pred_dir = "up" if mr > 0 else "down"
        if pred_dir == actual_dir:
            dir_hits += 1
        total += 1

        mae_sum += abs(pred_future - actual_future)

        price_low = cr * (1 + lr / 100)
        price_high = cr * (1 + hr / 100)
        if price_low <= actual_future <= price_high:
            int_hits += 1

        for q in [0.1, 0.5, 0.9]:
            losses[q].append(ar - models[q][i])

        tier = _price_tier(cr)
        if actual_dir == pred_dir:
            tier_buckets[tier]["hits"] += 1
        tier_buckets[tier]["total"] += 1

    dir_acc = dir_hits / total * 100 if total > 0 else 0
    mae = mae_sum / total if total > 0 else 0
    int_cov = int_hits / total * 100 if total > 0 else 0

    pl = {}
    for q in [0.1, 0.5, 0.9]:
        pl[q] = float(pinball_loss(np.array(losses[q]), np.zeros(len(losses[q])), q))

    tier_acc = {}
    for tier, v in tier_buckets.items():
        tier_acc[tier] = round(v["hits"] / v["total"] * 100, 1) if v["total"] > 0 else 0

    return {
        "dir_acc": round(dir_acc, 2),
        "mae": round(mae, 4),
        "int_cov": round(int_cov, 2),
        "pinball": {str(k): round(v, 6) for k, v in pl.items()},
        "n": total,
        "tier_dir_acc": {str(k): v for k, v in sorted(tier_acc.items())},
    }


def _price_tier(price):
    if price < 5:
        return "<$5"
    elif price < 20:
        return "$5-20"
    elif price < 100:
        return "$20-100"
    else:
        return ">$100"


def main():
    logger.info("=" * 60)
    logger.info("3D DEPTH EXPERIMENT: Shallow vs Deep Capacity")
    logger.info("=" * 60)

    df, forecaster = load_data(max_items=200)

    # Build target table for 3d horizon
    tdf = forecaster.prepare_targets(df, HORIZON)
    tdf = tdf.dropna(subset=[f"target_return_{HORIZON}d"]).copy()
    tdf = tdf.sort_values(["item_id", "date"])

    logger.info(f"Target rows: {len(tdf):,}")

    feature_cols = [c for c in forecaster.feature_cols if c in tdf.columns]
    if not feature_cols:
        exclude = {"item_id", "date", "timestamp", "price", "volume", "name", "release_date"}
        exclude |= {f"target_{h}d" for h in forecaster.HORIZONS}
        exclude |= {f"target_return_{h}d" for h in forecaster.HORIZONS}
        feature_cols = [c for c in tdf.columns if c not in exclude
                        and tdf[c].dtype in (np.float64, np.float32, np.int64, int, float)]

    logger.info(f"Using {len(feature_cols)} features")

    # Walk-forward split
    dates = sorted(tdf["date"].unique())
    split_idx = len(dates) * 2 // 3
    logger.info(f"Date range: {dates[0]} to {dates[-1]} ({len(dates)} unique dates)")
    logger.info(f"Walk-forward start: split at idx {split_idx} (date {dates[split_idx]})")

    folds_shallow = []
    folds_deep = []
    configs = [
        ("shallow", SHALLOW, folds_shallow),
        ("deep", DEEP, folds_deep),
    ]

    fold_id = 0
    for window_end in range(split_idx + 1, len(dates), STEP):
        train_dates = dates[:window_end]
        val_dates = dates[window_end:window_end + VAL_WINDOW_DAYS]
        if len(val_dates) < 7:
            continue

        train_df = tdf[tdf["date"].isin(train_dates)]
        val_df = tdf[tdf["date"].isin(val_dates)]
        if len(val_df) < 50:
            continue

        fold_id += 1

        # Cap training rows
        if len(train_df) > 200000:
            train_df = train_df.sort_values("date").tail(200000)

        # Feature pruning at fold level
        if len(feature_cols) > 2:
            corr = train_df[feature_cols].corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
            to_drop = set()
            for col in upper.columns:
                if col in to_drop:
                    continue
                highly_corr = upper[col][upper[col] > 0.95].index
                to_drop.update(highly_corr)
            fcols = [c for c in feature_cols if c not in to_drop]
        else:
            fcols = feature_cols

        X_train = train_df[fcols].fillna(train_df[fcols].median())
        y_train = train_df[f"target_return_{HORIZON}d"]
        X_val = val_df[fcols].fillna(train_df[fcols].median())
        y_val = val_df[f"target_return_{HORIZON}d"]

        logger.info(f"Fold {fold_id}: train={len(X_train):,} val={len(X_val):,} "
                    f"dates={val_dates[0]}..{val_dates[-1]}")

        for name, cfg, storage in configs:
            result = run_fold(name, build_config_params(name, cfg),
                              X_train, y_train, X_val, y_val, val_df["price"])
            result["fold"] = fold_id
            result["val_start"] = str(val_dates[0])
            result["val_end"] = str(val_dates[-1])
            storage.append(result)
            logger.info(f"  {name}: dir_acc={result['dir_acc']:.1f}% "
                        f"pinball_50={result['pinball']['0.5']:.6f} "
                        f"int_cov={result['int_cov']:.1f}% "
                        f"n={result['n']}")

    # --- Aggregate results ---
    def aggregate(storage, label):
        if not storage:
            return {}
        total_n = sum(f["n"] for f in storage)
        weighted_dir = sum(f["dir_acc"] * f["n"] for f in storage) / total_n
        weighted_mae = sum(f["mae"] * f["n"] for f in storage) / total_n
        weighted_int = sum(f["int_cov"] * f["n"] for f in storage) / total_n

        mean_pl50 = np.mean([f["pinball"]["0.5"] for f in storage])
        mean_pl10 = np.mean([f["pinball"]["0.1"] for f in storage])
        mean_pl90 = np.mean([f["pinball"]["0.9"] for f in storage])

        accs = [f["dir_acc"] for f in storage]
        tiers = defaultdict(lambda: {"hits": 0, "total": 0})
        # Aggregate tier dir_acc across folds (weighted by fold-tier-n)
        # Simpler: report per-fold tier dir_acc means
        tier_fold_accs = defaultdict(list)
        for f in storage:
            for t, acc in f.get("tier_dir_acc", {}).items():
                tier_fold_accs[t].append(acc)

        return {
            "weighted_dir_acc": round(weighted_dir, 2),
            "weighted_mae": round(weighted_mae, 4),
            "weighted_int_cov": round(weighted_int, 2),
            "mean_pinball_10": round(mean_pl10, 6),
            "mean_pinball_50": round(mean_pl50, 6),
            "mean_pinball_90": round(mean_pl90, 6),
            "fold_count": len(storage),
            "total_samples": total_n,
            "fold_dir_accs": [f["dir_acc"] for f in storage],
            "tier_mean_dir_acc": {t: round(np.mean(v), 1) for t, v in sorted(tier_fold_accs.items())},
        }

    shallow_agg = aggregate(folds_shallow, "shallow")
    deep_agg = aggregate(folds_deep, "deep")

    # --- Print results ---
    print()
    print("=" * 70)
    print("RESULTS: Shallow (Optuna-chosen: depth=3, leaves=15, no reg) vs Deep (depth=6, leaves=47, reg=0.5)")
    print("=" * 70)

    for label, agg, folds_list in [
        ("SHALLOW (depth=3, leaves=15, l1=0, l2=0)", shallow_agg, folds_shallow),
        ("DEEP    (depth=6, leaves=47, l1=0.5, l2=0.5)", deep_agg, folds_deep),
    ]:
        print(f"\n  {label}")
        print(f"    Weighted DirAcc:   {agg['weighted_dir_acc']:.1f}%")
        print(f"    Weighted MAE:      ${agg['weighted_mae']:.4f}")
        print(f"    Weighted IntCov:   {agg['weighted_int_cov']:.1f}%")
        print(f"    Pinball (p10/p50/p90): {agg['mean_pinball_10']:.6f} / {agg['mean_pinball_50']:.6f} / {agg['mean_pinball_90']:.6f}")
        print(f"    Folds:             {agg['fold_count']} folds, {agg['total_samples']:,} samples")
        fold_str = ", ".join(f"{a:.1f}" for a in agg["fold_dir_accs"])
        print(f"    Fold DirAccs:      [{fold_str}]")
        if agg.get("tier_mean_dir_acc"):
            print(f"    Tier DirAcc:       {agg['tier_mean_dir_acc']}")

    # Paired fold comparison
    if folds_shallow and folds_deep:
        print(f"\n  PAIRED FOLD COMPARISON:")
        diffs = [d["dir_acc"] - s["dir_acc"] for s, d in zip(folds_shallow, folds_deep)]
        mean_diff = np.mean(diffs)
        std_diff = np.std(diffs)
        wins = sum(1 for d in diffs if d > 0)
        losses = sum(1 for d in diffs if d < 0)
        ties = sum(1 for d in diffs if d == 0)
        print(f"    Deep - Shallow DirAcc: {mean_diff:+.2f}pp (sd={std_diff:.2f})")
        print(f"    Deep wins / ties / losses: {wins} / {ties} / {losses} (over {len(diffs)} folds)")

        pl50_diffs = [d["pinball"]["0.5"] - s["pinball"]["0.5"]
                      for s, d in zip(folds_shallow, folds_deep)]
        print(f"    Deep - Shallow Pinball@50: {np.mean(pl50_diffs):+.6f} (negative = deep better)")

        int_diffs = [d["int_cov"] - s["int_cov"] for s, d in zip(folds_shallow, folds_deep)]
        print(f"    Deep - Shallow IntCov: {np.mean(int_diffs):+.2f}pp")

        mae_diffs = [d["mae"] - s["mae"] for s, d in zip(folds_shallow, folds_deep)]
        print(f"    Deep - Shallow MAE: ${np.mean(mae_diffs):+.4f}")

    print()
    result = {
        "horizon": HORIZON,
        "shallow": dict(shallow_agg),
        "deep": dict(deep_agg),
        "paired_comparison": {
            "dir_acc_diff_mean": round(float(mean_diff), 2) if folds_shallow and folds_deep else None,
            "dir_acc_diff_std": round(float(std_diff), 2) if folds_shallow and folds_deep else None,
            "deep_wins": wins if folds_shallow and folds_deep else None,
            "deep_losses": losses if folds_shallow and folds_deep else None,
            "pinball50_diff_mean": round(float(np.mean(pl50_diffs)), 6) if folds_shallow and folds_deep else None,
        } if folds_shallow and folds_deep else None,
    }

    print(f"\nJSON: {json.dumps(result, indent=2)}")

    # Save
    out_path = Path(__file__).parent.parent / "depth_experiment_result.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    logger.info(f"Saved to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
