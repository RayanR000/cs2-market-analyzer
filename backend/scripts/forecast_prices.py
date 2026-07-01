#!/usr/bin/env python3
"""
Generate ML-based price forecasts for all CS2 items using LightGBM.
Trains quantile regression models (7d and 30d horizons) and writes
forecasts to the item_forecasts table.

Usage:
    python scripts/forecast_prices.py          # train + predict
    python scripts/forecast_prices.py --predict-only  # skip training, use saved models
    python scripts/forecast_prices.py --train-only     # train models only, skip forecasts
"""

import sys
import math
import logging
from pathlib import Path
from datetime import datetime, date, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, ItemForecast, Item
from models.forecaster import ItemForecaster
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("forecast_prices")

MODEL_VERSION = "lgbm-v1"


def run_forecast(train_only: bool = False, predict_only: bool = False):
    db = SessionLocal()
    try:
        forecaster = ItemForecaster(db_session=db)
        has_models = forecaster.load_models()

        if not predict_only:
            if has_models:
                logger.info("Saved models found, retraining...")
            else:
                logger.info("No saved models found, training from scratch...")
            forecaster.train(max_rows=200_000)
            has_models = True

        if train_only:
            logger.info("Train-only mode, skipping forecast generation.")
            return {"status": "success", "mode": "train_only"}

        if not has_models:
            logger.error("No models available for prediction.")
            return {"status": "error", "message": "No trained models"}

        results = forecaster.predict()

        if results.empty:
            logger.warning("No forecast results generated.")
            return {"status": "empty", "forecast_count": 0}

        # Write forecasts to DB
        today = date.today()
        forecast_rows = []
        for _, row in results.iterrows():
            item_id = int(row["item_id"])
            current_price = row.get("current_price")
            forecasts = row.get("forecasts", {})

            for horizon, fcast in forecasts.items():
                forecast_rows.append({
                    "item_id": item_id,
                    "forecast_date": today,
                    "horizon_days": horizon,
                    "price_low": fcast.get("low"),
                    "price_mid": fcast.get("mid"),
                    "price_high": fcast.get("high"),
                    "current_price": current_price,
                    "direction": fcast.get("direction"),
                    "confidence": fcast.get("confidence"),
                    "model_version": MODEL_VERSION,
                    "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
                })

        # Bulk upsert in batches
        if forecast_rows:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy.dialects.sqlite import insert as sqlite_insert

            bind = db.get_bind()
            dialect_name = bind.dialect.name if bind is not None else "sqlite"
            insert_stmt = sqlite_insert if dialect_name == "sqlite" else pg_insert
            table = ItemForecast.__table__

            batch_size = 5000
            for i in range(0, len(forecast_rows), batch_size):
                batch = forecast_rows[i:i + batch_size]
                stmt = insert_stmt(table).values(batch)
                excluded = stmt.excluded
                update_cols = {
                    col.name: getattr(excluded, col.name)
                    for col in table.columns
                    if col.name not in {"id", "item_id", "forecast_date", "horizon_days", "created_at"}
                }
                stmt = stmt.on_conflict_do_update(
                    index_elements=["item_id", "forecast_date", "horizon_days"],
                    set_=update_cols,
                )
                db.execute(stmt)
                db.commit()

        logger.info(f"✅ Wrote {len(forecast_rows)} forecasts to item_forecasts table")
        return {
            "status": "success",
            "items": len(results),
            "forecasts": len(forecast_rows),
            "model_version": MODEL_VERSION,
        }

    except Exception as e:
        logger.error(f"❌ Forecast failed: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "message": str(e)}

    finally:
        db.close()


def main():
    args = set(sys.argv[1:])
    train_only = "--train-only" in args
    predict_only = "--predict-only" in args

    result = run_forecast(train_only=train_only, predict_only=predict_only)
    print(f"RESULT: {result}")
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
