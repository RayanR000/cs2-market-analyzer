"""
Accuracy metrics API — serves backtest results and per-forecast outcomes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import date

from database import get_db, PredictionAccuracy, ForecastOutcome

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


def _row_to_dict(row: PredictionAccuracy) -> dict:
    return {
        "id": row.id,
        "prediction_type": row.prediction_type,
        "evaluation_date": row.evaluation_date.isoformat() if row.evaluation_date else None,
        "horizon_days": row.horizon_days,
        "model_version": row.model_version,
        "evaluation_window_days": row.evaluation_window_days,
        "sample_count": row.sample_count,
        "metrics": row.metrics,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/")
def list_accuracy(
    prediction_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(PredictionAccuracy).order_by(desc(PredictionAccuracy.evaluation_date))
    if prediction_type:
        q = q.filter(PredictionAccuracy.prediction_type == prediction_type)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]


@router.get("/latest")
def get_latest_accuracy(
    prediction_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get the most recent accuracy record for each prediction type."""
    rows = db.query(PredictionAccuracy).order_by(
        PredictionAccuracy.prediction_type,
        desc(PredictionAccuracy.evaluation_date),
    ).all()

    latest = {}
    for r in rows:
        key = r.prediction_type
        if key not in latest:
            latest[key] = _row_to_dict(r)

    if prediction_type:
        return latest.get(prediction_type)

    return latest


@router.get("/summary")
def get_accuracy_summary(
    prediction_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Returns aggregated summary across all available accuracy records."""
    q = db.query(PredictionAccuracy)
    if prediction_type:
        q = q.filter(PredictionAccuracy.prediction_type == prediction_type)

    rows = q.order_by(PredictionAccuracy.evaluation_date).all()

    summary = {}
    for r in rows:
        key = f"{r.prediction_type}"

        # Group forecast by horizon also
        if r.prediction_type == "forecast" and r.horizon_days:
            gh_key = f"{key}_{r.horizon_days}d"
        elif r.prediction_type == "trend_direction" and r.evaluation_window_days:
            gh_key = f"{key}_{r.evaluation_window_days}d"
        elif r.prediction_type == "opportunity" and r.evaluation_window_days:
            gh_key = f"{key}_{r.evaluation_window_days}d"
        else:
            gh_key = key

        if gh_key not in summary:
            summary[gh_key] = {
                "prediction_type": r.prediction_type,
                "horizon_days": r.horizon_days,
                "evaluation_window_days": r.evaluation_window_days,
                "records": [],
            }
        summary[gh_key]["records"].append(_row_to_dict(r))

    # Return as list sorted by type
    result = sorted(summary.values(), key=lambda x: x["prediction_type"])
    return result


# ---------------------------------------------------------------------------
# Per-forecast outcomes
# ---------------------------------------------------------------------------

def _outcome_to_dict(o: ForecastOutcome) -> dict:
    return {
        "id": o.id,
        "forecast_id": o.forecast_id,
        "item_id": o.item_id,
        "forecast_date": o.forecast_date.isoformat() if o.forecast_date else None,
        "horizon_days": o.horizon_days,
        "target_date": o.target_date.isoformat() if o.target_date else None,
        "current_price": o.current_price,
        "predicted_price_mid": o.predicted_price_mid,
        "actual_price": o.actual_price,
        "direction_predicted": o.direction_predicted,
        "direction_actual": o.direction_actual,
        "direction_correct": bool(o.direction_correct),
        "in_interval": bool(o.in_interval) if o.in_interval is not None else None,
        "abs_error": o.abs_error,
        "pct_error": o.pct_error,
        "model_version": o.model_version,
        "evaluated_at": o.evaluated_at.isoformat() if o.evaluated_at else None,
    }


@router.get("/outcomes")
def list_outcomes(
    item_id: Optional[int] = Query(None),
    horizon_days: Optional[int] = Query(None),
    correct: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Query individual forecast outcomes — was each prediction right or wrong?"""
    q = db.query(ForecastOutcome).order_by(desc(ForecastOutcome.evaluated_at))
    if item_id is not None:
        q = q.filter(ForecastOutcome.item_id == item_id)
    if horizon_days is not None:
        q = q.filter(ForecastOutcome.horizon_days == horizon_days)
    if correct is not None:
        q = q.filter(ForecastOutcome.direction_correct == (1 if correct else 0))
    rows = q.limit(limit).all()
    return [_outcome_to_dict(r) for r in rows]


@router.get("/outcomes/stats")
def outcome_stats(
    db: Session = Depends(get_db),
):
    """Aggregated stats from forecast outcomes — accuracy, error distribution."""
    from sqlalchemy import func

    total = db.query(func.count(ForecastOutcome.id)).scalar() or 0
    if total == 0:
        return {"total_outcomes": 0}

    correct = db.query(func.count(ForecastOutcome.id)).filter(
        ForecastOutcome.direction_correct == 1
    ).scalar() or 0

    avg_error = db.query(func.avg(ForecastOutcome.abs_error)).scalar() or 0
    avg_pct = db.query(func.avg(ForecastOutcome.pct_error)).scalar() or 0

    # Per-horizon breakdown
    from sqlalchemy import text
    per_horizon = db.execute(text("""
        SELECT horizon_days,
               COUNT(*) AS total,
               SUM(direction_correct) AS correct,
               ROUND(AVG(abs_error), 4) AS avg_abs_error,
               ROUND(AVG(pct_error), 2) AS avg_pct_error
        FROM forecast_outcomes
        GROUP BY horizon_days
        ORDER BY horizon_days
    """)).fetchall()

    return {
        "total_outcomes": total,
        "overall_accuracy": round(correct / total * 100, 2) if total > 0 else 0,
        "mean_abs_error": round(avg_error, 4),
        "mean_pct_error": round(avg_pct, 2),
        "per_horizon": [
            {
                "horizon_days": r.horizon_days,
                "total": r.total,
                "correct": r.correct,
                "accuracy": round(r.correct / r.total * 100, 2) if r.total > 0 else 0,
                "avg_abs_error": r.avg_abs_error,
                "avg_pct_error": r.avg_pct_error,
            }
            for r in per_horizon
        ],
    }
