"""
CS2 player count collector — Steam API.
Fetches concurrent player count from Steam's public endpoint
and appends to a daily CSV for Parquet archival.

Supports both hourly intra-day collection (via --append)
and the daily 23:00 UTC snapshot (via pipeline integration).
"""

import csv
import os
import logging
import requests
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

STEAM_API_URL = (
    "https://api.steampowered.com/"
    "ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=730"
)

PLAYER_COUNTS_DIR = "/tmp/player-counts"


def fetch_current_cs2_players() -> Optional[int]:
    resp = requests.get(STEAM_API_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    count = data.get("response", {}).get("player_count")
    if count is None:
        logger.warning("Steam API response missing player_count: %s", data)
        return None
    return int(count)


def _daily_csv_path(date_str: Optional[str] = None) -> str:
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(PLAYER_COUNTS_DIR, exist_ok=True)
    return os.path.join(PLAYER_COUNTS_DIR, f"{date_str}.csv")


def collect_and_append(date_str: Optional[str] = None) -> Optional[int]:
    """Fetch current player count and append to the day's CSV.

    Returns the player count, or None on failure.
    """
    count = fetch_current_cs2_players()
    if count is None:
        return None

    path = _daily_csv_path(date_str)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "players"])
        writer.writerow([now_iso, count])

    logger.info("Player count: %s → %s (%s)", count, path, now_iso)
    return count


def get_daily_csv_path(date_str: Optional[str] = None) -> str:
    return _daily_csv_path(date_str)


def read_daily_csv(date_str: Optional[str] = None) -> list[dict]:
    """Read all readings from the day's CSV (for Parquet conversion)."""
    path = _daily_csv_path(date_str)
    if not os.path.exists(path):
        logger.warning("No player count CSV found at %s", path)
        return []
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def summarize_daily_csv(date_str: Optional[str] = None) -> Optional[dict]:
    """Compute daily stats from CSV: mean, peak, count, last."""
    rows = read_daily_csv(date_str)
    if not rows:
        return None
    players = [int(r["players"]) for r in rows]
    return {
        "date": (date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "mean_players": round(sum(players) / len(players)),
        "peak_players": max(players),
        "min_players": min(players),
        "reading_count": len(players),
        "last_players": players[-1],
        "last_timestamp": rows[-1]["timestamp"],
    }


if __name__ == "__main__":
    count = collect_and_append()
    if count is None:
        print("Failed to fetch player count", flush=True)
        sys.exit(1)
    print(f"Player count: {count}", flush=True)
