#!/usr/bin/env python3
"""
Check workflow health and recent data collection.
Monitors whether scheduled workflows are actually collecting data.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy import func, desc

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, Item, PriceHistory, CollectionRun

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger("workflow_health")

def format_time(dt):
    """Format datetime for display."""
    if not dt:
        return "N/A"
    return dt.strftime('%Y-%m-%d %H:%M:%S %Z')

def check_workflow_health():
    """Check recent workflow execution and data collection."""
    db = SessionLocal()

    try:
        print("\n" + "="*70)
        print("WORKFLOW HEALTH CHECK")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")

        # Recent collection runs (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_runs = db.query(CollectionRun).filter(
            CollectionRun.started_at >= seven_days_ago
        ).order_by(desc(CollectionRun.started_at)).all()

        print(f"📊 COLLECTION RUNS (Last 7 Days): {len(recent_runs)} runs")
        print("-" * 70)

        if recent_runs:
            for run in recent_runs[:10]:  # Show last 10
                status = "✅ SUCCESS" if run.success else "❌ FAILED"
                duration = ""
                if run.started_at and run.completed_at:
                    delta = (run.completed_at - run.started_at).total_seconds()
                    duration = f" ({delta:.1f}s)"

                print(f"{status} | {format_time(run.started_at)}{duration}")
                print(f"    Items collected: {run.items_collected} | Errors: {run.errors_count}")
                print(f"    Runner: {run.runner} | Version: {run.collector_version}")
                print()
        else:
            print("⚠️  No collection runs found in the last 7 days")
            print()

        # Most recent run details
        if recent_runs:
            latest = recent_runs[0]
            print(f"\n📈 MOST RECENT RUN")
            print("-" * 70)
            print(f"Status: {'✅ SUCCESS' if latest.success else '❌ FAILED'}")
            print(f"Started: {format_time(latest.started_at)}")
            print(f"Completed: {format_time(latest.completed_at)}")

            if latest.started_at and latest.completed_at:
                duration = (latest.completed_at - latest.started_at).total_seconds()
                print(f"Duration: {duration:.1f} seconds")

            print(f"Items Collected: {latest.items_collected}")
            print(f"Errors: {latest.errors_count}")
            print(f"Runner: {latest.runner}")
            print(f"Collector Version: {latest.collector_version}")
            if latest.notes:
                print(f"Notes: {latest.notes}")

        # Database statistics
        print(f"\n📦 DATABASE STATISTICS")
        print("-" * 70)

        total_items = db.query(func.count(Item.id)).scalar()
        total_prices = db.query(func.count(PriceHistory.id)).scalar()

        print(f"Total Items: {total_items:,}")
        print(f"Total Price Records: {total_prices:,}")

        # Recent price updates (last 24 hours)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        recent_prices = db.query(func.count(PriceHistory.id)).filter(
            PriceHistory.recorded_at >= one_day_ago
        ).scalar()

        print(f"Price Updates (Last 24h): {recent_prices:,}")

        # Workflow schedule expectations
        print(f"\n⏰ SCHEDULE INFORMATION")
        print("-" * 70)
        print("Aggregator Market Update (17k items):")
        print("  Schedule: Every 6 hours (3:30, 9:30, 15:30, 21:30 UTC)")
        print("  EST times: 11:30 PM, 5:30 AM, 11:30 AM, 5:30 PM")

        # Check if we have runs near expected times
        if recent_runs:
            hours_in_day = {}
            for run in recent_runs[:30]:  # Last 30 runs
                hour = run.started_at.hour
                hours_in_day[hour] = hours_in_day.get(hour, 0) + 1

            expected_hours = [3, 9, 15, 21]
            print(f"\n  Run frequency by hour (UTC):")
            for hour in sorted(hours_in_day.keys()):
                count = hours_in_day[hour]
                expected = "✅" if hour in expected_hours else "⚠️"
                print(f"    {expected} {hour:02d}:00 UTC - {count} run(s)")

        print("\nDatabase Maintenance (Pruning):")
        print("  Schedule: Every Sunday at 08:00 UTC (04:00 AM EST)")

        print("\n" + "="*70)

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    check_workflow_health()
