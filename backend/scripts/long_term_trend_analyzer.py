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
from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean, stdev

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal, Item, PriceHistory, TrendIndicator, utcnow_naive
from sqlalchemy import func

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("long_term_analyzer")


class LongTermTrendAnalyzer:
    # Items fetched per bulk history query; bounds memory usage.
    ITEM_CHUNK_SIZE = 500

    def __init__(self, db_session):
        self.db = db_session
        self.analysis_date = utcnow_naive()
        self.min_data_points = 7
        self.min_age_days = 60
        self.max_lookback_days = 365 * 3  # 3 years

    def get_first_seen_bulk(self):
        """Get first price timestamp for every item.

        Reads from Parquet archive when available, otherwise Supabase.
        """
        archive_dir = Path(__file__).parent.parent.parent / "archive" / "price-archive"
        if archive_dir.exists():
            import duckdb
            con = duckdb.connect()
            try:
                rows = con.sql("""
                    SELECT item_slug, MIN(day) AS first_seen
                    FROM read_parquet('{}/*.parquet')
                    GROUP BY item_slug
                """.format(archive_dir)).fetchall()
                slug_rows = self.db.query(Item.id, Item.item_id).all()
                slug_map = {r.item_id: r.id for r in slug_rows}
                result = {}
                for slug, first_seen in rows:
                    int_id = slug_map.get(slug)
                    if int_id:
                        result[int_id] = datetime.combine(first_seen, datetime.min.time())
                return result
            finally:
                con.close()

        rows = self.db.query(
            PriceHistory.item_id,
            func.min(PriceHistory.timestamp)
        ).filter(
            ~PriceHistory.source.like('synthetic_demo'),
            ~PriceHistory.source.like('historical_fallback:%'),
        ).group_by(PriceHistory.item_id).all()

        return {item_id: first_seen for item_id, first_seen in rows}

    def get_price_history_bulk(self, item_ids):
        """Fetch daily price history for a chunk of items.

        Reads from Parquet archive when available, otherwise Supabase.
        """
        if not item_ids:
            return {}

        archive_dir = Path(__file__).parent.parent.parent / "archive" / "price-archive"
        if archive_dir.exists():
            import duckdb
            slug_rows = self.db.query(Item.id, Item.item_id).filter(
                Item.id.in_(item_ids)
            ).all()
            slug_to_int = {r.item_id: r.id for r in slug_rows}
            slug_set = list(slug_to_int.keys())
            lookback_date = self.analysis_date - timedelta(days=self.max_lookback_days)

            con = duckdb.connect()
            try:
                rows = con.sql("""
                    SELECT item_slug, day, mean_price AS price
                    FROM read_parquet('{}/*.parquet')
                    WHERE item_slug IN ?
                      AND day >= DATE ?
                    ORDER BY item_slug, day
                """.format(archive_dir), [slug_set, lookback_date.strftime("%Y-%m-%d")]).fetchall()

                daily = defaultdict(list)
                for slug, day, price in rows:
                    item_id = slug_to_int.get(slug)
                    if item_id:
                        daily[item_id].append((day, price))
                return dict(daily)
            finally:
                con.close()

        lookback_date = self.analysis_date - timedelta(days=self.max_lookback_days)

        rows = self.db.query(
            PriceHistory.item_id,
            PriceHistory.timestamp,
            PriceHistory.price
        ).filter(
            PriceHistory.item_id.in_(item_ids),
            PriceHistory.timestamp >= lookback_date,
            ~PriceHistory.source.like('synthetic_demo'),
            ~PriceHistory.source.like('historical_fallback:%'),
        ).order_by(PriceHistory.item_id, PriceHistory.timestamp).all()

        daily = defaultdict(lambda: defaultdict(list))
        for item_id, timestamp, price in rows:
            daily[item_id][timestamp.date()].append(price)

        return {
            item_id: [(day, sum(prices) / len(prices)) for day, prices in sorted(days.items())]
            for item_id, days in daily.items()
        }

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
        """Calculate price volatility as a percentage of the mean price.

        Using the coefficient of variation keeps the value comparable across
        cheap and expensive items and keeps price_stability (100 - volatility)
        meaningful.
        """
        if not prices or len(prices) < 2:
            return 0

        price_list = [p[1] for p in prices]
        mean_price = mean(price_list)
        if mean_price == 0:
            return 0

        try:
            volatility_pct = (stdev(price_list) / mean_price) * 100
        except Exception:
            return 0

        return min(volatility_pct, 100.0)

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

    def analyze_item(self, item_id, prices, age_days):
        """Analyze a single item using its (pre-fetched) daily history."""
        try:
            if age_days < self.min_age_days:
                return None

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

        first_seen = self.get_first_seen_bulk()

        eligible = []
        skipped = 0
        for (item_id,) in all_items:
            seen = first_seen.get(item_id)
            age_days = (self.analysis_date - seen).days if seen else 0
            if age_days >= self.min_age_days:
                eligible.append((item_id, age_days))
            else:
                skipped += 1

        logger.info(f"Eligible items (>= {self.min_age_days} days old): {len(eligible)}")

        analyzed = 0
        indicator_rows = []

        for start in range(0, len(eligible), self.ITEM_CHUNK_SIZE):
            chunk = eligible[start:start + self.ITEM_CHUNK_SIZE]
            prices_by_item = self.get_price_history_bulk([item_id for item_id, _ in chunk])

            for item_id, age_days in chunk:
                result = self.analyze_item(item_id, prices_by_item.get(item_id, []), age_days)

                if result:
                    indicator_rows.append({
                        'item_id': item_id,
                        'timestamp': self.analysis_date,
                        'sma_7': result['ma_7day'],
                        'sma_30': result['ma_30day'],
                        'volatility': result['volatility'],
                        'trend_score': result['momentum_score'],
                        'trend_direction': result['trend_direction'],
                        'confidence': 'high' if result['data_points'] > 100 else 'medium'
                    })
                    analyzed += 1

                    if analyzed % 500 == 0:
                        logger.info(f"Progress: {analyzed} items analyzed...")
                else:
                    skipped += 1

        if indicator_rows:
            self.db.bulk_insert_mappings(TrendIndicator, indicator_rows)
        self.db.commit()

        logger.info(f"\n✅ Analysis complete:")
        logger.info(f"  Analyzed: {analyzed} items")
        logger.info(f"  Skipped: {skipped} items (too new or insufficient data)")
        logger.info(f"  Records created: {len(indicator_rows)}")

        return {
            'status': 'success',
            'analyzed': analyzed,
            'skipped': skipped,
            'records_created': len(indicator_rows)
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
