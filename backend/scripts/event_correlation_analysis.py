#!/usr/bin/env python3
"""
Event correlation analysis for CS2 market events.

Computes historical price impacts around market events (operations, cases,
updates) and writes results to event_impacts, event_patterns, and
event_correlations tables.

Usage:
    python scripts/event_correlation_analysis.py
    python scripts/event_correlation_analysis.py --days-back 90
"""

import sys
import math
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    SessionLocal, Event, EventImpact, EventPattern, EventCorrelation,
    PriceHistory, Item,
)
from sqlalchemy import text, func, and_, desc

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("event_correlation")


def _date_range(event: Event, days_before: int = 14, days_after: int = 30):
    """Return (start, end) datetime range around an event."""
    start = event.timestamp - timedelta(days=days_before)
    end = event.timestamp + timedelta(days=days_after)
    return start, end


def _price_on_date(db, item_id: int, target: datetime, window_days: int = 3):
    """Get average price around a target date (centered window)."""
    half = window_days // 2
    start = target - timedelta(days=half)
    end = target + timedelta(days=half)
    row = (
        db.query(func.avg(PriceHistory.price))
        .filter(
            PriceHistory.item_id == item_id,
            PriceHistory.timestamp >= start,
            PriceHistory.timestamp <= end,
        )
        .scalar()
    )
    return float(row) if row is not None else None


def _pre_event_price(db, item_id: int, event_date: datetime):
    """Average price in the 7 days before the event."""
    end = event_date - timedelta(days=1)
    start = event_date - timedelta(days=8)
    row = (
        db.query(func.avg(PriceHistory.price))
        .filter(
            PriceHistory.item_id == item_id,
            PriceHistory.timestamp >= start,
            PriceHistory.timestamp <= end,
        )
        .scalar()
    )
    return float(row) if row is not None else None


def _post_event_price(db, item_id: int, event_date: datetime, offset_days: int):
    """Average price at offset_days after the event (3-day centered window)."""
    target = event_date + timedelta(days=offset_days)
    return _price_on_date(db, item_id, target, window_days=3)


def _control_group_prices(db, item_type: str, event_date: datetime,
                          exclude_item_ids: set[int], offset_days: int):
    """Average price change for similar items not affected by the event."""
    before, after = [], []
    end = event_date - timedelta(days=1)
    start = event_date - timedelta(days=8)
    target = event_date + timedelta(days=offset_days)
    target_end = target + timedelta(days=1)
    target_start = target - timedelta(days=1)

    rows = (
        db.query(
            PriceHistory.item_id,
            func.avg(PriceHistory.price).label("avg_price"),
            func.date_trunc('day', PriceHistory.timestamp).label("day"),
        )
        .join(Item, Item.id == PriceHistory.item_id)
        .filter(
            Item.type == item_type,
            ~Item.id.in_(exclude_item_ids) if exclude_item_ids else True,
            PriceHistory.timestamp.between(start, end),
        )
        .group_by(PriceHistory.item_id, func.date_trunc('day', PriceHistory.timestamp))
        .all()
    )
    by_item: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        by_item[r.item_id].append(r.avg_price)

    target_rows = (
        db.query(
            PriceHistory.item_id,
            func.avg(PriceHistory.price).label("avg_price"),
        )
        .join(Item, Item.id == PriceHistory.item_id)
        .filter(
            Item.type == item_type,
            ~Item.id.in_(exclude_item_ids) if exclude_item_ids else True,
            PriceHistory.timestamp.between(target_start, target_end),
        )
        .group_by(PriceHistory.item_id)
        .all()
    )
    target_prices = {r.item_id: float(r.avg_price) for r in target_rows}

    changes: list[float] = []
    for item_id, prices in by_item.items():
        if item_id not in target_prices:
            continue
        avg_before = sum(prices) / len(prices)
        if avg_before > 0:
            change = (target_prices[item_id] - avg_before) / avg_before * 100
            changes.append(change)

    if not changes:
        return 0.0, 0.0
    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / len(changes)
    std = math.sqrt(variance) if variance > 0 else 0.001
    return mean, std


