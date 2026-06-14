from datetime import datetime

import aiosqlite

from app.db.helpers import last_insert_id
from app.schemas.monitors import (
    MonitorCreate,
    MonitorRow,
    MonitorStatus,
    MonitorUpdate,
    row_to_monitor_row,
)
from app.settings import Settings
from app.util.time import utc_now


async def create_monitor(conn: aiosqlite.Connection, data: MonitorCreate, settings: Settings) -> MonitorRow:
    now = utc_now()
    await conn.execute(
        """INSERT INTO monitors (url, display_name, enabled, check_interval_seconds,
           timeout_seconds, failure_threshold, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(data.url),
            data.display_name,
            int(data.enabled),
            data.check_interval_seconds or settings.default_check_interval_seconds,
            data.timeout_seconds or settings.default_timeout_seconds,
            data.failure_threshold or settings.default_failure_threshold,
            MonitorStatus.UNKNOWN.value,
            now,
            now,
        ),
    )
    await conn.commit()
    monitor_id = await last_insert_id(conn)
    row = await get_monitor(conn, monitor_id)
    assert row is not None
    return row


async def list_monitors(
    conn: aiosqlite.Connection, limit: int, offset: int
) -> tuple[list[MonitorRow], int]:
    count_cursor = await conn.execute("SELECT COUNT(*) FROM monitors")
    count_row = await count_cursor.fetchone()
    total = count_row[0]

    cursor = await conn.execute(
        "SELECT * FROM monitors ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    )
    rows = await cursor.fetchall()
    return [row_to_monitor_row(row) for row in rows], total


async def get_monitor(conn: aiosqlite.Connection, monitor_id: int) -> MonitorRow | None:
    cursor = await conn.execute("SELECT * FROM monitors WHERE id = ?", (monitor_id,))
    row = await cursor.fetchone()
    if row is None:
        return None
    return row_to_monitor_row(row)


async def update_monitor(
    conn: aiosqlite.Connection, monitor_id: int, data: MonitorUpdate
) -> MonitorRow | None:
    existing = await get_monitor(conn, monitor_id)
    if existing is None:
        return None

    fields: list[str] = []
    values: list[object] = []

    if data.url is not None:
        fields.append("url = ?")
        values.append(str(data.url))
    if data.display_name is not None:
        fields.append("display_name = ?")
        values.append(data.display_name)
    if data.check_interval_seconds is not None:
        fields.append("check_interval_seconds = ?")
        values.append(data.check_interval_seconds)
    if data.timeout_seconds is not None:
        fields.append("timeout_seconds = ?")
        values.append(data.timeout_seconds)
    if data.failure_threshold is not None:
        fields.append("failure_threshold = ?")
        values.append(data.failure_threshold)
    if data.enabled is not None:
        fields.append("enabled = ?")
        values.append(int(data.enabled))

    if not fields:
        return existing

    fields.append("updated_at = ?")
    values.append(utc_now())
    values.append(monitor_id)

    await conn.execute(
        f"UPDATE monitors SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    await conn.commit()
    return await get_monitor(conn, monitor_id)


async def delete_monitor(conn: aiosqlite.Connection, monitor_id: int) -> bool:
    cursor = await conn.execute("DELETE FROM monitors WHERE id = ?", (monitor_id,))
    await conn.commit()
    return cursor.rowcount > 0


async def list_enabled_monitors(conn: aiosqlite.Connection) -> list[MonitorRow]:
    cursor = await conn.execute("SELECT * FROM monitors WHERE enabled = 1")
    rows = await cursor.fetchall()
    return [row_to_monitor_row(row) for row in rows]


def is_monitor_due(monitor: MonitorRow, now: datetime) -> bool:
    if monitor["last_checked_at"] is None:
        return True
    last = datetime.fromisoformat(monitor["last_checked_at"])
    elapsed = (now - last).total_seconds()
    return elapsed >= monitor["check_interval_seconds"]


async def get_monitors_due_for_check(conn: aiosqlite.Connection, now: datetime) -> list[MonitorRow]:
    enabled = await list_enabled_monitors(conn)
    return [m for m in enabled if is_monitor_due(m, now)]


async def get_status_summary(conn: aiosqlite.Connection) -> dict:
    cursor = await conn.execute(
        """SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status = 'UP' THEN 1 ELSE 0 END) AS up,
            SUM(CASE WHEN status = 'DOWN' THEN 1 ELSE 0 END) AS down,
            SUM(CASE WHEN status = 'UNKNOWN' THEN 1 ELSE 0 END) AS unknown
           FROM monitors"""
    )
    counts = await cursor.fetchone()

    cursor = await conn.execute(
        "SELECT id, url, status, consecutive_failures FROM monitors ORDER BY id"
    )
    rows = await cursor.fetchall()

    return {
        "total": counts["total"],
        "up": counts["up"] or 0,
        "down": counts["down"] or 0,
        "unknown": counts["unknown"] or 0,
        "monitors": [
            {
                "id": row["id"],
                "url": row["url"],
                "status": row["status"],
                "consecutive_failures": row["consecutive_failures"],
            }
            for row in rows
        ],
    }
