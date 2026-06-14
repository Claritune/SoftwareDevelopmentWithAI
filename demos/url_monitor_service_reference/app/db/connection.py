from pathlib import Path

import aiosqlite

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def open_db(path: str) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_schema(conn: aiosqlite.Connection) -> None:
    ddl = SCHEMA_PATH.read_text()
    await conn.executescript(ddl)
    await conn.commit()


async def close_db(conn: aiosqlite.Connection) -> None:
    await conn.close()
