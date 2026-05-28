#!/usr/bin/env python3
"""
Long-term trend analyzer using full item history.
Analyzes trends from item release date (capped at 3 years).

Time window strategy:
- New items (60-365 days old): Use all data since release
- Mature items (365+ days old): Use last 3 years (most predictive)
- Skip very new items (< 60 days old)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from statistics import mean, stdev

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, Item, PriceHistory, TrendIndicator
from sqlalchemy import func

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("long_term_analyzer")


class LongTermTrendAnalyzer:
    def __init__(self, db_session):
        self.db = db_session
        self.analysis_date = datetime.utcnow()
        self.min_data_points = 7
        self.min_age_days = 60
        self.max_lookback_days = 365 * 3  # 3 years

    def get_item_age_days(self, item_id):
        """Get days since item was first seen in database."""
        first_price = self.db.query(func.min(PriceHistory.timestamp)).filter(
            PriceHistory.item_id == item_id
        ).scalar()

        if not first_price:
            return 0

        age = (self.analysis_date - first_price).days
        return age

    def get_item_price_history(self, item_id):
        """Fetch price history from release date (or 3yr cap)."""
        first_price_date = self.db.query(func.min(PriceHistory.timestamp)).filter(
            PriceHistory.item_id == item_id
        ).scalar()

        if not first_price_date:
            return []

        # Calculate lookback: use all data but cap at 3 years
        lookback_date = max(
            first_price_date,
            self.analysis_date - timedelta(days=self.max_lookback_days)
        )

        prices = self.db.query(PriceHistory).filter(
            PriceHistory.item_id == item_id,
            PriceHistory.timestamp >= lookback_date
        ).order_by(PriceHistory.timestamp).all()

        return [(p.timestamp, p.price) for p in prices]

    def calculate_moving_average(self, prices, days):
        """Calculate moving average for last N days."""
        if not prices or len(prices) < days:
            return None

        recent_prices = [p[1] for p in prices[-days:]]
        return mean(recent_prices)

    def calculate_momentum(self, prices, days):
        """Calculate % change over N days."""
        if not prices or len(prices) < days:
            return None

        old_price = prices[-days][1]
        new_price = prices[-1][1]

        if old_price == 0:
            return 0

        return ((new_price - old_price) / old_price) * 100

    def calculate_volatility(self, prices):
        """Calculate price volatility (standard deviation)."""
        if not prices or len(prices) < 2:
            return 0

        price_list = [p[1] for p in prices]
        try:
            return stdev(price_list)
        except:
            return 0

    def determine_trend(self, ma_7, ma_30):
        """Determine trend direction based on moving averages."""
        if ma_7 is None or ma_30 is None:
            return "neutral"

        if ma_7 > ma_30 * 1.02:
            return "bullish"
        elif ma_7 < ma_30 * 0.98:
            return "bearish"
        return "neutral"

    def calculate_momentum_score(self, momentum_7, momentum_30):
        """Score momentum strength (-100 to +100)."""
        if momentum_7 is None or momentum_30 is None:
            return 0

        avg_momentum = (momentum_7 + momentum_30) / 2
        return max(-100, min(100, avg_momentum))

    def calculate_opportunity_score(self, current_price, ma_30, momentum_score, volatility):
        """Score investment opportunity (-100 to +100)."""
        if ma_30 is None:
            return 0

        # Price deviation from 30-day MA
        deviation = ((current_price - ma_30) / ma_30) * 100

        # Combine momentum and deviation
        opportunity = (momentum_score * 0.6) + (deviation * 0.4)

        # Adjust for volatility (higher volatility = more risk)
        if volatility > 0:
            opportunity = opportunity / (1 + (volatility / 100))

        return max(-100, min(100, opportunity))

    def analyze_item(self, item_id):
        """Analyze a single item using full history."""
        try:
            # Check if item is old enough
            age_days = self.get_item_age_days(item_id)
            if age_days < self.min_age_days:
                return None

            prices = self.get_item_price_history(item_id)

            # Need at least minimum data points
            if not prices or len(prices) < self.min_data_points:
                return None

            current_price = prices[-1][1]

            # Calculate moving averages
            ma_7 = self.calculate_moving_average(prices, 7)
            ma_30 = self.calculate_moving_average(prices, 30)
            ma_90 = self.calculate_moving_average(prices, 90)

            # Calculate momentum
            momentum_7 = self.calculate_momentum(prices, 7)
            momentum_30 = self.calculate_momentum(prices, 30)
            volatility = self.calculate_volatility(prices)

            # Determine trend
            trend = self.determine_trend(ma_7, ma_30)
            momentum_score = self.calculate_momentum_score(momentum_7, momentum_30)
            opportunity_score = self.calculate_opportunity_score(
                current_price, ma_30, momentum_score, volatility
            )

            price_stability = max(0, 100 - volatility)

            return {
                'item_id': item_id,
                'analysis_date': self.analysis_date,
                'current_price': current_price,
                'ma_7day': ma_7,
                'ma_30day': ma_30,
                'ma_90day': ma_90,
                'momentum_7day': momentum_7,
                'momentum_30day': momentum_30,
                'volatility': volatility,
                'trend_direction': trend,
                'momentum_score': momentum_score,
                'opportunity_score': opportunity_score,
                'price_stability': price_stability,
                'data_points': len(prices),
                'age_days': age_days
            }

        except Exception as e:
            logger.warning(f"Error analyzing item {item_id}: {e}")
            return None

    def run_analysis(self):
        """Run analysis for all eligible items."""
        logger.info("=" * 60)
        logger.info("LONG-TERM TREND ANALYSIS (Full Item History)")
        logger.info(f"Date: {self.analysis_date}")
        logger.info("=" * 60)

        # Get all items
        all_items = self.db.query(Item.id).all()
        total_items = len(all_items)
        logger.info(f"Total items in database: {total_items}")

        analyzed = 0
        skipped = 0
        created_records = 0

        for (item_id,) in all_items:
            result = self.analyze_item(item_id)

            if result:
                # Create trend indicator record
                trend_indicator = TrendIndicator(
                    item_id=item_id,
                    timestamp=self.analysis_date,
                    sma_7=result['ma_7day'],
                    sma_30=result['ma_30day'],
                    volatility=result['volatility'],
                    trend_score=result['momentum_score'],
                    trend_direction=result['trend_direction'],
                    confidence='high' if result['data_points'] > 100 else 'medium'
                )
                self.db.add(trend_indicator)
                analyzed += 1
                created_records += 1

                if analyzed % 500 == 0:
                    logger.info(f"Progress: {analyzed} items analyzed...")
            else:
                skipped += 1

        self.db.commit()

        logger.info(f"\n✅ Analysis complete:")
        logger.info(f"  Analyzed: {analyzed} items")
        logger.info(f"  Skipped: {skipped} items (too new or insufficient data)")
        logger.info(f"  Records created: {created_records}")

        return {
            'status': 'success',
            'analyzed': analyzed,
            'skipped': skipped,
            'records_created': created_records
        }


def main():
    db = SessionLocal()

    try:
        analyzer = LongTermTrendAnalyzer(db)
        result = analyzer.run_analysis()
        print(f"\nRESULT: {result}")

    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
