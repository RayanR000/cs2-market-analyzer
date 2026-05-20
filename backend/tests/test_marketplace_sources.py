"""
Tests for marketplace source collectors.
"""

from datetime import datetime

from collectors.marketplace_sources import (
    SkinportMarketCollector,
    DMarketCollector,
    build_marketplace_name_candidates,
)


class FakeResponse:
    def __init__(self, payload, headers=None):
        self._payload = payload
        self.headers = headers or {}
        self.content = b""

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_skinport_batch_collection_parses_price_and_volume(monkeypatch):
    collector = SkinportMarketCollector(chunk_size=10)

    def fake_get(url, params=None, timeout=None):
        assert "sales/history" in url
        return FakeResponse([
            {
                "market_hash_name": "AK-47 | Phantom Disruptor",
                "last_24_hours": {"median": 12.5, "volume": 8},
                "last_7_days": {"median": 11.0, "volume": 60},
            },
            {
                "market_hash_name": "Clutch Case",
                "last_24_hours": {"median": None, "volume": 0},
                "last_7_days": {"median": 0.78, "volume": 140},
            },
        ])

    monkeypatch.setattr(collector.session, "get", fake_get)

    results = collector.collect_batch_items(["AK-47 | Phantom Disruptor", "Clutch Case"])

    assert results["AK-47 | Phantom Disruptor"][0] == 12.5
    assert results["AK-47 | Phantom Disruptor"][1] == 8
    assert isinstance(results["AK-47 | Phantom Disruptor"][2], datetime)
    assert results["Clutch Case"][0] == 0.78
    assert results["Clutch Case"][1] == 140


def test_dmarket_batch_collection_parses_aggregated_prices(monkeypatch):
    collector = DMarketCollector()

    def fake_post(url, json=None, timeout=None):
        assert "aggregated-prices" in url
        return FakeResponse({
            "aggregatedPrices": [
                {
                    "title": "AK-47 | Phantom Disruptor",
                    "orderBestPrice": {"Currency": "USD", "Amount": "10.25"},
                    "orderCount": "12",
                    "offerBestPrice": {"Currency": "USD", "Amount": "12.75"},
                    "offerCount": "7",
                },
                {
                    "title": "Clutch Case",
                    "orderBestPrice": {"Currency": "USD", "Amount": "0.69"},
                    "orderCount": "100",
                    "offerBestPrice": {"Currency": "USD", "Amount": "0.74"},
                    "offerCount": "35",
                },
            ]
        })

    monkeypatch.setattr(collector.session, "post", fake_post)

    results = collector.collect_batch_items(["AK-47 | Phantom Disruptor", "Clutch Case"])

    assert results["AK-47 | Phantom Disruptor"][0] == 11.5
    assert results["AK-47 | Phantom Disruptor"][1] == 19
    assert isinstance(results["AK-47 | Phantom Disruptor"][2], datetime)
    assert results["Clutch Case"][0] == 0.72
    assert results["Clutch Case"][1] == 135


def test_marketplace_name_candidates_expand_skin_variants():
    candidates = build_marketplace_name_candidates("AWP Dragon Lore", "skin")

    assert "AWP Dragon Lore" in candidates
    assert "AWP | Dragon Lore" in candidates
    assert "AWP | Dragon Lore (Factory New)" in candidates
