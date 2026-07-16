"""
skins.ai market data collector.

Free, no-key, no-cookie CS2 price API. Pulls the full catalog (name, slug,
best cross-market price) in a single bulk call and matches it against the
local item catalog so skins.ai becomes an additional price source that flows
into the Parquet archive alongside CSGOTrader.

API reference: https://skins.ai/developers
"""

import logging
import re
import unicodedata
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

CATALOG_URL = "https://skins.ai/api/item-names"
SOURCE_LABEL = "skinsai"

WEAR_SUFFIXES = (
    "Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred",
    "Holo", "Foil", "Glitter", "Gold", "Paper",
)

# Condition names only — safe to strip even when not wrapped in parentheses
# (e.g. embedded in a slug like "m9-bayonet-fade-factory-new"). Sticker variants
# such as Holo/Gold are left intact because they are distinguishing variants in
# the catalog and must not be removed.
BARE_CONDITION_SUFFIXES = (
    "Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred",
)


def _normalize_name(name: str) -> str:
    normalized = (name or "").replace("™", "").replace("®", "")
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = normalized.casefold()
    normalized = normalized.replace("|", " ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _strip_variant(name: str) -> str:
    stripped = name
    for suffix in WEAR_SUFFIXES:
        stripped = re.sub(
            r"\s*\(\s*" + re.escape(suffix) + r"\s*\)", "", stripped, flags=re.IGNORECASE
        )
    for suffix in BARE_CONDITION_SUFFIXES:
        stripped = re.sub(r"\b" + re.escape(suffix) + r"\b", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"^\s*★\s*", "", stripped)
    stripped = re.sub(r"^\s*StatTrak[™ ]*\s*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"^\s*Souvenir\s+", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return stripped


class SkinsAIClient:
    """Fetches skins.ai prices and matches them to local items by name."""

    def __init__(self, timeout: int = 30, session: Optional[requests.Session] = None):
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": "CS2MarketAnalyzer/1.0 (+skins.ai free API)"}
        )
        self._catalog: List[dict] = []
        self._name_lookup: Dict[str, dict] = {}
        self._slug_lookup: Dict[str, dict] = {}

    def fetch_catalog(self) -> List[dict]:
        try:
            response = self.session.get(CATALOG_URL, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.warning("Failed to fetch skins.ai catalog: %s", e)
            self._catalog = []
            return self._catalog

        if isinstance(data, list):
            self._catalog = data
        elif isinstance(data, dict):
            self._catalog = data.get("data") or data.get("items") or []
        else:
            self._catalog = []

        self._name_lookup = {}
        self._slug_lookup = {}
        for entry in self._catalog:
            name = entry.get("n") or entry.get("name")
            slug = entry.get("s") or entry.get("slug")
            if name:
                self._name_lookup[_normalize_name(name)] = entry
            if slug:
                self._slug_lookup[_normalize_name(slug)] = entry

        logger.info("Fetched skins.ai catalog: %s items", len(self._catalog))
        return self._catalog

    def match(self, item_name: str, item_slug: Optional[str] = None) -> Optional[dict]:
        if not self._catalog:
            self.fetch_catalog()
        if not self._catalog:
            return None

        name_norm = _normalize_name(item_name)
        if name_norm in self._name_lookup:
            return self._name_lookup[name_norm]

        base_name = _strip_variant(item_name)
        base_norm = _normalize_name(base_name)
        if base_norm in self._name_lookup:
            return self._name_lookup[base_norm]

        if item_slug:
            slug_norm = _normalize_name(item_slug)
            if slug_norm in self._slug_lookup:
                return self._slug_lookup[slug_norm]
            base_slug_norm = _normalize_name(_strip_variant(item_slug.replace("-", " ")))
            if base_slug_norm in self._name_lookup:
                return self._name_lookup[base_slug_norm]

        return None

    def collect_for_items(self, items: List[dict]) -> Dict[str, object]:
        """Match a list of local items to skins.ai prices.

        Args:
            items: list of {"id": int, "item_id": slug, "name": str}

        Returns:
            {
                "records": [{"item_id", "slug", "price", "source"}],
                "matched": int, "unmatched": int, "total": int,
            }
        """
        if not self._catalog:
            self.fetch_catalog()

        records: List[dict] = []
        matched = 0
        unmatched = 0

        for item in items:
            entry = self.match(item["name"], item.get("item_id"))
            if entry is None:
                unmatched += 1
                continue
            price = entry.get("p") if "p" in entry else entry.get("price")
            if price is None or price <= 0:
                unmatched += 1
                continue
            records.append({
                "item_id": item["id"],
                "slug": item["item_id"],
                "price": float(price),
                "source": SOURCE_LABEL,
            })
            matched += 1

        logger.info(
            "skins.ai matched %s/%s items (%s unmatched)",
            matched, len(items), unmatched,
        )
        return {
            "records": records,
            "matched": matched,
            "unmatched": unmatched,
            "total": len(items),
        }