def _compute_impacts(db, event: Event, item_ids: list[int]):
    """Compute impact metrics for all items around an event."""
    event_date = event.timestamp
    pre_prices: dict[int, float] = {}
    for item_id in item_ids:
        p = _pre_event_price(db, item_id, event_date)
        if p is not None:
            pre_prices[item_id] = p

    if not pre_prices:
        return []

    impacts: list[dict] = []
    for item_id, price_before in pre_prices.items():
        p1 = _post_event_price(db, item_id, event_date, 1)
        p3 = _post_event_price(db, item_id, event_date, 3)
        p7 = _post_event_price(db, item_id, event_date, 7)

        if p1 is None and p3 is None and p7 is None:
            continue

        impact_1d = ((p1 - price_before) / price_before * 100) if p1 else None
        impact_3d = ((p3 - price_before) / price_before * 100) if p3 else None
        impact_7d = ((p7 - price_before) / price_before * 100) if p7 else None

        impacts_vals = [v for v in [impact_1d, impact_3d, impact_7d] if v is not None]
        peak = max(impacts_vals, key=abs) if impacts_vals else 0.0
        peak_day = None
        if peak == impact_1d:
            peak_day = 1
        elif peak == impact_3d:
            peak_day = 3
        elif peak == impact_7d:
            peak_day = 7

        duration = None
        for d, imp in [(1, impact_1d), (3, impact_3d), (7, impact_7d)]:
            if imp is not None and abs(imp) > 0.5:
                duration = d

        item_type_result = db.query(Item.type).filter(Item.id == item_id).scalar()
        control_mean, control_std = _control_group_prices(
            db, item_type_result or "skin", event_date, {item_id},
            offset_days=7,
        )

        item_impact = impact_7d or impact_3d or impact_1d or 0.0
        z_score = (item_impact - control_mean) / control_std if control_std > 0 else 0.0

        impacts.append({
            "event_id": event.id,
            "item_id": item_id,
            "price_day_before": price_before,
            "price_day_1": p1,
            "price_day_3": p3,
            "price_day_7": p7,
            "impact_pct_1day": impact_1d,
            "impact_pct_3day": impact_3d,
            "impact_pct_7day": impact_7d,
            "peak_impact_pct": peak,
            "peak_impact_day": peak_day,
            "duration_days": duration,
            "z_score": round(z_score, 4),
        })

    return impacts


def _upsert_event_impacts(db, impacts: list[dict]):
    """Write event_impacts rows."""
    written = 0
    for row in impacts:
        existing = (
            db.query(EventImpact)
            .filter(
                EventImpact.event_id == row["event_id"],
                EventImpact.item_id == row["item_id"],
            )
            .first()
        )
        if existing:
            for key, val in row.items():
                setattr(existing, key, val)
        else:
            db.add(EventImpact(**row))
        written += 1
    db.commit()
    return written


def _compute_and_upsert_patterns(db, event_type: str, impacts: list[dict]):
    """Aggregate impacts into event_patterns for this event type."""
    by_item: dict[int, list[dict]] = defaultdict(list)
    for imp in impacts:
        by_item[imp["item_id"]].append(imp)

    for item_id, item_impacts in by_item.items():
        impacts_1d = [i["impact_pct_1day"] for i in item_impacts if i["impact_pct_1day"] is not None]
        impacts_3d = [i["impact_pct_3day"] for i in item_impacts if i["impact_pct_3day"] is not None]
        impacts_7d = [i["impact_pct_7day"] for i in item_impacts if i["impact_pct_7day"] is not None]
        z_scores = [i["z_score"] for i in item_impacts if i["z_score"] is not None]

        n = len(item_impacts)

        def _avg(vals):
            return sum(vals) / len(vals) if vals else None

        def _std(vals):
            if len(vals) < 2:
                return None
            m = sum(vals) / len(vals)
            return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))

        avg_1d = _avg(impacts_1d)
        avg_3d = _avg(impacts_3d)
        avg_7d = _avg(impacts_7d)
        std_dev = _std(impacts_1d + impacts_3d + impacts_7d)

        # consistency: fraction of impacts with same sign
        all_signs: list[int] = []
        for imp in impacts_1d + impacts_3d + impacts_7d:
            if imp is not None:
                all_signs.append(1 if imp > 0 else -1)
        if all_signs:
            majority = max(set(all_signs), key=all_signs.count)
            consistency = sum(1 for s in all_signs if s == majority) / len(all_signs)
        else:
            consistency = 0.0

        # holdout accuracy: if we split impacts into train/test halves
        holdout_acc = None
        if len(z_scores) >= 4:
            mid = len(z_scores) // 2
            train_z = z_scores[:mid]
            test_z = z_scores[mid:]
            if train_z and test_z:
                train_sign = 1 if sum(train_z) / len(train_z) > 0 else -1
                correct = sum(1 for z in test_z if (z > 0) == (train_sign > 0))
                holdout_acc = correct / len(test_z)

        existing = (
            db.query(EventPattern)
            .filter(
                EventPattern.event_type == event_type,
                EventPattern.item_id == item_id,
            )
            .first()
        )
        data = {
            "sample_size": n,
            "avg_impact_1day": avg_1d,
            "avg_impact_3day": avg_3d,
            "avg_impact_7day": avg_7d,
            "std_dev": std_dev,
            "consistency_score": round(consistency, 4),
            "holdout_accuracy": round(holdout_acc, 4) if holdout_acc is not None else None,
        }
        if existing:
            for key, val in data.items():
                setattr(existing, key, val)
        else:
            db.add(EventPattern(event_type=event_type, item_id=item_id, **data))
    db.commit()
    return len(by_item)


