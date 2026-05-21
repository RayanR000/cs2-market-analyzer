import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.real_data_collector import get_collector
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("background_collect")

def run():
    logger.info("Starting background collection script")
    collector = get_collector()
    try:
        stats = collector.collect_all_items()
        logger.info(f"Collection complete: {stats}")
    except Exception as e:
        logger.error(f"Collection failed: {e}", exc_info=True)

if __name__ == "__main__":
    run()
