from __future__ import annotations

from types import SimpleNamespace

import collectors.skinsai_collector as skinsai_module
from collectors.skinsai_collector import SkinsAIClient, SOURCE_LABEL


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


CATALOG = [
    {"n": "AK-47 | Redline", "s": "ak-47-redline", "g": "cs2", "p": 24.37},
    {"n": "AK-47 | Redline (Field-Tested)", "s": "ak-47-redline-field-tested", "g": "cs2", "p": 24.10},
    {"n": "★ M9 Bayonet | Fade (Factory New)", "s": "m9-bayonet-fade-factory-new", "g": "cs2", "p": 900.0},
    {"n": "Sticker | s1mple (Holo) | Shanghai 2024", "s": "sticker-s1mple-holo-shanghai-2024", "g": "cs2", "p": 5.5},
]


def make_client(catalog=CATALOG):
    client = SkinsAIClient()
    client.session = SimpleNamespace(
        get=lambda *a, **k: FakeResponse(catalog)
    )
    return client


def test_fetch_catalog_builds_lookups():
    client = make_client()
    catalog = client.fetch_catalog()
    assert len(catalog) == 4
    assert "ak-47 redline" in client._name_lookup
    assert "ak-47-redline" in client._slug_lookup


def test_match_exact_name():
    client = make_client()
    entry = client.match("AK-47 | Redline (Field-Tested)", "ak-47-redline-field-tested")
    assert entry is not None
    assert entry["p"] == 24.10


def test_match_base_name_fallback():
    client = make_client()
    entry = client.match("AK-47 | Redline (Minimal Wear)", "ak-47-redline-minimal-wear")
    assert entry is not None
    assert entry["p"] == 24.37


def test_match_slug_fallback():
    client = make_client()
    entry = client.match("Unknown Name", "ak-47-redline")
    assert entry is not None
    assert entry["p"] == 24.37


def test_match_stattrak_and_star_variants():
    client = make_client()
    assert client.match("StatTrak AK-47 | Redline (Field-Tested)", "stattrak-ak-47-redline-field-tested") is not None
    assert client.match("★ M9 Bayonet | Fade (Factory New)", "m9-bayonet-fade-factory-new") is not None


def test_match_unmatched_returns_none():
    client = make_client()
    assert client.match("Something With No Listing", "nope") is None


def test_collect_for_items_builds_records():
    client = make_client()
    items = [
        {"id": 1, "item_id": "ak-47-redline-field-tested", "name": "AK-47 | Redline (Field-Tested)"},
        {"id": 2, "item_id": "m9-bayonet-fade-factory-new", "name": "★ M9 Bayonet | Fade (Factory New)"},
        {"id": 3, "item_id": "ghost-item", "name": "No Such Skin"},
    ]
    result = client.collect_for_items(items)
    assert result["matched"] == 2
    assert result["unmatched"] == 1
    assert len(result["records"]) == 2
    rec = result["records"][0]
    assert rec["source"] == SOURCE_LABEL
    assert rec["item_id"] == 1
    assert rec["price"] == 24.10


def test_collect_skips_nonpositive_price():
    client = make_client(catalog=[{"n": "Broken Skin", "s": "broken-skin", "g": "cs2", "p": 0}])
    result = client.collect_for_items([{"id": 1, "item_id": "broken-skin", "name": "Broken Skin"}])
    assert result["matched"] == 0


def test_fetch_catalog_failure_returns_empty(monkeypatch):
    client = SkinsAIClient()
    client.session = SimpleNamespace(get=lambda *a, **k: (_ for _ in ()).throw(Exception("boom")))
    assert client.fetch_catalog() == []
    assert client.match("AK-47 | Redline") is None
