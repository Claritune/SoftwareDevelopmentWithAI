"""Stdout logging, transition emission, and timestamp utilities."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from url_monitor.checker import CheckResult, Status, status_name


def iso8601_now() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_info(msg: str) -> None:
    """Log an informational message to stdout."""
    ts = iso8601_now()
    print(f"{ts} {msg}", flush=True)


def log_error(msg: str) -> None:
    """Log an error message to stderr."""
    ts = iso8601_now()
    print(f"{ts} ERROR {msg}", file=sys.stderr, flush=True)


def _result_detail(result: CheckResult) -> str:
    """Format check result detail string."""
    if result.error is not None:
        return f"(error: {result.error})"
    return f"(HTTP {result.http_status}, {result.total_ms:.0f}ms)"


def emit_transition(
    url: str, prev: Status, now: Status, result: CheckResult
) -> None:
    """Emit a status transition notification."""
    status_label = status_name(now).upper()
    detail = _result_detail(result)
    ts = iso8601_now()
    line = f"{ts} {status_label:<5} {url}  {detail}"
    print(line, flush=True)


def log_check(url: str, status: Status, result: CheckResult) -> None:
    """Log a check result (verbose mode)."""
    status_label = status_name(status).upper()
    detail = _result_detail(result)
    log_info(f"{status_label:<5} {url}  {detail}")
