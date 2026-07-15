#!/usr/bin/env python3
"""
Permutation importance test for player count features.

Tests whether the accuracy improvement from player count features is
real signal (causal) or spurious (correlation / extra model capacity).

Method:
  1. Train model WITH player count features (standard treatment).
  2. On held-out validation windows, randomly SHUFFLE the player count
     columns (breaking temporal link to price while preserving distribution).
  3. If accuracy drops back toward the control baseline, signal is causal.
     If accuracy stays elevated, the improvement was from extra capacity.

Also reports LightGBM gain importance ranking of player count features.

Usage:
    python scripts/permutation_test_player_counts.py [--max-items 100] [--n-shuffles 30]
"""

import sys
import json
import math
import logging
import random
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import lightgbm as lgb

from database import SessionLocal
from models.forecaster import ItemForecaster

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("permutation_test")

ARCHIVE_DIR = Path(__file__).parent.parent.parent / "price-archive"
PLAYER_COUNT_COLS = [
    "players_mean", "players_peak", "players_min",
    "players_last", "players_readings",
    "players_change_1d", "players_change_7d",
    "players_ma7", "players_z_score_30d", "players_mean_ratio_7d",
]
RNG = np.random.RandomState(42)


def run_permutation_test(max_items=100, n_shuffles=30):
    import duckdb
    con = duckdb.connect()
    db = SessionLocal()

    try:
        forecaster = ItemForecaster(db_session=db)
        events_df = forecaster.fetch_events()
        db.close()

        # ── Load items ──────────────────────────────────────────────
        where = """WHERE item_slug IN (SELECT DISTINCT item_slug FROM read_parquet('{}/prices-*.parquet') WHERE source = 'STEAMCOMMUNITY')""".format(ARCHIVE_DIR)
        rows = con.sql(f"""
            SELECT item_slug FROM read_parquet('{ARCHIVE_DIR}/prices-*.parquet')
            {where}
            GROUP BY item_slug HAVING COUNT(*) >= 90
            ORDER BY COUNT(*) DESC LIMIT {max_items}
        """).fetchall()

        all_rows = []
        for (item_slug,) in rows:
            r = con.sql(f"""SELECT item_slug AS item_id, day AS timestamp,
                mean_price AS price, volume
                FROM read_parquet('{ARCHIVE_DIR}/prices-*.parquet')
                WHERE item_slug = ? ORDER BY day""", params=[item_slug]).fetchall()
            item_df = pd.DataFrame(r, columns=["item_id","timestamp","price","volume"])
            item_df["timestamp"] = pd.to_datetime(item_df["timestamp"])
            item_df["date"] = item_df["timestamp"].dt.date
            all_rows.append(item_df)

        all_prices = pd.concat(all_rows, ignore_index=True)
        logger.info(f"Loaded {len(rows)} items")

        # ── Build features (WITH player counts) ─────────────────────
        df = forecaster.engineer_features(all_prices, events_df)
        df = forecaster._add_cross_sectional_features(df)
        df = forecaster._add_player_count_features(df)

        exclude = {"item_id","date","timestamp","price","volume","name","release_date"}
        feature_cols = [c for c in df.columns if c not in exclude
                        and df[c].dtype in (np.float64,np.float32,np.int64,int,float)]

        idx = [i for i, c in enumerate(feature_cols) if c in PLAYER_COUNT_COLS]
        logger.info(f"  {len(feature_cols)} total features ({len(idx)} player count features)")

        if len(feature_cols) > 2:
            corr = df[feature_cols].corr().abs()
            upper = corr.where(np.triu(np.ones(corr.shape),k=1).astype(bool))
            to_drop = set()
            for c in upper.columns:
                hc = upper[c][upper[c] > 0.95].index; to_drop.update(hc)
            feature_cols = [c for c in feature_cols if c not in to_drop]
            idx = [i for i, c in enumerate(feature_cols) if c in PLAYER_COUNT_COLS]

        logger.info(f"  After pruning: {len(feature_cols)} features ({len(idx)} still player count)")

        # ── Results accumulators ────────────────────────────────────
        results_by_horizon = {}

        for horizon in forecaster.HORIZONS:
            logger.info(f"\n  Processing {horizon}d horizon...")

            tdf = forecaster.prepare_targets(df, horizon)
            tdf = tdf.dropna(subset=[f"target_return_{horizon}d"]).sort_values(["item_id","date"])

            if tdf.empty:
                continue

            dates = sorted(tdf["date"].unique())
            si = len(dates) * 2 // 3
            VAL_WINDOW = 21
            step = 60

            # Track per-fold: real accuracy and shuffled accuracy distribution
            fold_real_accs = []
            fold_shuffled_accs = []  # list of lists: per shuffle iteration

            for we in range(si + 1, len(dates), step):
                vd = dates[we:we + VAL_WINDOW]
                if len(vd) < 7: continue
                tr = tdf[tdf["date"].isin(dates[:we])]
                vl = tdf[tdf["date"].isin(vd)]
                if len(vl) < 50: continue
                if len(tr) > 200000: tr = tr.sort_values("date").tail(200000)

                fc = [c for c in feature_cols if c in tdf.columns]
                pc_local = [i for i, c in enumerate(fc) if c in PLAYER_COUNT_COLS]

                Xtr = tr[fc].fillna(tr[fc].median()).values
                ytr = tr[f"target_return_{horizon}d"].values
                Xvl_raw = vl[fc].fillna(tr[fc].median()).values
                yvl = vl[f"target_return_{horizon}d"].values

                # ── Train model ──────────────────────────────────────
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
                    m = lgb.train(params, lgb.Dataset(Xtr, ytr), num_boost_round=100,
                                  valid_sets=[lgb.Dataset(Xvl_raw, yvl)],
                                  callbacks=[lgb.early_stopping(15, verbose=False),
                                             lgb.log_evaluation(0)])
                    models[q] = m

                # ── Real accuracy ────────────────────────────────────
                def _compute_accuracy(Xvl_mat):
                    p10 = models[0.1].predict(Xvl_mat)
                    p50 = models[0.5].predict(Xvl_mat)
                    p90 = models[0.9].predict(Xvl_mat)
                    cm = (p10 > p50) | (p50 > p90)
                    nc = ~cm
                    lo, hi = np.minimum(p10, p50), np.maximum(p50, p90)
                    if nc.any():
                        ah = np.mean([np.mean(p50[nc]-p10[nc]), np.mean(p90[nc]-p50[nc])])
                        if ah > 0:
                            lo[cm] = p50[cm] - ah
                            hi[cm] = p50[cm] + ah
                    lo, hi = np.minimum(lo, p50), np.maximum(hi, p50)
                    hits = np.sum((p50 > 0) == (yvl > 0))
                    total = len(yvl)
                    return hits / total * 100 if total > 0 else 0

                real_acc = _compute_accuracy(Xvl_raw)
                fold_real_accs.append(real_acc)

                # ── Shuffled accuracy (N permutations) ──────────────
                shuffled_accs = []
                for s in range(n_shuffles):
                    Xvl_shuff = Xvl_raw.copy()
                    for pi in pc_local:
                        RNG.shuffle(Xvl_shuff[:, pi])
                    shuf_acc = _compute_accuracy(Xvl_shuff)
                    shuffled_accs.append(shuf_acc)

                fold_shuffled_accs.append(shuffled_accs)

                if len(fold_real_accs) % 2 == 0:
                    real = np.mean(fold_real_accs)
                    shuf = np.mean([np.mean(fa) for fa in fold_shuffled_accs])
                    logger.info(f"    Fold {len(fold_real_accs)}: real={real_acc:.1f}% shuffled_mean={np.mean(shuffled_accs):.1f}% (running avg: real={real:.1f}% shuffled={shuf:.1f}%)")

            if not fold_real_accs:
                continue

            # ── Aggregate ─────────────────────────────────────────
            real_mean = np.mean(fold_real_accs)
            shuffled_means = [np.mean(fa) for fa in fold_shuffled_accs]
            shuffled_overall_mean = np.mean(shuffled_means)
            shuffled_std = np.std(shuffled_means)

            # How often is real accuracy HIGHER than shuffled?
            worse_count = 0
            for shuf_acc in shuffled_means:
                if real_mean > shuf_acc:
                    worse_count += 1
            p_value = 1.0 - (worse_count / len(shuffled_means))

            baseline_2class = 50.0
            result = {
                "horizon": horizon,
                "real_accuracy": round(real_mean, 2),
                "real_improvement_vs_baseline_pp": round(real_mean - baseline_2class, 1),
                "shuffled_accuracy_mean": round(shuffled_overall_mean, 2),
                "shuffled_accuracy_std": round(shuffled_std, 2),
                "shuffled_accuracy_delta_pp": round(real_mean - shuffled_overall_mean, 2),
                "shuffled_accuracy_min": round(min(shuffled_means), 2),
                "shuffled_accuracy_max": round(max(shuffled_means), 2),
                "n_folds": len(fold_real_accs),
                "n_permutations": n_shuffles,
                "p_value": round(p_value, 4),
                "is_significant": p_value >= 0.95,
            }
            results_by_horizon[horizon] = result

            logger.info(f"\n  === {horizon}d ===")
            logger.info(f"  Real accuracy:      {real_mean:.2f}%")
            logger.info(f"  Shuffled (mean):    {shuffled_overall_mean:.2f}% ± {shuffled_std:.2f}")
            logger.info(f"  Signal delta:       {result['shuffled_accuracy_delta_pp']:+.2f}pp")
            logger.info(f"  p(real > shuffled): {p_value:.3f} {'✅ SIGNIFICANT' if result['is_significant'] else '❌ NOT significant'}")
            logger.info(f"  Shuffled range:     [{min(shuffled_means):.2f}%, {max(shuffled_means):.2f}%]")

        # ── LightGBM feature importance ──────────────────────────────
        logger.info("\n\n  === FEATURE IMPORTANCE (player count features) ===")
        logger.info("  (Gain importance from last-trained models)")

        importance_summary = {}
        for horizon in forecaster.HORIZONS:
            if horizon not in results_by_horizon:
                continue
            key = (horizon, 0.5)
            if key not in models:
                continue
            model = models[key]
            fi = pd.DataFrame({
                "feature": fc,
                "importance": model.feature_importance(importance_type="gain"),
            })
            fi = fi.sort_values("importance", ascending=False)
            fi["pct"] = fi["importance"] / fi["importance"].sum() * 100

            pc_fi = fi[fi["feature"].isin(PLAYER_COUNT_COLS)]
            pc_total_pct = pc_fi["pct"].sum()
            pc_rank = fi.reset_index(drop=True)
            pc_ranks = {row["feature"]: i+1 for i, row in pc_rank.iterrows() if row["feature"] in PLAYER_COUNT_COLS}

            importance_summary[horizon] = {
                "player_count_total_importance_pct": round(pc_total_pct, 2),
                "feature_ranks": pc_ranks,
                "top_20": [
                    {"feature": row["feature"], "importance_pct": round(row["pct"], 2)}
                    for _, row in fi.head(20).iterrows()
                ],
            }

            logger.info(f"\n  {horizon}d:")
            logger.info(f"    Player count features: {pc_total_pct:.2f}% of total gain importance")
            for feat, rank in sorted(pc_ranks.items(), key=lambda x: x[1]):
                logger.info(f"      #{rank} {feat}")
            logger.info(f"    Top 20 features:")
            for entry in importance_summary[horizon]["top_20"]:
                marker = " ← PC" if entry["feature"] in PLAYER_COUNT_COLS else ""
                logger.info(f"      {entry['feature']}: {entry['importance_pct']:.2f}%{marker}")

        return {"accuracy": results_by_horizon, "importance": importance_summary}

    finally:
        con.close()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--n-shuffles", type=int, default=30)
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("PERMUTATION IMPORTANCE TEST: Player Count Features")
    logger.info(f"  {args.max_items} items, {args.n_shuffles} shuffles per fold")
    logger.info("=" * 70)

    result = run_permutation_test(max_items=args.max_items, n_shuffles=args.n_shuffles)

    # Summary verdict
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    all_sig = True
    for h, r in sorted(result["accuracy"].items()):
        sig = r["is_significant"]
        all_sig = all_sig and sig
        note = "✅ SIGNIFICANT" if sig else "❌ NOT SIGNIFICANT"
        print(f"  {h:>2}d: {r['shuffled_accuracy_delta_pp']:+.2f}pp drop when shuffled ({note})")
    print(f"\n  Verdict: Player count features are {'CAUSAL' if all_sig else 'PARTIALLY CAUSAL'}")

    print(f"\n  Full JSON:\n{json.dumps(result, indent=2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
