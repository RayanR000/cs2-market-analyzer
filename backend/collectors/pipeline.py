"""
Data pipeline orchestration
Manages scheduled data collection, validation, and storage
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

class DataPipeline:
    """Orchestrates data collection and processing pipeline"""
    
    def __init__(self, db_session=None):
        """
        Initialize data pipeline
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False
    
    def start(self, scheduler: Optional[BackgroundScheduler] = None):
        """
        Start the data pipeline scheduler
        
        Args:
            scheduler: Optional BackgroundScheduler instance to use
        """
        if self.is_running:
            logger.warning("Data pipeline already running")
            return
        
        try:
            self.scheduler = scheduler or BackgroundScheduler()
            
            # Schedule daily data collection at 1 AM UTC
            self.scheduler.add_job(
                self.run_daily_collection,
                CronTrigger(hour=1, minute=0),
                id='daily_collection',
                name='Daily market data collection',
                replace_existing=True
            )
            
            # Schedule hourly feature computation at :00
            self.scheduler.add_job(
                self.run_feature_computation,
                CronTrigger(minute=0),
                id='hourly_features',
                name='Hourly feature computation',
                replace_existing=True
            )
            
            # Schedule daily trend analysis at 2 AM UTC
            self.scheduler.add_job(
                self.run_trend_analysis,
                CronTrigger(hour=2, minute=0),
                id='daily_trends',
                name='Daily trend analysis',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("Data pipeline started successfully")
            
        except Exception as e:
            logger.error(f"Error starting data pipeline: {e}")
            raise
    
    def stop(self):
        """Stop the data pipeline scheduler"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Data pipeline stopped")
    
    def run_daily_collection(self):
        """Execute daily market data collection"""
        try:
            logger.info("Starting daily market data collection")
            
            # Import here to avoid circular dependencies
            from collectors.steam_market import SteamMarketCollector
            from collectors.data_validation import DataValidator, DataCleaner
            
            collector = SteamMarketCollector()
            validator = DataValidator()
            cleaner = DataCleaner()
            
            # TODO: Implement actual collection logic
            # This would:
            # 1. Fetch market listings from Steam
            # 2. For each item, collect price and volume
            # 3. Validate data
            # 4. Store in database
            
            logger.info("Daily market data collection completed")
            return {"status": "success", "timestamp": datetime.utcnow()}
            
        except Exception as e:
            logger.error(f"Error in daily collection: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}
    
    def run_feature_computation(self):
        """Execute feature computation for trend analysis"""
        try:
            logger.info("Starting feature computation")
            
            # TODO: Implement feature computation
            # This would:
            # 1. Load recent price history for all items
            # 2. Compute moving averages (7-day, 30-day)
            # 3. Compute volatility
            # 4. Store computed features
            
            logger.info("Feature computation completed")
            return {"status": "success", "timestamp": datetime.utcnow()}
            
        except Exception as e:
            logger.error(f"Error in feature computation: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}
    
    def run_trend_analysis(self):
        """Execute trend scoring and opportunity detection"""
        try:
            logger.info("Starting trend analysis")
            
            # TODO: Implement trend analysis
            # This would:
            # 1. Load features for all items
            # 2. Compute trend scores
            # 3. Detect opportunities
            # 4. Update trend indicators in database
            
            logger.info("Trend analysis completed")
            return {"status": "success", "timestamp": datetime.utcnow()}
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}
    
    def get_scheduled_jobs(self) -> List[Dict]:
        """Get list of scheduled jobs"""
        if not self.scheduler:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'trigger': str(job.trigger),
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
            })
        return jobs


class PipelineMonitor:
    """Monitors pipeline health and performance"""
    
    def __init__(self):
        """Initialize pipeline monitor"""
        self.collection_stats = {
            'last_run': None,
            'last_success': None,
            'last_error': None,
            'total_runs': 0,
            'total_failures': 0,
            'items_collected': 0
        }
        self.feature_stats = {
            'last_run': None,
            'last_success': None,
            'items_processed': 0,
            'total_features_computed': 0
        }
    
    def record_collection_run(self, success: bool, items_count: int = 0, error: Optional[str] = None):
        """Record a collection run"""
        self.collection_stats['last_run'] = datetime.utcnow()
        self.collection_stats['total_runs'] += 1
        
        if success:
            self.collection_stats['last_success'] = datetime.utcnow()
            self.collection_stats['items_collected'] += items_count
        else:
            self.collection_stats['total_failures'] += 1
            self.collection_stats['last_error'] = error
    
    def get_collection_health(self) -> Dict:
        """Get collection pipeline health status"""
        if self.collection_stats['total_runs'] == 0:
            return {'status': 'never_run'}
        
        success_rate = (self.collection_stats['total_runs'] - self.collection_stats['total_failures']) / self.collection_stats['total_runs']
        
        return {
            'status': 'healthy' if success_rate > 0.9 else 'degraded' if success_rate > 0.5 else 'unhealthy',
            'success_rate': success_rate,
            **self.collection_stats
        }
    
    def get_stats(self) -> Dict:
        """Get all pipeline statistics"""
        return {
            'collection': self.get_collection_health(),
            'features': self.feature_stats
        }
