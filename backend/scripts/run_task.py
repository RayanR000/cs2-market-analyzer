#!/usr/bin/env python3
"""
Task runner for automated maintenance and collection.
Used by GitHub Actions to trigger specific pipeline tasks.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from collectors.pipeline import DataPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("task_runner")

def run_task(task_name):
    db = SessionLocal()
    pipeline = DataPipeline(db_session=db)

    try:
        start_time = datetime.now()

        if task_name == "aggregate":
            logger.info("="*60)
            logger.info("TASK: Full Aggregator Scrape (All 17k items)")
            logger.info("="*60)
            result = pipeline.run_full_aggregator_collection()

            if isinstance(result, dict):
                logger.info(f"✅ SUCCESS - Items collected: {result.get('items_collected', 'N/A')}")
                logger.info(f"  Errors: {result.get('errors', 0)}")
                logger.info(f"  Duration: {result.get('duration_seconds', 'N/A')}s")

            print(f"RESULT: {result}")

        elif task_name == "priority":
            logger.info("="*60)
            logger.info("TASK: Priority Aggregator Scrape (Top 2000)")
            logger.info("="*60)
            result = pipeline.run_priority_collection()
            print(f"RESULT: {result}")

        elif task_name == "prune":
            logger.info("="*60)
            logger.info("TASK: Database Pruning & Downsampling")
            logger.info("="*60)
            result = pipeline.run_database_pruning()

            if isinstance(result, dict):
                logger.info(f"✅ SUCCESS - Records pruned: {result.get('records_pruned', 'N/A')}")
                logger.info(f"  Duration: {result.get('duration_seconds', 'N/A')}s")

            print(f"RESULT: {result}")

        elif task_name == "trends":
            logger.info("="*60)
            logger.info("TASK: Trend Analysis & Opportunity Detection (90-day)")
            logger.info("="*60)
            result = pipeline.run_feature_computation()
            result2 = pipeline.run_trend_analysis()
            print(f"RESULT: {result}, {result2}")

        elif task_name == "long_term_trends":
            logger.info("="*60)
            logger.info("TASK: Long-Term Trend Analysis (Full History)")
            logger.info("="*60)
            from scripts.long_term_trend_analyzer import LongTermTrendAnalyzer
            analyzer = LongTermTrendAnalyzer(db_session=db)
            result = analyzer.run_analysis()
            print(f"RESULT: {result}")

        else:
            logger.error(f"Unknown task: {task_name}")
            sys.exit(1)

        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Total task time: {elapsed:.1f} seconds")

    except Exception as e:
        logger.error(f"❌ TASK FAILED: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_task.py <task_name>")
        print("Tasks: aggregate, priority, prune, trends")
        sys.exit(1)
        
    run_task(sys.argv[1])
