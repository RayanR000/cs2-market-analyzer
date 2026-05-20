#!/usr/bin/env python3
"""
Manual backfill script for free CS2 historical data.

Usage:
    cd backend
    CS2SH_API_KEY=... python scripts/import_free_market_data.py
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime

from collectors.free_data_importer import FreeDataBackfillImporter


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill free CS2 history and events")
    parser.add_argument(
        "--history-start",
        default="2023-01-01",
        help="Archive history start date (YYYY-MM-DD). Default: 2023-01-01",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    history_start = datetime.fromisoformat(args.history_start)

    importer = FreeDataBackfillImporter()
    stats = importer.run_full_import(history_start=history_start)
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
