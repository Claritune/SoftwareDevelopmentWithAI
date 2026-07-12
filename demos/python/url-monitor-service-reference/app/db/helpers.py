async def last_insert_id(conn) -> int:
    cursor = await conn.execute("SELECT last_insert_rowid()")
    row = await cursor.fetchone()
    return row[0]
