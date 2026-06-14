from typing import TypedDict

import aiosqlite

from app.util.time import utc_now


class TransitionRow(TypedDict):
    id: int
    monitor_id: int
    transitioned_at: str
    from_status: str
    to_status: str
    check_id: int


def row_to_transition_row(row) -> TransitionRow:
    return TransitionRow(
        id=row["id"],
        monitor_id=row["monitor_id"],
        transitioned_at=row["transitioned_at"],
        from_status=row["from_status"],
        to_status=row["to_status"],
        check_id=row["check_id"],
    )


async def insert_transition(
    conn: aiosqlite.Connection,
    monitor_id: int,
    from_status: str,
    to_status: str,
    check_id: int,
) -> None:
    await conn.execute(
        """INSERT INTO transitions (monitor_id, transitioned_at, from_status, to_status, check_id)
           VALUES (?, ?, ?, ?, ?)""",
        (monitor_id, utc_now(), from_status, to_status, check_id),
    )
    await conn.commit()


async def list_transitions(
    conn: aiosqlite.Connection, monitor_id: int, limit: int, offset: int
) -> tuple[list[TransitionRow], int]:
    count_cursor = await conn.execute(
        "SELECT COUNT(*) FROM transitions WHERE monitor_id = ?",
        (monitor_id,),
    )
    count_row = await count_cursor.fetchone()
    total = count_row[0]

    cursor = await conn.execute(
        """SELECT * FROM transitions WHERE monitor_id = ?
           ORDER BY transitioned_at DESC LIMIT ? OFFSET ?""",
        (monitor_id, limit, offset),
    )
    rows = await cursor.fetchall()
    return [row_to_transition_row(row) for row in rows], total
