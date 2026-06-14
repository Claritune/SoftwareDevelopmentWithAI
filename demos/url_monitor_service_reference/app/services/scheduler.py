import asyncio
import contextlib
import logging
from datetime import datetime, timezone

import aiosqlite
import httpx

from app.repositories.monitors import get_monitors_due_for_check
from app.schemas.monitors import MonitorRow
from app.services.checker import process_monitor_check
from app.settings import Settings

logger = logging.getLogger(__name__)


async def safe_check(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    monitor: MonitorRow,
) -> None:
    try:
        await process_monitor_check(conn, client, monitor)
    except Exception:
        logger.exception("Check failed for monitor %s", monitor["id"])


async def run_cycle(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    settings: Settings,
) -> None:
    now = datetime.now(timezone.utc)
    due = await get_monitors_due_for_check(conn, now)
    if not due:
        return
    async with asyncio.TaskGroup() as tg:
        for monitor in due:
            tg.create_task(safe_check(conn, client, monitor))


async def scheduler_loop(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    settings: Settings,
) -> None:
    while True:
        try:
            await run_cycle(conn, client, settings)
        except Exception:
            logger.exception("Scheduler cycle failed")
        await asyncio.sleep(settings.coordinator_tick_seconds)


async def start_scheduler(
    conn: aiosqlite.Connection,
    client: httpx.AsyncClient,
    settings: Settings,
) -> asyncio.Task:
    return asyncio.create_task(scheduler_loop(conn, client, settings))


async def stop_scheduler(task: asyncio.Task) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
