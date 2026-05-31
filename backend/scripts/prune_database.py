#!/usr/bin/env python3
"""
Database pruning and downsampling script (optimized for performance).
Implements tiered data retention using batch SQL operations:
  - Week (0-7 days): All data points
  - Month (7-30 days): Daily average
  - Year (30-365 days): Weekly average
  - Older (365+ days): Monthly average (kept indefinitely)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pruning")


def prune_trend_indicators(db_session, days_to_keep=180, dry_run=False):
    """Delete trend indicators older than days_to_keep."""
    from database import TrendIndicator
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

    query = db_session.query(TrendIndicator).filter(
        TrendIndicator.timestamp < cutoff_date
    )

    count = query.count()

    if count > 0 and not dry_run:
        query.delete()
        db_session.commit()
        logger.info(f"Deleted {count} trend indicator records older than {days_to_keep} days")

    return count


def prune_price_history(db_session, days_to_keep_granular=7, dry_run=False):
    """Backward-compatible alias for the current downsampling routine."""
    return downsample_price_history(
        db_session,
        days_to_keep_granular=days_to_keep_granular,
        dry_run=dry_run,
    )


def downsample_price_history(db_session, days_to_keep_granular=7, dry_run=False):
    """
    Downsample price history with tiered strategy.
    - 0-7 days: Keep all data
    - 7-30 days: Keep daily average (1 record per item per day)
    - 30-365 days: Keep weekly average (1 record per item per week)
    - 365+ days: Keep monthly average (1 record per item per month)
    """
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    year_ago = now - timedelta(days=365)

    total_deleted = 0

    # Tier 1: 7-30 days → Daily average
    deleted = _downsample_tier(
        db_session,
        week_ago,
        month_ago,
        "date(timestamp)::text",
        "daily averages (7-30 days)",
        dry_run
    )
    total_deleted += deleted

    # Tier 2: 30-365 days → Weekly average
    deleted = _downsample_tier(
        db_session,
        month_ago,
        year_ago,
        "to_char(timestamp, 'YYYY-WW')",
        "weekly averages (30-365 days)",
        dry_run
    )
    total_deleted += deleted

    # Tier 3: 365+ days → Monthly average
    deleted = _downsample_tier(
        db_session,
        year_ago,
        None,
        "to_char(timestamp, 'YYYY-MM')",
        "monthly averages (365+ days)",
        dry_run
    )
    total_deleted += deleted

    return total_deleted


def _downsample_tier(db_session, start_date, end_date, group_expr, desc, dry_run):
    """Delete records, keeping one per group with earliest timestamp."""

    # Build time filter
    if end_date:
        time_filter = f"timestamp >= '{start_date}' AND timestamp < '{end_date}'"
    else:
        time_filter = f"timestamp < '{start_date}'"

    # Count records to be deleted
    count_sql = f"SELECT COUNT(*) FROM price_history WHERE {time_filter}"
    result = db_session.execute(text(count_sql)).scalar()
    total_in_tier = result or 0

    if total_in_tier == 0:
        logger.info(f"Downsampled 0 records to {desc}")
        return 0

    if dry_run:
        logger.info(f"Would downsample {total_in_tier:,} records to {desc}")
        return total_in_tier

    # Find IDs to keep (earliest timestamp per item per group)
    keep_sql = f"""
    SELECT DISTINCT ON (item_id, {group_expr}) id
    FROM price_history
    WHERE {time_filter}
    ORDER BY item_id, {group_expr}, timestamp ASC
    """

    # Delete everything except what we're keeping
    delete_sql = f"""
    DELETE FROM price_history
    WHERE {time_filter}
    AND id NOT IN ({keep_sql})
    """

    try:
        db_session.execute(text(delete_sql))
        db_session.commit()

        # Count what was actually deleted
        result = db_session.execute(text(count_sql)).scalar()
        deleted_count = total_in_tier - (result or 0)

        logger.info(f"Downsampled {deleted_count:,} records to {desc}")
        return deleted_count

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error downsampling {desc}: {e}")
        raise


if __name__ == "__main__":
    db = SessionLocal()

    try:
        print("Starting database downsampling...")
        print("=" * 70)

        downsampled = downsample_price_history(db, dry_run=False)
        pruned_trends = prune_trend_indicators(db, dry_run=False)

        total = downsampled + pruned_trends
        print(f"\n✅ Maintenance complete:")
        print(f"  Downsampled records: {downsampled:,}")
        print(f"  Deleted old trends: {pruned_trends:,}")
        print(f"  Total records processed: {total:,}")
        print("=" * 70)

    except Exception as e:
        logger.error(f"❌ Pruning failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()
