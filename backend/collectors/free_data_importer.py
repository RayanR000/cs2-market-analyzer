"""
Free historical data importer for CS2 market data.

This module backfills price history from cs2.sh when available and uses
synthetic rows only to cover the pre-archive gap or any items the free
archive does not cover. It also imports official Steam announcements as
market events.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Sequence
from xml.etree import ElementTree as ET

import requests
from sqlalchemy.orm import Session

from collectors.cs2_data_sources import CS2ItemCatalog, HistoricalDataGenerator
from collectors.name_candidates import build_marketplace_name_candidates
from config import settings
from database import Event, Item, PriceHistory, SessionLocal

logger = logging.getLogger(__name__)


CS2SH_ARCHIVE_START = datetime(2023, 1, 1)
CS2SH_DEFAULT_BASE_URL = "https://api.cs2.sh"
STEAM_ANNOUNCEMENTS_RSS = "https://steamcommunity.com/app/730/announcements/rss"


def _parse_timestamp(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(float(value))

    text = str(value).strip()
    if not text:
        return None

    try:
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _generate_item_id(item_name: str) -> str:
    item_id = item_name.lower().replace(" | ", "-").replace(" ", "-")
    return "".join(ch for ch in item_id if ch.isalnum() or ch == "-")


def _infer_event_type(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if "operation" in text:
        return "operation"
    if "case" in text and any(term in text for term in ("new", "added", "released", "drop")):
        return "case_drop"
    if any(term in text for term in ("release notes", "official release", "released", "launch")):
        return "major"
    return "update"


@dataclass
class ImportedHistoryStats:
    item_name: str
    archive_rows: int = 0
    synthetic_rows: int = 0
    matched_source: Optional[str] = None


class CS2ShClient:
    """Small client for the free cs2.sh archive endpoints."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str = CS2SH_DEFAULT_BASE_URL,
        session: Optional[requests.Session] = None,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def enabled(self) -> bool:
        return bool(self.api_key)

    def fetch_archive_history(
        self,
        items: Sequence[str],
        start: datetime,
        end: Optional[datetime] = None,
        interval: str = "1d",
        sources: Optional[Sequence[str]] = None,
    ) -> Dict:
        if not self.api_key:
            raise RuntimeError("CS2SH_API_KEY is required for archive history import")

        payload: Dict[str, object] = {
            "items": list(items),
            "start": start.date().isoformat() if start else None,
            "interval": interval,
        }
        if end is not None:
            payload["end"] = end.date().isoformat()
        if sources:
            payload["sources"] = list(sources)

        response = self.session.post(
            f"{self.base_url}/v1/archive/history",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()


class SteamAnnouncementsImporter:
    """Imports official Steam announcements into the events table."""

    def __init__(
        self,
        rss_url: str = STEAM_ANNOUNCEMENTS_RSS,
        session: Optional[requests.Session] = None,
        timeout: int = 30,
    ) -> None:
        self.rss_url = rss_url
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_announcements(self) -> List[Dict[str, object]]:
        response = self.session.get(self.rss_url, timeout=self.timeout)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        channel = root.find("channel")
        if channel is None:
            return []

        announcements: List[Dict[str, object]] = []
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date_raw = item.findtext("pubDate") or item.findtext("date") or ""
            description_html = item.findtext("description") or ""
            summary = _strip_html(description_html)

            timestamp = None
            if pub_date_raw:
                try:
                    timestamp = parsedate_to_datetime(pub_date_raw)
                    if timestamp.tzinfo:
                        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
                except Exception:
                    timestamp = _parse_timestamp(pub_date_raw)

            if not title or not timestamp:
                continue

            announcements.append(
                {
                    "title": title,
                    "link": link,
                    "timestamp": timestamp,
                    "summary": summary,
                    "type": _infer_event_type(title, summary),
                }
            )

        return announcements


class FreeDataBackfillImporter:
    """
    Backfill CS2 catalog, price history, and official events without a paid provider.

    The importer prefers real archive data from cs2.sh and falls back to
    synthetic rows only when the archive has no coverage.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cs2sh_client: Optional[CS2ShClient] = None,
        announcements_importer: Optional[SteamAnnouncementsImporter] = None,
    ) -> None:
        resolved_api_key = api_key if api_key is not None else settings.cs2sh_api_key
        self.cs2sh_client = cs2sh_client or CS2ShClient(api_key=resolved_api_key)
        self.announcements_importer = announcements_importer or SteamAnnouncementsImporter()

    def ensure_catalog(self, db: Session) -> Dict[str, int]:
        """Seed or update the local item catalog using the static CS2 catalog."""
        stats = {"items_added": 0, "items_updated": 0, "items_skipped": 0}
        for catalog_item in CS2ItemCatalog.get_all_items():
            existing = db.query(Item).filter(Item.name == catalog_item["name"]).first()
            if existing:
                updated = False
                if not existing.release_date and catalog_item.get("release_date"):
                    existing.release_date = catalog_item["release_date"]
                    updated = True
                if updated:
                    stats["items_updated"] += 1
                else:
                    stats["items_skipped"] += 1
                continue

            item = Item(
                item_id=_generate_item_id(catalog_item["name"]),
                name=catalog_item["name"],
                type=catalog_item["type"],
                release_date=catalog_item.get("release_date"),
            )
            db.add(item)
            stats["items_added"] += 1

        db.flush()
        return stats

    def _price_record_exists(
        self,
        db: Session,
        item_id: int,
        timestamp: datetime,
        source: str,
    ) -> bool:
        return (
            db.query(PriceHistory.id)
            .filter(
                PriceHistory.item_id == item_id,
                PriceHistory.timestamp == timestamp,
                PriceHistory.source == source,
            )
            .first()
            is not None
        )

    def _store_archive_rows(
        self,
        db: Session,
        item: Item,
        entry: Dict[str, object],
        source_name: str = "cs2sh_archive",
    ) -> int:
        rows_added = 0
        data_points = entry.get("data") or []
        for point in data_points:
            if not isinstance(point, dict):
                continue
            bucket = _parse_timestamp(point.get("bucket"))
            aggregate = point.get("aggregate") or {}
            if not bucket or not isinstance(aggregate, dict):
                continue

            ask = aggregate.get("ask")
            bid = aggregate.get("bid")
            ask_volume = aggregate.get("ask_volume")
            bid_volume = aggregate.get("bid_volume")
            hourly_volume = aggregate.get("hourly_volume")

            if ask is not None and bid is not None:
                price_value = (float(ask) + float(bid)) / 2.0
            else:
                price_value = ask if ask is not None else bid
            if price_value is None:
                continue

            volume_value = hourly_volume if hourly_volume is not None else ask_volume
            if volume_value is None:
                volume_value = bid_volume

            if self._price_record_exists(db, item.id, bucket, source_name):
                continue

            db.add(
                PriceHistory(
                    item_id=item.id,
                    timestamp=bucket,
                    price=float(price_value),
                    volume=int(volume_value) if volume_value is not None else None,
                    median_price=float(price_value),
                    source=source_name,
                )
            )
            rows_added += 1

        return rows_added

    def _store_synthetic_rows(
        self,
        db: Session,
        item: Item,
        start_date: datetime,
        end_date: datetime,
        source_name: str = "synthetic_demo",
    ) -> int:
        if end_date < start_date:
            return 0

        generated = HistoricalDataGenerator.generate_historical_prices(
            item.name,
            start_date,
            end_date,
            days_back=max((end_date - start_date).days + 1, 1),
        )

        rows_added = 0
        for timestamp, price, volume in generated:
            if self._price_record_exists(db, item.id, timestamp, source_name):
                continue
            db.add(
                PriceHistory(
                    item_id=item.id,
                    timestamp=timestamp,
                    price=price,
                    volume=volume,
                    median_price=price,
                    source=source_name,
                )
            )
            rows_added += 1
        return rows_added

    def backfill_price_history(
        self,
        db: Optional[Session] = None,
        history_start: datetime = CS2SH_ARCHIVE_START,
        interval: str = "1d",
        fill_missing_with_synthetic: bool = True,
        commit_every_item: bool = True,
    ) -> Dict[str, object]:
        """
        Import archive history from cs2.sh and synthesize only the uncovered gap.
        """
        own_db = db is None
        db = db or SessionLocal()
        stats: Dict[str, object] = {
            "items_total": 0,
            "items_with_archive": 0,
            "archive_rows_added": 0,
            "synthetic_rows_added": 0,
            "items": [],
            "synthetic_enabled": fill_missing_with_synthetic,
            "history_start": history_start.date().isoformat(),
        }

        try:
            items = db.query(Item).order_by(Item.name.asc()).all()
            stats["items_total"] = len(items)
            now = datetime.utcnow()
            for item in items:
                item_stats = ImportedHistoryStats(item_name=item.name)
                release_date = item.release_date or history_start
                request_start = max(history_start, release_date)
                candidate_names = build_marketplace_name_candidates(item.name, item.type)

                archive_rows = 0
                if self.cs2sh_client.enabled():
                    try:
                        payload = self.cs2sh_client.fetch_archive_history(
                            candidate_names,
                            start=request_start,
                            end=now,
                            interval=interval,
                            sources=["aggregate"],
                        )
                        response_items = payload.get("items") or {}
                        ordered_candidates = [name for name in candidate_names if name in response_items]
                        for candidate in ordered_candidates:
                            archive_rows += self._store_archive_rows(
                                db,
                                item,
                                response_items[candidate],
                                source_name="cs2sh_archive",
                            )
                            item_stats.matched_source = candidate
                            if archive_rows:
                                break
                    except Exception as exc:
                        logger.warning("Archive import failed for %s: %s", item.name, exc)

                item_stats.archive_rows = archive_rows
                if archive_rows:
                    stats["items_with_archive"] = int(stats["items_with_archive"]) + 1

                synthetic_rows = 0
                if fill_missing_with_synthetic:
                    if archive_rows == 0:
                        synthetic_rows += self._store_synthetic_rows(
                            db,
                            item,
                            start_date=release_date,
                            end_date=now,
                            source_name="synthetic_demo",
                        )
                    elif release_date < history_start:
                        synthetic_rows += self._store_synthetic_rows(
                            db,
                            item,
                            start_date=release_date,
                            end_date=history_start - timedelta(days=1),
                            source_name="synthetic_demo",
                        )

                item_stats.synthetic_rows = synthetic_rows
                stats["archive_rows_added"] = int(stats["archive_rows_added"]) + archive_rows
                stats["synthetic_rows_added"] = int(stats["synthetic_rows_added"]) + synthetic_rows
                stats["items"].append(item_stats.__dict__)

                if commit_every_item:
                    db.flush()

            db.commit()
            return stats
        except Exception:
            db.rollback()
            raise
        finally:
            if own_db:
                db.close()

    def import_official_events(
        self,
        db: Optional[Session] = None,
        max_items: Optional[int] = None,
    ) -> Dict[str, object]:
        """Import official Steam announcements into the events table."""
        own_db = db is None
        db = db or SessionLocal()
        stats: Dict[str, object] = {
            "events_added": 0,
            "events_skipped": 0,
            "source": "steam_announcements",
        }

        try:
            announcements = self.announcements_importer.fetch_announcements()
            if max_items is not None:
                announcements = announcements[:max_items]

            for announcement in announcements:
                title = str(announcement.get("title") or "").strip()
                timestamp = announcement.get("timestamp")
                if not title or not isinstance(timestamp, datetime):
                    stats["events_skipped"] = int(stats["events_skipped"]) + 1
                    continue

                summary = str(announcement.get("summary") or "")
                link = str(announcement.get("link") or "")
                description = _strip_html(summary)
                if link:
                    description = f"{description} ({link})" if description else link
                description = f"{title} - {description}" if description else title
                if len(description) > 500:
                    description = description[:497] + "..."

                event_type = str(announcement.get("type") or _infer_event_type(title, description))

                exists = (
                    db.query(Event.id)
                    .filter(
                        Event.timestamp == timestamp,
                        Event.type == event_type,
                        Event.description == description,
                    )
                    .first()
                )
                if exists:
                    stats["events_skipped"] = int(stats["events_skipped"]) + 1
                    continue

                db.add(
                    Event(
                        type=event_type,
                        timestamp=timestamp,
                        description=description,
                    )
                )
                stats["events_added"] = int(stats["events_added"]) + 1

            db.commit()
            return stats
        except Exception:
            db.rollback()
            raise
        finally:
            if own_db:
                db.close()

    def run_full_import(
        self,
        db: Optional[Session] = None,
        history_start: datetime = CS2SH_ARCHIVE_START,
    ) -> Dict[str, object]:
        """Run catalog, history, and event import in one explicit step."""
        own_db = db is None
        db = db or SessionLocal()
        try:
            catalog_stats = self.ensure_catalog(db)
            history_stats = self.backfill_price_history(
                db=db,
                history_start=history_start,
                fill_missing_with_synthetic=True,
            )
            event_stats = self.import_official_events(db=db)
            db.commit()
            return {
                "catalog": catalog_stats,
                "history": history_stats,
                "events": event_stats,
            }
        finally:
            if own_db:
                db.close()


def load_free_cs2_data(db: Optional[Session] = None) -> Dict[str, object]:
    """Convenience helper for manual imports and scripts."""
    importer = FreeDataBackfillImporter()
    return importer.run_full_import(db=db)
