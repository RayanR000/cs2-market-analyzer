"""
A/B test results API — serves regime-switching vs global-only comparison data.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date

from database import get_db, PredictionAccuracy

router = APIRouter(prefix="/ab-test", tags=["ab_test"])


def _row_to_dict(row: PredictionAccuracy) -> dict:
    return {
        "id": row.id,
        "prediction_type": row.prediction_type,
        "evaluation_date": row.evaluation_date.isoformat() if row.evaluation_date else None,
        "horizon_days": row.horizon_days,
        "model_version": row.model_version,
        "sample_count": row.sample_count,
        "metrics": row.metrics,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/regime")
def get_regime_ab_test(
    db = Depends(get_db),
):
    """Return the latest A/B test comparison between regime and global-only models."""
    from sqlalchemy import text

    # Get the latest evaluation date for ab_test_regime_delta records
    latest_date = db.execute(text("""
        SELECT MAX(evaluation_date)
        FROM prediction_accuracy
        WHERE prediction_type = 'ab_test_regime_delta'
    """)).scalar()

    if not latest_date:
        return {"status": "no_data", "message": "No A/B test results found. Run `python scripts/ab_test_regime.py` first."}

    # Fetch regime metrics
    regime_rows = db.execute(text("""
        SELECT horizon_days, sample_count, metrics
        FROM prediction_accuracy
        WHERE prediction_type = 'ab_test_regime'
          AND model_version = 'lgbm-v3-regime'
          AND evaluation_date = :d
        ORDER BY horizon_days
    """), {"d": latest_date}).fetchall()

    # Fetch global-only metrics
    global_rows = db.execute(text("""
        SELECT horizon_days, sample_count, metrics
        FROM prediction_accuracy
        WHERE prediction_type = 'ab_test_regime'
          AND model_version = 'lgbm-v3-global-only'
          AND evaluation_date = :d
        ORDER BY horizon_days
    """), {"d": latest_date}).fetchall()

    # Fetch delta records
    delta_rows = db.execute(text("""
        SELECT horizon_days, metrics
        FROM prediction_accuracy
        WHERE prediction_type = 'ab_test_regime_delta'
          AND evaluation_date = :d
        ORDER BY horizon_days
    """), {"d": latest_date}).fetchall()

    regime_by_h = {r.horizon_days: r for r in regime_rows}
    global_by_h = {r.horizon_days: r for r in global_rows}
    delta_by_h = {r.horizon_days: r for r in delta_rows}

    horizons = []
    for h in sorted(set(list(regime_by_h.keys()) + list(global_by_h.keys()) + list(delta_by_h.keys()))):
        entry = {"horizon_days": h}
        if h in regime_by_h:
            r = regime_by_h[h]
            entry["regime"] = {"sample_count": r.sample_count, "metrics": r.metrics}
        if h in global_by_h:
            g = global_by_h[h]
            entry["global_only"] = {"sample_count": g.sample_count, "metrics": g.metrics}
        if h in delta_by_h:
            entry["delta"] = delta_by_h[h].metrics
        horizons.append(entry)

    return {
        "test_date": latest_date.isoformat() if latest_date else None,
        "horizons": horizons,
    }
