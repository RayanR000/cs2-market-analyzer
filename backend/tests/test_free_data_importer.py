from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database as database_module
from collectors import free_data_importer as free_importer_module
from collectors.free_data_importer import FreeDataBackfillImporter, SteamAnnouncementsImporter
from database import Item, PriceHistory, Event


class FakeCS2ShClient:
    def enabled(self) -> bool:
        return True

    def fetch_archive_history(self, items, start, end=None, interval="1d", sources=None):
        assert interval == "1d"
        assert sources == ["aggregate"]
        return {
            "items": {
                "AWP | Asiimov (Field-Tested)": {
                    "market_hash_name": "AWP | Asiimov (Field-Tested)",
                    "count": 2,
                    "data": [
                        {
                            "bucket": "2023-01-01T00:00:00Z",
                            "aggregate": {
                                "ask": 120.0,
                                "bid": 118.0,
                                "ask_volume": 41,
                                "bid_volume": 7,
                                "hourly_volume": 9,
                                "total_supply": 1000,
                                "sample_count": 24,
                            },
                        },
                        {
                            "bucket": "2023-01-02T00:00:00Z",
                            "aggregate": {
                                "ask": 122.0,
                                "bid": 119.0,
                                "ask_volume": 42,
                                "bid_volume": 8,
                                "hourly_volume": 10,
                                "total_supply": 1001,
                                "sample_count": 24,
                            },
                        },
                    ],
                }
            }
        }


class FakeAnnouncementsImporter:
    def fetch_announcements(self):
        return [
            {
                "title": "Counter-Strike 2 Update",
                "timestamp": datetime(2024, 4, 1, 12, 0, 0),
                "summary": "Today's <b>update</b> adds new animation work.",
                "link": "https://steamcommunity.com/app/730/announcements/detail/123",
                "type": "update",
            }
        ]


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    test_session_factory = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    database_module.engine = test_engine
    database_module.SessionLocal = test_session_factory
    free_importer_module.SessionLocal = test_session_factory
    database_module.Base.metadata.create_all(bind=test_engine)
    yield


def test_backfill_uses_archive_and_synthetic_gap():
    db = database_module.SessionLocal()
    try:
        item = Item(
            item_id="awp-asiimov",
            name="AWP Asiimov",
            type="skin",
            release_date=datetime(2022, 1, 1),
        )
        db.add(item)
        db.commit()

        original_generator = free_importer_module.HistoricalDataGenerator.generate_historical_prices
        free_importer_module.HistoricalDataGenerator.generate_historical_prices = staticmethod(
            lambda item_name, release_date, end_date=None, days_back=365: [
                (datetime(2022, 12, 31), 99.0, 33)
            ]
        )

        importer = FreeDataBackfillImporter(
            api_key="test-key",
            cs2sh_client=FakeCS2ShClient(),
            announcements_importer=FakeAnnouncementsImporter(),
        )
        stats = importer.backfill_price_history(db=db, history_start=datetime(2023, 1, 1))
        assert stats["archive_rows_added"] == 2
        assert stats["synthetic_rows_added"] == 1

        sources = {
            row[0]
            for row in db.query(PriceHistory.source).filter(PriceHistory.item_id == item.id).all()
        }
        assert sources == {"cs2sh_archive", "synthetic_demo"}
    finally:
        free_importer_module.HistoricalDataGenerator.generate_historical_prices = original_generator
        db.close()


def test_official_announcements_import():
    db = database_module.SessionLocal()
    try:
        importer = FreeDataBackfillImporter(
            api_key=None,
            cs2sh_client=FakeCS2ShClient(),
            announcements_importer=FakeAnnouncementsImporter(),
        )
        stats = importer.import_official_events(db=db)
        assert stats["events_added"] == 1

        event = db.query(Event).first()
        assert event is not None
        assert event.type == "update"
        assert "Counter-Strike 2 Update" in event.description
        assert "https://steamcommunity.com/app/730/announcements/detail/123" in event.description
    finally:
        db.close()
