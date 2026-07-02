from __future__ import annotations

from datetime import datetime

from collectors.csfloat_market import CSFloatMarketCollector


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_csfloat_batch_collection_parses_listings(monkeypatch):
    collector = CSFloatMarketCollector()

    def fake_get(url, params=None, timeout=None):
        assert "listings" in url
        assert params["market_hash_name"] == "AK-47 | Redline (Field-Tested)"
        return FakeResponse([
            {"price": 1250},
            {"price": 1349},
            {"price": 1299},
        ])

    monkeypatch.setattr(collector.session, "get", fake_get)

    results = collector.collect_batch_items(["AK-47 | Redline (Field-Tested)"])

    assert results["AK-47 | Redline (Field-Tested)"][0] == 12.5
    assert results["AK-47 | Redline (Field-Tested)"][1] == 3
    assert isinstance(results["AK-47 | Redline (Field-Tested)"][2], datetime)
