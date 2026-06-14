from typing import TypedDict

import aiosqlite

from app.schemas.checks import CheckResult
from app.util.time import utc_now


class CheckRow(TypedDict):
    id: int
    monitor_id: int
    checked_at: str
    http_status: int | None
    response_time_ms: int
    success: int
    error_message: str | None


def row_to_check_row(row) -> CheckRow:
    return CheckRow(
        id=row["id"],
        monitor_id=row["monitor_id"],
        checked_at=row["checked_at"],
        http_status=row["http_status"],
        response_time_ms=row["response_time_ms"],
        success=row["success"],
        error_message=row["error_message"],
    )


async def insert_check(conn: aiosqlite.Connection, monitor_id: int, result: CheckResult) -> int:
    now = utc_now()
    cursor = await conn.execute(
        """INSERT INTO checks (monitor_id, checked_at, http_status, response_time_ms, success, error_message)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            monitor_id,
            now,
            result.http_status,
            result.response_time_ms,
            int(result.success),
            result.error_message,
        ),
    )
    await conn.commit()
    return cursor.lastrowid


async def list_checks(
    conn: aiosqlite.Connection, monitor_id: int, limit: int, offset: int
) -> tuple[list[CheckRow], int]:
    count_cursor = await conn.execute(
        "SELECT COUNT(*) FROM checks WHERE monitor_id = ?",
        (monitor_id,),
    )
    count_row = await count_cursor.fetchone()
    total = count_row[0]

    cursor = await conn.execute(
        """SELECT * FROM checks WHERE monitor_id = ?
           ORDER BY checked_at DESC LIMIT ? OFFSET ?""",
        (monitor_id, limit, offset),
    )
    rows = await cursor.fetchall()
    return [row_to_check_row(row) for row in rows], total


async def count_checks_for_monitor(conn: aiosqlite.Connection, monitor_id: int) -> int:
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM checks WHERE monitor_id = ?",
        (monitor_id,),
    )
    row = await cursor.fetchone()
    return row[0]
