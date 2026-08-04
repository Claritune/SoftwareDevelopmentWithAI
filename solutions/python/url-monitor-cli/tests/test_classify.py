"""Tests for status classification logic."""

import pytest

from url_monitor.checker import CheckResult, Status, classify, status_name


class TestClassify:
    """Test the classify() function — up only if no error AND HTTP 200."""

    def test_http_200_no_error_is_up(self):
        result = CheckResult(http_status=200, error=None, total_ms=150.0)
        assert classify(result) == Status.Up

    def test_http_301_no_error_is_down(self):
        result = CheckResult(http_status=301, error=None, total_ms=200.0)
        assert classify(result) == Status.Down

    def test_http_404_no_error_is_down(self):
        result = CheckResult(http_status=404, error=None, total_ms=100.0)
        assert classify(result) == Status.Down

    def test_http_500_no_error_is_down(self):
        result = CheckResult(http_status=500, error=None, total_ms=300.0)
        assert classify(result) == Status.Down

    def test_http_503_no_error_is_down(self):
        result = CheckResult(http_status=503, error=None, total_ms=250.0)
        assert classify(result) == Status.Down

    def test_error_timeout_is_down(self):
        result = CheckResult(http_status=0, error="connection_timeout", total_ms=0.0)
        assert classify(result) == Status.Down

    def test_error_connection_refused_is_down(self):
        result = CheckResult(
            http_status=0, error="connection_refused", total_ms=0.0
        )
        assert classify(result) == Status.Down

    def test_error_dns_failure_is_down(self):
        result = CheckResult(http_status=0, error="connecterror", total_ms=0.0)
        assert classify(result) == Status.Down

    def test_http_0_no_error_is_down(self):
        """HTTP status 0 with no error string should still be Down."""
        result = CheckResult(http_status=0, error=None, total_ms=0.0)
        assert classify(result) == Status.Down

    def test_http_200_with_error_is_down(self):
        """Even if HTTP 200, presence of an error means Down."""
        result = CheckResult(
            http_status=200, error="ssl_error", total_ms=100.0
        )
        assert classify(result) == Status.Down


class TestStatusName:
    """Test status_name() returns correct lowercase strings."""

    def test_up(self):
        assert status_name(Status.Up) == "up"

    def test_down(self):
        assert status_name(Status.Down) == "down"

    def test_unknown(self):
        assert status_name(Status.Unknown) == "unknown"
