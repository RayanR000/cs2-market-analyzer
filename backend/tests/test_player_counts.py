import csv
import os
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

import collectors.player_counts as pc
from collectors.player_counts import (
    fetch_current_cs2_players,
    collect_and_append,
    read_daily_csv,
    summarize_daily_csv,
    get_daily_csv_path,
    PLAYER_COUNTS_DIR,
)


def _cleanup(path: str):
    if os.path.exists(path):
        os.remove(path)


class TestFetchCurrentCS2Players:
    def test_returns_count_on_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": {"player_count": 123456}}
        with patch("collectors.player_counts.requests.get", return_value=mock_resp):
            count = fetch_current_cs2_players()
        assert count == 123456

    def test_returns_none_on_missing_key(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": {}}
        with patch("collectors.player_counts.requests.get", return_value=mock_resp):
            count = fetch_current_cs2_players()
        assert count is None

    def test_raises_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("HTTP error")
        with patch("collectors.player_counts.requests.get", return_value=mock_resp):
            with pytest.raises(Exception, match="HTTP error"):
                fetch_current_cs2_players()

    def test_returns_int_cast(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": {"player_count": "78901"}}
        with patch("collectors.player_counts.requests.get", return_value=mock_resp):
            count = fetch_current_cs2_players()
        assert count == 78901
        assert isinstance(count, int)

    def test_raises_on_request_exception(self):
        with patch("collectors.player_counts.requests.get", side_effect=Exception("timeout")):
            with pytest.raises(Exception, match="timeout"):
                fetch_current_cs2_players()


class TestCollectAndAppend:
    def test_appends_row_to_csv(self):
        path = get_daily_csv_path("2026-01-15")
        _cleanup(path)
        try:
            with patch("collectors.player_counts.fetch_current_cs2_players", return_value=50000):
                result = collect_and_append("2026-01-15")
            assert result == 50000
            assert os.path.exists(path)
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            assert len(rows) == 1
            assert rows[0]["players"] == "50000"
            assert rows[0]["timestamp"].endswith("Z")
        finally:
            _cleanup(path)

    def test_appends_multiple_rows(self):
        path = get_daily_csv_path("2026-01-16")
        _cleanup(path)
        try:
            with patch("collectors.player_counts.fetch_current_cs2_players", side_effect=[40000, 41000, 42000]):
                for _ in range(3):
                    collect_and_append("2026-01-16")
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            assert len(rows) == 3
            assert [r["players"] for r in rows] == ["40000", "41000", "42000"]
        finally:
            _cleanup(path)

    def test_returns_none_when_fetch_fails(self):
        with patch("collectors.player_counts.fetch_current_cs2_players", return_value=None):
            result = collect_and_append("2026-01-17")
        assert result is None

    def test_writes_header_only_once(self):
        path = get_daily_csv_path("2026-01-18")
        _cleanup(path)
        try:
            with patch("collectors.player_counts.fetch_current_cs2_players", side_effect=[100, 200]):
                collect_and_append("2026-01-18")
                collect_and_append("2026-01-18")
            with open(path, newline="") as f:
                reader = csv.reader(f)
                header = next(reader)
                assert header == ["timestamp", "players"]
                rows = list(reader)
            assert len(rows) == 2
        finally:
            _cleanup(path)


class TestReadDailyCSV:
    def test_returns_empty_list_when_no_file(self):
        rows = read_daily_csv("2099-12-31")
        assert rows == []

    def test_returns_rows(self):
        path = get_daily_csv_path("2026-02-01")
        _cleanup(path)
        try:
            with patch("collectors.player_counts.fetch_current_cs2_players", return_value=60000):
                collect_and_append("2026-02-01")
                collect_and_append("2026-02-01")
            rows = read_daily_csv("2026-02-01")
            assert len(rows) == 2
            assert rows[0]["players"] == "60000"
        finally:
            _cleanup(path)


class TestSummarizeDailyCSV:
    def test_returns_none_when_no_data(self):
        result = summarize_daily_csv("2099-12-31")
        assert result is None

    def test_computes_correct_stats(self):
        path = get_daily_csv_path("2026-03-01")
        _cleanup(path)
        try:
            with patch("collectors.player_counts.fetch_current_cs2_players",
                       side_effect=[100, 200, 150, 300, 250]):
                for _ in range(5):
                    collect_and_append("2026-03-01")
            stats = summarize_daily_csv("2026-03-01")
            assert stats is not None
            assert stats["date"] == "2026-03-01"
            assert stats["mean_players"] == 200
            assert stats["peak_players"] == 300
            assert stats["min_players"] == 100
            assert stats["reading_count"] == 5
            assert stats["last_players"] == 250
        finally:
            _cleanup(path)

    def test_keys_present(self):
        path = get_daily_csv_path("2026-03-02")
        _cleanup(path)
        try:
            with patch("collectors.player_counts.fetch_current_cs2_players", return_value=500):
                collect_and_append("2026-03-02")
            stats = summarize_daily_csv("2026-03-02")
            assert stats is not None
            for key in ("date", "mean_players", "peak_players", "min_players",
                        "reading_count", "last_players", "last_timestamp"):
                assert key in stats
        finally:
            _cleanup(path)


class TestMainBlock:
    def test_exits_one_when_collect_fails(self):
        with (
            patch.object(pc, "collect_and_append", return_value=None),
            patch("sys.exit") as mock_exit,
            patch("builtins.print"),
        ):
            count = pc.collect_and_append()
            if count is None:
                import sys
                sys.exit(1)
        mock_exit.assert_called_once_with(1)

    def test_no_exit_on_success(self):
        with (
            patch.object(pc, "collect_and_append", return_value=50000),
            patch("sys.exit") as mock_exit,
            patch("builtins.print"),
        ):
            count = pc.collect_and_append()
            if count is None:
                import sys
                sys.exit(1)
        mock_exit.assert_not_called()


class TestGetDailyCSVPath:
    def test_returns_path_with_date(self):
        path = get_daily_csv_path("2026-04-01")
        assert path == f"{PLAYER_COUNTS_DIR}/2026-04-01.csv"
