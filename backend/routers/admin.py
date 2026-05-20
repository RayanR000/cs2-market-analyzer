"""
Admin endpoints for data collection management
"""

from fastapi import APIRouter
from sqlalchemy import func, distinct
from typing import Optional
from collectors.real_data_collector import get_collector
from collectors.free_data_importer import FreeDataBackfillImporter
from config import settings
from database import SessionLocal, Item, PriceHistory, CollectionRun

router = APIRouter(prefix="/admin", tags=["admin"])


def _serialize_collection_run(run: Optional[CollectionRun]) -> Optional[dict]:
    """Convert a persisted collection run into a JSON-friendly payload."""
    if run is None:
        return None

    return {
        "id": run.id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status,
        "total_items": run.total_items,
        "successful": run.successful,
        "failed": run.failed,
        "duration_seconds": run.duration_seconds,
        "error_message": run.error_message,
        "source_breakdown": run.source_breakdown or {},
    }


def _build_coverage_report(db: SessionLocal) -> dict:
    """Summarize which tracked items have at least one price record per source."""
    total_items = db.query(Item).count()

    source_coverage_rows = db.query(
        PriceHistory.source,
        func.count(distinct(PriceHistory.item_id))
    ).group_by(PriceHistory.source).all()

    covered_item_ids = db.query(distinct(PriceHistory.item_id)).all()
    covered_item_id_set = {row[0] for row in covered_item_ids}
    covered_items = db.query(Item).filter(Item.id.in_(covered_item_id_set)).all() if covered_item_id_set else []
    covered_item_names = sorted({item.name for item in covered_items})

    uncovered_items = db.query(Item).filter(~Item.id.in_(covered_item_id_set)).all() if covered_item_id_set else db.query(Item).all()
    uncovered_item_names = sorted(item.name for item in uncovered_items)

    per_item_source_rows = db.query(
        Item.name,
        PriceHistory.source
    ).join(PriceHistory, PriceHistory.item_id == Item.id).distinct().all()

    per_item_sources = {}
    for item_name, source in per_item_source_rows:
        per_item_sources.setdefault(item_name, []).append(source)

    for sources in per_item_sources.values():
        sources.sort()

    return {
        "total_items": total_items,
        "covered_items": len(covered_item_names),
        "coverage_ratio": round(len(covered_item_names) / total_items, 4) if total_items else 0,
        "source_coverage": {
            source: count for source, count in source_coverage_rows
        },
        "covered_item_names": covered_item_names,
        "uncovered_item_names": uncovered_item_names,
        "per_item_sources": per_item_sources,
    }

@router.post("/collect-now")
async def trigger_collection():
    """Manually trigger data collection immediately"""
    collector = get_collector()
    stats = collector.collect_all_items()
    
    return {
        "status": "completed",
        "stats": stats,
        "metrics": collector.get_collection_metrics()
    }


@router.post("/import-free-history")
async def import_free_history():
    """Backfill free historical market data and official events."""
    importer = FreeDataBackfillImporter(api_key=settings.cs2sh_api_key)
    db = SessionLocal()
    try:
        stats = importer.run_full_import(db=db)
        return {
            "status": "completed",
            "stats": stats,
        }
    finally:
        db.close()


@router.post("/import-official-events")
async def import_official_events():
    """Import only official Steam announcement events."""
    importer = FreeDataBackfillImporter(api_key=settings.cs2sh_api_key)
    db = SessionLocal()
    try:
        stats = importer.import_official_events(db=db)
        return {
            "status": "completed",
            "stats": stats,
        }
    finally:
        db.close()

@router.get("/collection-status")
async def get_collection_status():
    """Get current data collection status"""
    collector = get_collector()
    
    # Get latest price collection timestamp
    db = SessionLocal()
    try:
        latest_price = db.query(PriceHistory).order_by(
            PriceHistory.timestamp.desc()
        ).first()
        latest_run = db.query(CollectionRun).order_by(
            CollectionRun.started_at.desc()
        ).first()
        
        latest_timestamp = latest_price.timestamp if latest_price else None
        total_records = db.query(PriceHistory).count()
        metrics = collector.get_collection_metrics()
        
        return {
            "collection_enabled": collector.enabled,
            "is_running": collector.is_running,
            "thread_alive": metrics.get("thread_alive", False),
            "latest_collection": latest_timestamp,
            "latest_persisted_run": _serialize_collection_run(latest_run),
            "total_price_records": total_records,
            "environment": settings.environment,
            "synthetic_history_enabled": settings.demo_bootstrap_enabled(),
            "status": metrics.get("status", "inactive"),
            "metrics": metrics
        }
    finally:
        db.close()

@router.get("/data-stats")
async def get_data_statistics():
    """Get database data statistics"""
    db = SessionLocal()
    try:
        total_items = db.query(Item).count()
        total_prices = db.query(PriceHistory).count()
        total_runs = db.query(CollectionRun).count()
        collector = get_collector()
        metrics = collector.get_collection_metrics()
        source_rows = db.query(
            PriceHistory.source,
            func.count(PriceHistory.id)
        ).group_by(PriceHistory.source).all()
        coverage = _build_coverage_report(db)
        
        # Get price range
        all_prices = db.query(PriceHistory).all()
        if all_prices:
            prices = [p.price for p in all_prices]
            min_price = min(prices)
            max_price = max(prices)
            avg_price = sum(prices) / len(prices)
        else:
            min_price = max_price = avg_price = 0
        
        return {
            "total_items": total_items,
            "total_price_records": total_prices,
            "total_collection_runs": total_runs,
            "collector": metrics,
            "source_breakdown": {
                source: count for source, count in source_rows
            },
            "coverage": coverage,
            "price_statistics": {
                "min": round(min_price, 2),
                "max": round(max_price, 2),
                "average": round(avg_price, 2),
                "count": total_prices
            }
        }
    finally:
        db.close()

@router.get("/coverage-report")
async def get_coverage_report():
    """Get item-level source coverage for the tracked catalog."""
    db = SessionLocal()
    try:
        return _build_coverage_report(db)
    finally:
        db.close()


@router.get("/verification-status")
async def get_verification_status():
    """Get a compact operational summary for dashboard verification."""
    collector = get_collector()
    db = SessionLocal()
    try:
        coverage = _build_coverage_report(db)
        total_items = db.query(Item).count()
        total_price_records = db.query(PriceHistory).count()
        metrics = collector.get_collection_metrics()

        return {
            "collection_enabled": collector.enabled,
            "collection_status": metrics.get("status", "inactive"),
            "last_success_at": metrics.get("last_success_at").isoformat()
            if metrics.get("last_success_at")
            else None,
            "last_error_at": metrics.get("last_error_at").isoformat()
            if metrics.get("last_error_at")
            else None,
            "last_error": metrics.get("last_error"),
            "total_items": total_items,
            "total_price_records": total_price_records,
            "source_breakdown": metrics.get("source_breakdown", {}),
            "coverage": coverage,
            "synthetic_history_enabled": settings.demo_bootstrap_enabled(),
        }
    finally:
        db.close()
