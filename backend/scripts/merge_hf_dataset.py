#!/usr/bin/env python3
"""
Merge Hugging Face CS2 hourly price dataset into the Parquet archive.

Fills the Mar 22 – Apr 15 2026 window with daily OHLCV data from
BUFF / CSFloat / YouPin for ~33K items, covering 17 previously-empty
gap days (Mar 30 – Apr 15) and extending item coverage on the
8 overlap days (Mar 22–29).

Usage:
    python scripts/merge_hf_dataset.py [--out-dir ../archive]
"""

import argparse
import os
import sys
from pathlib import Path

import duckdb
import pandas as pd
import requests

HF_URL = (
    "https://huggingface.co/datasets/"
    "idomanteu/cs2-historical-item-prices-hourly-march-april-2026/"
    "resolve/main/cs2_listing_prices_hourly.parquet"
)

PRICE_COLS = ["item_slug", "day", "source", "mean_price", "min_price",
              "max_price", "median_price", "volume"]
SNAP_COLS = ["item_slug", "day", "source", "price", "volume"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", default="../archive",
        help="Archive root (default: ../archive)",
    )
    parser.add_argument(
        "--hf-file",
        help="Local path to HF Parquet (downloads if not provided)",
    )
    parser.add_argument(
        "--start-date", default="2026-03-22",
        help="Inclusive start date (default: 2026-03-22)",
    )
    parser.add_argument(
        "--end-date", default="2026-04-15",
        help="Inclusive end date (default: 2026-04-15)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir) / "price-archive"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Load HF dataset ────────────────────────────────────────────────
    if args.hf_file:
        hf_path = Path(args.hf_file)
        if not hf_path.exists():
            print(f"ERROR: {hf_path} not found", file=sys.stderr)
            sys.exit(1)
    else:
        local = Path("/tmp") / "cs2_listing_prices_hourly.parquet"
        if local.exists():
            print(f"Using cached {local}")
        else:
            print(f"Downloading from Hugging Face (~668 MB) ...")
            resp = requests.get(HF_URL, stream=True, timeout=300)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(local, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        pct = downloaded / total * 100 if total else 0
                        print(f"  {downloaded/1e6:.1f}/{total/1e6:.0f} MB ({pct:.0f}%)")
        hf_path = local
    print(f"Source: {hf_path}")

    con = duckdb.connect()
    try:
        df = con.sql(f"""
            SELECT
                market_hash_name  AS item_slug,
                CAST(bucket AS DATE)  AS day,
                CASE source
                    WHEN 'buff'    THEN 'aggregator_buff163'
                    WHEN 'csfloat' THEN 'aggregator_csfloat'
                    WHEN 'youpin'  THEN 'aggregator_youpin'
                END  AS source,
                close_ask  AS price,
                ask_volume AS volume
            FROM read_parquet('{hf_path}')
            WHERE source IN ('buff', 'csfloat', 'youpin')
              AND close_ask IS NOT NULL
              AND CAST(bucket AS DATE) >= '{args.start_date}'
              AND CAST(bucket AS DATE) <= '{args.end_date}'
        """).fetchdf()

        if df.empty:
            print("No rows after filtering — nothing to merge")
            sys.exit(0)

        print(f"Loaded {len(df):,} hourly rows "
              f"({df['day'].nunique()} days, "
              f"{df['item_slug'].nunique()} items, "
              f"{df['source'].nunique()} sources)")

        # ── Aggregate hourly → daily OHLCV ──────────────────────────────
        daily = df.groupby(["item_slug", "day", "source"], sort=False).agg(
            mean_price=("price", "mean"),
            min_price=("price", "min"),
            max_price=("price", "max"),
            median_price=("price", "median"),
            volume=("volume", "sum"),
        ).reset_index()

        daily["day"] = pd.to_datetime(daily["day"])
        print(f"Daily OHLCV: {len(daily):,} rows "
              f"({daily['day'].nunique()} days)")

        for src in sorted(daily["source"].unique()):
            subset = daily[daily["source"] == src]
            print(f"  {src}: {subset['item_slug'].nunique():,} items, "
                  f"{subset['day'].nunique()} days")

        # ── Build snapshot data (one row per day per source) ────────────
        snapshots = daily[["item_slug", "day", "source", "mean_price", "volume"]].copy()
        snapshots = snapshots.rename(columns={"mean_price": "price"})
        snapshots = snapshots[SNAP_COLS]

        # ── Append to archive ───────────────────────────────────────────
        prices_path = out_dir / "prices-2026.parquet"
        snaps_path = out_dir / "snapshots-2026.parquet"

        _append_parquet(prices_path, daily[PRICE_COLS],
                        ["item_slug", "day", "source"])
        _append_parquet(snaps_path, snapshots,
                        ["item_slug", "day", "source"])

        print(f"Done. Merged {args.start_date} to {args.end_date}")

    finally:
        con.close()


def _append_parquet(path: Path, new_data: pd.DataFrame, dedup_keys: list):
    """Append new_data to an existing Parquet file, deduplicating on keys.

    Mirrors append_to_parquet.py's _append_parquet logic for consistency.
    """
    con = duckdb.connect()
    try:
        if path.exists():
            existing = con.sql(
                f"SELECT * FROM read_parquet('{path}')"
            ).fetchdf()
            if "source" not in existing.columns and "source" in new_data.columns:
                existing["source"] = "aggregator_sync"
            combined = pd.concat([existing, new_data], ignore_index=True)
            combined = combined.drop_duplicates(subset=dedup_keys, keep="last")
            combined.to_parquet(path, index=False)
            print(f"  {path.name}: {len(new_data):,} appended, "
                  f"{len(combined):,} total")
        else:
            new_data.to_parquet(path, index=False)
            print(f"  {path.name}: {len(new_data):,} written (new file)")
    finally:
        con.close()


if __name__ == "__main__":
    main()
