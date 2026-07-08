#!/usr/bin/env python3
"""
Daily: append today's aggregator rows to the current year's Parquet file.

Reads today's prices from Supabase (aggregator_sync, steam_batch sources),
appends to archive/price-archive/prices-YYYY.parquet, then runs
build_chart_points.py to upsert today's close.

Usage:
    python scripts/append_to_parquet.py --date 2026-07-08 --out-dir ../archive
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine


FETCH_TODAY_SQL = """
    SELECT i.item_id AS item_slug,
           DATE(ph.timestamp) AS day,
           ph.price,
           ph.volume,
           ph.median_price,
           ph.source
    FROM price_history ph
    JOIN items i ON i.id = ph.item_id
    WHERE ph.timestamp >= :day_start AND ph.timestamp < :day_end
      AND ph.source IN ('aggregator_sync', 'steam_batch')
    ORDER BY i.item_id, ph.timestamp
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        help="UTC day to export (YYYY-MM-DD, default: today)",
    )
    parser.add_argument(
        "--out-dir",
        default="../archive",
        help="Archive root; price-archive lives under this",
    )
    parser.add_argument(
        "--skip-chart-points",
        action="store_true",
        help="Skip the chart_points sync step",
    )
    args = parser.parse_args()

    day_start = datetime.strptime(args.date, "%Y-%m-%d")
    day_end = day_start + timedelta(days=1)

    # 1. Fetch today's rows from Supabase
    with engine.connect() as conn:
        rows = conn.execute(
            text(FETCH_TODAY_SQL),
            {"day_start": day_start, "day_end": day_end},
        ).fetchall()

    if not rows:
        print(f"No rows found for {args.date}")
        sys.exit(0)

    df = pd.DataFrame(rows, columns=["item_slug", "day", "price", "volume", "median_price", "source"])

    # Collapse to daily mean/min/max/median/volume per item slug
    daily = df.groupby(["item_slug", "day"]).agg(
        mean_price=("price", "mean"),
        min_price=("price", "min"),
        max_price=("price", "max"),
        median_price=("median_price", "mean"),
        volume=("volume", "sum"),
    ).reset_index()

    daily["day"] = daily["day"].dt.date

    year = day_start.year
    out_dir = Path(args.out_dir) / "price-archive"
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / f"prices-{year}.parquet"

    # 2. Append to the year's Parquet file
    con = duckdb.connect()
    if parquet_path.exists():
        existing = con.sql(f"SELECT * FROM read_parquet('{parquet_path}')").fetchdf()
        combined = pd.concat([existing, daily], ignore_index=True)
        combined = combined.drop_duplicates(subset=["item_slug", "day"], keep="last")
        combined.to_parquet(parquet_path, index=False)
        appended = len(daily)
        total = len(combined)
    else:
        daily.to_parquet(parquet_path, index=False)
        appended = len(daily)
        total = appended

    con.close()

    size_mb = parquet_path.stat().st_size / (1024 * 1024)
    print(f"Appended {appended} rows to {parquet_path.name} ({total} total, {size_mb:.1f} MB)")

    # 3. Sync to chart_points
    if not args.skip_chart_points:
        import subprocess
        script_path = Path(__file__).parent / "build_chart_points.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--parquet-dir", str(out_dir), "--date", args.date],
            capture_output=False,
        )
        if result.returncode != 0:
            print(f"Warning: chart_points sync exited with code {result.returncode}")

    print(f"Done: {args.date}")


if __name__ == "__main__":
    main()
