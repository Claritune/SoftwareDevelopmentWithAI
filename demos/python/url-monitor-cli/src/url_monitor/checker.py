from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass(frozen=True)
class CheckResult:
    url: str
    success: bool
    status_code: int | None
    response_time_ms: float | None
    error: str | None
    timestamp: datetime


def is_failure(result: CheckResult) -> bool:
    return not result.success


def check(url: str, timeout: int, client: httpx.Client | None = None) -> CheckResult:
    owns_client = client is None
    if owns_client:
        client = httpx.Client(follow_redirects=True)

    start = datetime.now(timezone.utc)
    try:
        response = client.get(url, timeout=timeout)
        elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        success = response.status_code < 400
        return CheckResult(
            url=url,
            success=success,
            status_code=response.status_code,
            response_time_ms=elapsed_ms,
            error=None,
            timestamp=start,
        )
    except httpx.RequestError as exc:
        return CheckResult(
            url=url,
            success=False,
            status_code=None,
            response_time_ms=None,
            error=str(exc),
            timestamp=start,
        )
    finally:
        if owns_client:
            client.close()
