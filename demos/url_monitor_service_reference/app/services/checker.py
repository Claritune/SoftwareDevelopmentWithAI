import time

import aiosqlite
import httpx

from app.repositories.checks import insert_check
from app.repositories.transitions import insert_transition
from app.schemas.checks import CheckResult
from app.schemas.monitors import MonitorRow, MonitorStatus
from app.util.time import utc_now


async def check_url(client: httpx.AsyncClient, url: str, timeout: float) -> CheckResult:
    start = time.perf_counter()
    try:
        resp = await client.get(url, timeout=timeout)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        success = resp.status_code < 400
        return CheckResult(
            success=success,
            http_status=resp.status_code,
            response_time_ms=elapsed_ms,
            error_message=None if success else f"HTTP {resp.status_code}",
        )
    except httpx.TimeoutException:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return CheckResult(
            success=False,
            http_status=None,
            response_time_ms=elapsed_ms,
            error_message="Request timed out",
        )
    except httpx.RequestError as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return CheckResult(
            success=False,
            http_status=None,
            response_time_ms=elapsed_ms,
            error_message=str(exc),
        )


async def update_monitor_after_check(
    conn: aiosqlite.Connection,
    monitor_id: int,
    status: str,
    consecutive_failures: int,
    checked_at: str,
) -> None:
    await conn.execute(
        """UPDATE monitors SET status = ?, consecutive_failures = ?,
           last_checked_at = ?, updated_at = ? WHERE id = ?""",
        (status, consecutive_failures, checked_at, utc_now(), monitor_id),
    )
    await conn.commit()


async def process_monitor_check(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    monitor: MonitorRow,
) -> None:
    result = await check_url(client, monitor["url"], float(monitor["timeout_seconds"]))
    check_id = await insert_check(conn, monitor["id"], result)

    status = monitor["status"]
    consecutive = monitor["consecutive_failures"]
    threshold = monitor["failure_threshold"]
    new_status = status
    checked_at = utc_now()

    if result.success:
        consecutive = 0
        if status != MonitorStatus.UP.value:
            new_status = MonitorStatus.UP.value
            await insert_transition(conn, monitor["id"], status, new_status, check_id)
    else:
        consecutive += 1
        if consecutive >= threshold and status in (
            MonitorStatus.UP.value,
            MonitorStatus.UNKNOWN.value,
        ):
            new_status = MonitorStatus.DOWN.value
            await insert_transition(conn, monitor["id"], status, new_status, check_id)

    await update_monitor_after_check(conn, monitor["id"], new_status, consecutive, checked_at)
