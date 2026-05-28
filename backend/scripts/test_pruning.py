#!/usr/bin/env python3
"""
Test script for database pruning.
Shows before/after state and verifies pruning works correctly.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, PriceHistory
from prune_database import downsample_price_history, prune_trend_indicators

def get_stats():
    """Get current data distribution by tier."""
    db = SessionLocal()
    now = datetime.utcnow()

    tier_0_7 = db.query(PriceHistory).filter(
        PriceHistory.timestamp >= now - timedelta(days=7)
    ).count()

    tier_7_30 = db.query(PriceHistory).filter(
        PriceHistory.timestamp >= now - timedelta(days=30),
        PriceHistory.timestamp < now - timedelta(days=7)
    ).count()

    tier_30_365 = db.query(PriceHistory).filter(
        PriceHistory.timestamp >= now - timedelta(days=365),
        PriceHistory.timestamp < now - timedelta(days=30)
    ).count()

    tier_365_plus = db.query(PriceHistory).filter(
        PriceHistory.timestamp < now - timedelta(days=365)
    ).count()

    total = tier_0_7 + tier_7_30 + tier_30_365 + tier_365_plus

    db.close()

    return {
        '0-7d': tier_0_7,
        '7-30d': tier_7_30,
        '30-365d': tier_30_365,
        '365+d': tier_365_plus,
        'total': total
    }

def print_stats(label, stats):
    """Print formatted statistics."""
    total = stats['total']
    mb = (total * 150) / (1024 * 1024)

    print(f"\n{label}")
    print("=" * 70)
    print(f"  0-7 days:      {stats['0-7d']:>10,} records")
    print(f"  7-30 days:     {stats['7-30d']:>10,} records")
    print(f"  30-365 days:   {stats['30-365d']:>10,} records")
    print(f"  365+ days:     {stats['365+d']:>10,} records")
    print("-" * 70)
    print(f"  TOTAL:         {total:>10,} records (~{mb:.2f} MB)")

def main():
    print("\n" + "=" * 70)
    print("DATABASE PRUNING TEST")
    print("=" * 70)

    # Step 1: Get before stats
    print("\n⏱️  STEP 1: Current database state")
    before_stats = get_stats()
    print_stats("BEFORE PRUNING", before_stats)

    # Step 2: Dry run
    print("\n⏱️  STEP 2: Running dry-run (no changes)")
    print("=" * 70)
    db = SessionLocal()
    would_downsample = downsample_price_history(db, dry_run=True)
    db.close()
    print(f"✓ Dry-run complete: Would affect {would_downsample:,} records")

    # Step 3: Actual pruning
    print("\n⏱️  STEP 3: Running actual pruning")
    print("=" * 70)
    db = SessionLocal()
    downsampled = downsample_price_history(db, dry_run=False)
    pruned_trends = prune_trend_indicators(db, dry_run=False)
    db.close()
    print(f"✓ Downsampling complete: {downsampled:,} records affected")
    print(f"✓ Trend pruning complete: {pruned_trends:,} records deleted")

    # Step 4: Get after stats
    print("\n⏱️  STEP 4: Database state after pruning")
    after_stats = get_stats()
    print_stats("AFTER PRUNING", after_stats)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    records_affected = before_stats['total'] - after_stats['total']
    mb_before = (before_stats['total'] * 150) / (1024 * 1024)
    mb_after = (after_stats['total'] * 150) / (1024 * 1024)
    mb_saved = mb_before - mb_after

    print(f"Records deleted: {records_affected:,}")
    print(f"Storage before: {mb_before:.2f} MB")
    print(f"Storage after:  {mb_after:.2f} MB")
    print(f"Storage saved:  {mb_saved:.2f} MB ({(mb_saved/mb_before)*100:.1f}% reduction)")

    # Verify tiers look correct
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    checks = [
        ("✓" if after_stats['0-7d'] > 0 else "✗", "0-7d tier has data (should be > 0)"),
        ("✓" if after_stats['365+d'] < before_stats['365+d'] else "✗", "365+d tier was downsampled"),
        ("✓" if after_stats['total'] < before_stats['total'] else "✗", "Total records decreased"),
    ]

    for status, check in checks:
        print(f"  {status} {check}")

    print("\n✅ Pruning test complete!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
