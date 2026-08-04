"""Tests for stats accumulation, formatting, and state round-trip."""

import json
import os
import tempfile

import pytest

from url_monitor.checker import CheckResult, Status
from url_monitor.state import StateStore, UrlState, load_state, save_state
from url_monitor.stats import UrlStats, format_stats, record


class TestRecord:
    """Test counter accumulation via record()."""

    def test_accumulate_sequence(self):
        """Record a sequence of results and verify counts."""
        stats = UrlStats()

        # Two successful checks
        record(stats, CheckResult(http_status=200, error=None, total_ms=100), Status.Up)
        record(stats, CheckResult(http_status=200, error=None, total_ms=120), Status.Up)

        # One 503
        record(
            stats,
            CheckResult(http_status=503, error=None, total_ms=200),
            Status.Down,
        )

        # One timeout error
        record(
            stats,
            CheckResult(http_status=0, error="connection_timeout", total_ms=0),
            Status.Down,
        )

        assert stats.total_checks == 4
        assert stats.up_checks == 2
        assert stats.down_checks == 2
        assert stats.http_status[200] == 2
        assert stats.http_status[503] == 1
        assert stats.errors["connection_timeout"] == 1

    def test_single_up_check(self):
        stats = UrlStats()
        record(stats, CheckResult(http_status=200, error=None, total_ms=50), Status.Up)
        assert stats.total_checks == 1
        assert stats.up_checks == 1
        assert stats.down_checks == 0
        assert stats.http_status == {200: 1}
        assert stats.errors == {}

    def test_error_does_not_record_http_status(self):
        """When there's an error, HTTP status 0 should not be recorded."""
        stats = UrlStats()
        record(
            stats,
            CheckResult(http_status=0, error="connection_refused", total_ms=0),
            Status.Down,
        )
        assert stats.http_status == {}
        assert stats.errors == {"connection_refused": 1}


class TestFormatStats:
    """Test format_stats() output."""

    def test_format_with_data(self):
        stats = UrlStats(
            total_checks=4,
            up_checks=2,
            down_checks=2,
            http_status={200: 2, 503: 1},
            errors={"connection_timeout": 1},
        )
        output = format_stats("https://example.com", stats)
        assert "checks=4" in output
        assert "up=2" in output
        assert "down=2" in output
        assert "uptime=50.0%" in output
        assert "200: 2" in output
        assert "503: 1" in output
        assert "connection_timeout: 1" in output

    def test_format_no_errors(self):
        stats = UrlStats(
            total_checks=10,
            up_checks=10,
            down_checks=0,
            http_status={200: 10},
            errors={},
        )
        output = format_stats("https://example.com", stats)
        assert "uptime=100.0%" in output
        assert "errors  (none)" in output

    def test_format_zero_checks(self):
        stats = UrlStats()
        output = format_stats("https://example.com", stats)
        assert "checks=0" in output
        assert "uptime=0.0%" in output


class TestStateRoundTrip:
    """Test state persistence round-trip."""

    def test_save_and_load(self):
        """Create StateStore, save to temp file, load back, verify equality."""
        store = StateStore(version=1)
        store.urls["https://example.com"] = UrlState(
            status=Status.Up,
            last_checked="2026-08-04T10:00:00Z",
            stats=UrlStats(
                total_checks=10,
                up_checks=8,
                down_checks=2,
                http_status={200: 8, 503: 2},
                errors={},
            ),
        )
        store.urls["https://down.example.com"] = UrlState(
            status=Status.Down,
            last_checked="2026-08-04T10:00:00Z",
            stats=UrlStats(
                total_checks=5,
                up_checks=0,
                down_checks=5,
                http_status={},
                errors={"connection_timeout": 3, "connection_refused": 2},
            ),
        )

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            save_state(tmp_path, store)
            loaded = load_state(tmp_path)

            assert loaded.version == store.version
            assert set(loaded.urls.keys()) == set(store.urls.keys())

            for url in store.urls:
                orig = store.urls[url]
                back = loaded.urls[url]
                assert back.status == orig.status
                assert back.last_checked == orig.last_checked
                assert back.stats.total_checks == orig.stats.total_checks
                assert back.stats.up_checks == orig.stats.up_checks
                assert back.stats.down_checks == orig.stats.down_checks
                assert back.stats.http_status == orig.stats.http_status
                assert back.stats.errors == orig.stats.errors
        finally:
            os.unlink(tmp_path)

    def test_legacy_state_without_stats(self):
        """State entry without 'stats' key loads with zeroed stats."""
        legacy_data = {
            "version": 1,
            "urls": {
                "https://example.com": {
                    "status": "up",
                    "last_checked": "2026-08-04T09:00:00Z",
                }
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(legacy_data, f)
            tmp_path = f.name

        try:
            loaded = load_state(tmp_path)
            url_state = loaded.urls["https://example.com"]
            assert url_state.status == Status.Up
            assert url_state.stats.total_checks == 0
            assert url_state.stats.up_checks == 0
            assert url_state.stats.down_checks == 0
            assert url_state.stats.http_status == {}
            assert url_state.stats.errors == {}
        finally:
            os.unlink(tmp_path)

    def test_missing_file_returns_empty(self):
        """Missing state file returns an empty StateStore."""
        store = load_state("/nonexistent/path/to/state.json")
        assert store.version == 1
        assert store.urls == {}

    def test_corrupt_file_returns_empty(self):
        """Corrupt JSON returns empty store with a warning."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json content!!!")
            tmp_path = f.name

        try:
            loaded = load_state(tmp_path)
            assert loaded.urls == {}
        finally:
            os.unlink(tmp_path)
