"""HTTP checking and status classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import httpx

from url_monitor.config import UrlSpec


class Status(Enum):
    Unknown = "unknown"
    Up = "up"
    Down = "down"


@dataclass
class CheckResult:
    http_status: int = 0
    error: str | None = None
    total_ms: float = 0.0


def classify(result: CheckResult) -> Status:
    """Up only if no error AND http_status == 200. Everything else = Down."""
    if result.error is None and result.http_status == 200:
        return Status.Up
    return Status.Down


def status_name(status: Status) -> str:
    """Return lowercase status string."""
    return status.value


def _error_key(exc: Exception) -> str:
    """Map httpx exceptions to stable error key strings."""
    if isinstance(exc, httpx.TimeoutException):
        return "connection_timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connection_refused"
    if isinstance(exc, httpx.TooManyRedirects):
        return "too_many_redirects"
    return type(exc).__name__.lower()


def check(spec: UrlSpec, client: httpx.Client) -> CheckResult:
    """Perform an HTTP GET check against the given URL spec."""
    try:
        response = client.get(spec.url, timeout=spec.timeout_seconds)
        elapsed_ms = response.elapsed.total_seconds() * 1000
        return CheckResult(
            http_status=response.status_code,
            error=None,
            total_ms=elapsed_ms,
        )
    except httpx.HTTPError as exc:
        return CheckResult(
            http_status=0,
            error=_error_key(exc),
            total_ms=0.0,
        )
    except Exception as exc:
        return CheckResult(
            http_status=0,
            error=type(exc).__name__.lower(),
            total_ms=0.0,
        )