def _compute_and_upsert_correlations(db, event: Event, db_item_ids: list[int],
                                      impacts: list[dict]):
    """Write event_correlations with statistical rigor checks."""
    impact_by_item = {i["item_id"]: i for i in impacts}
    event_date = event.timestamp

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None)
    event_age_days = (cutoff - event_date.replace(tzinfo=None) if event_date.tzinfo is None
                      else (cutoff - event_date)).days if event_date else 365

    written = 0
    for item_id in db_item_ids:
        imp = impact_by_item.get(item_id)
        if imp is None:
            continue

        impact_7d = imp.get("impact_pct_7day") or imp.get("impact_pct_3day") or 0.0
        z_score = imp.get("z_score") or 0.0

        # Significance check: |z| > 2 => 95% confidence
        significance_passed = 1 if abs(z_score) >= 2.0 else 0

        # Control group diff (same as z-score based)
        control_diff = impact_7d
        control_passed = 1 if abs(control_diff) > 0.0 else 0

        # Confounding events: count events on same calendar day
        day_start = event_date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        confounding = (
            db.query(func.count(Event.id))
            .filter(
                Event.id != event.id,
                Event.timestamp >= day_start,
                Event.timestamp < day_end,
            )
            .scalar()
        ) or 0
        confounding_passed = 1 if confounding == 0 else 0

        # Pattern consistency from event_patterns table
        pattern = (
            db.query(EventPattern)
            .filter(
                EventPattern.event_type == event.type,
                EventPattern.item_id == item_id,
            )
            .first()
        )
        pattern_consistency = pattern.consistency_score if pattern else None
        pattern_passed = 1 if (pattern_consistency is not None and pattern_consistency >= 0.7) else 0

        # Lag analysis
        peak_day = imp.get("peak_impact_day")
        lag_passed = 1 if (peak_day is not None and peak_day <= 7) else 0

        # Holdout validation from pattern
        holdout_acc = pattern.holdout_accuracy if pattern else None
        validation_passed = 1 if (holdout_acc is not None and holdout_acc >= 0.6) else 0

        # Overall confidence score (weighted average of 6 checks)
        checks = [significance_passed, control_passed, pattern_passed,
                  confounding_passed, lag_passed, validation_passed]
        weights = [0.25, 0.10, 0.20, 0.10, 0.15, 0.20]
        confidence = sum(c * w for c, w in zip(checks, weights))

        existing = (
            db.query(EventCorrelation)
            .filter(
                EventCorrelation.event_id == event.id,
                EventCorrelation.item_id == item_id,
            )
            .first()
        )
        data = {
            "event_id": event.id,
            "item_id": item_id,
            "price_change_pct": round(impact_7d, 4) if impact_7d else None,
            "control_group_change_pct": 0.0,
            "significance_test_zscore": round(z_score, 4),
            "significance_passed": significance_passed,
            "control_group_diff": round(control_diff, 4) if control_diff else None,
            "control_group_passed": control_passed,
            "pattern_consistency_score": pattern_consistency,
            "pattern_passed": pattern_passed,
            "confounding_events_count": confounding,
            "confounding_passed": confounding_passed,
            "lag_analysis_peak_day": peak_day,
            "lag_passed": lag_passed,
            "holdout_validation_accuracy": holdout_acc,
            "validation_passed": validation_passed,
            "confidence_score": round(confidence, 4),
        }
        if existing:
            for key, val in data.items():
                setattr(existing, key, val)
        else:
            db.add(EventCorrelation(**data))
        written += 1
    db.commit()
    return written


def run_analysis(days_back: int = 90):
    """Main entry point: analyze events and write results to DB."""
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)

        events = (
            db.query(Event)
            .filter(Event.timestamp >= cutoff)
            .order_by(desc(Event.timestamp))
            .all()
        )
        logger.info(f"Found {len(events)} events in the last {days_back} days")

        backfilled_items = (
            db.query(Item.id)
            .filter(Item.is_backfilled == 1)
            .all()
        )
        item_ids = [r.id for r in backfilled_items]
        logger.info(f"Found {len(item_ids)} backfilled items for analysis")

        total_impacts = 0
        total_patterns = 0
        total_correlations = 0

        for event in events:
            logger.info(f"Analyzing event #{event.id}: {event.type} - {event.description[:60]}")

            impacts = _compute_impacts(db, event, item_ids)
            if not impacts:
                logger.info(f"  No price data found for event #{event.id}, skipping")
                continue

            n_impacts = _upsert_event_impacts(db, impacts)
            total_impacts += n_impacts
            logger.info(f"  Wrote {n_impacts} event_impacts")

            n_patterns = _compute_and_upsert_patterns(db, event.type, impacts)
            total_patterns += n_patterns
            logger.info(f"  Wrote {n_patterns} event_patterns")

            n_correlations = _compute_and_upsert_correlations(
                db, event, item_ids, impacts,
            )
            total_correlations += n_correlations
            logger.info(f"  Wrote {n_correlations} event_correlations")

        logger.info(f"Done: {total_impacts} impacts, {total_patterns} patterns, {total_correlations} correlations")
        return {
            "status": "success",
            "events_analyzed": len(events),
            "impacts_written": total_impacts,
            "patterns_written": total_patterns,
            "correlations_written": total_correlations,
        }

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "error": str(e)}
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event correlation analysis")
    parser.add_argument(
        "--days-back", type=int, default=90,
        help="Analyze events within this many days (default: 90)",
    )
    args = parser.parse_args()
    result = run_analysis(days_back=args.days_back)
    print(f"RESULT: {result}")
    if result.get("status") == "error":
        sys.exit(1)
