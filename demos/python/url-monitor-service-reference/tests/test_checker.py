import httpx
import pytest

from app.repositories.monitors import get_monitor
from app.schemas.monitors import MonitorCreate, MonitorStatus
from app.services.checker import process_monitor_check
from app.settings import Settings


async def seed_monitor(conn, settings: Settings, **kwargs) -> dict:
    from app.repositories.monitors import create_monitor

    url = kwargs.pop("url", "https://example.com")
    status = kwargs.pop("status", None)
    consecutive_failures = kwargs.pop("consecutive_failures", None)
    last_checked_at = kwargs.pop("last_checked_at", None)

    data = MonitorCreate(url=url, **kwargs)
    row = await create_monitor(conn, data, settings)
    updates = []
    values = []
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    if consecutive_failures is not None:
        updates.append("consecutive_failures = ?")
        values.append(consecutive_failures)
    if last_checked_at is not None:
        updates.append("last_checked_at = ?")
        values.append(last_checked_at)
    if updates:
        values.append(row["id"])
        await conn.execute(
            f"UPDATE monitors SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        await conn.commit()
        updated = await get_monitor(conn, row["id"])
        assert updated is not None
        return updated
    return row


def mock_transport(status_code: int) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    return httpx.MockTransport(handler)


@pytest.mark.anyio
async def test_success_unknown_to_up(db_conn, test_settings):
    monitor = await seed_monitor(db_conn, test_settings)
    client = httpx.AsyncClient(transport=mock_transport(200))

    await process_monitor_check(db_conn, client, monitor)
    await client.aclose()

    updated = await get_monitor(db_conn, monitor["id"])
    assert updated is not None
    assert updated["status"] == MonitorStatus.UP.value
    assert updated["consecutive_failures"] == 0
    assert updated["last_checked_at"] is not None

    cursor = await db_conn.execute("SELECT COUNT(*) FROM checks WHERE monitor_id = ?", (monitor["id"],))
    assert (await cursor.fetchone())[0] == 1

    cursor = await db_conn.execute(
        "SELECT COUNT(*) FROM transitions WHERE monitor_id = ?", (monitor["id"],)
    )
    assert (await cursor.fetchone())[0] == 1


@pytest.mark.anyio
async def test_failure_threshold_unknown_to_down(db_conn, test_settings):
    monitor = await seed_monitor(db_conn, test_settings, failure_threshold=3)
    client = httpx.AsyncClient(transport=mock_transport(500))

    for _ in range(3):
        monitor = await get_monitor(db_conn, monitor["id"])
        assert monitor is not None
        await process_monitor_check(db_conn, client, monitor)
    await client.aclose()

    updated = await get_monitor(db_conn, monitor["id"])
    assert updated is not None
    assert updated["status"] == MonitorStatus.DOWN.value

    cursor = await db_conn.execute(
        "SELECT COUNT(*) FROM transitions WHERE monitor_id = ?", (monitor["id"],)
    )
    assert (await cursor.fetchone())[0] == 1


@pytest.mark.anyio
async def test_down_to_up_on_single_success(db_conn, test_settings):
    monitor = await seed_monitor(
        db_conn,
        test_settings,
        status=MonitorStatus.DOWN.value,
        consecutive_failures=3,
    )
    client = httpx.AsyncClient(transport=mock_transport(200))

    await process_monitor_check(db_conn, client, monitor)
    await client.aclose()

    updated = await get_monitor(db_conn, monitor["id"])
    assert updated is not None
    assert updated["status"] == MonitorStatus.UP.value
    assert updated["consecutive_failures"] == 0

    cursor = await db_conn.execute(
        "SELECT to_status FROM transitions WHERE monitor_id = ? ORDER BY id DESC LIMIT 1",
        (monitor["id"],),
    )
    row = await cursor.fetchone()
    assert row[0] == MonitorStatus.UP.value


@pytest.mark.anyio
async def test_up_stays_up_below_threshold(db_conn, test_settings):
    monitor = await seed_monitor(
        db_conn,
        test_settings,
        status=MonitorStatus.UP.value,
        failure_threshold=3,
    )
    client = httpx.AsyncClient(transport=mock_transport(500))

    for _ in range(2):
        monitor = await get_monitor(db_conn, monitor["id"])
        assert monitor is not None
        await process_monitor_check(db_conn, client, monitor)
    await client.aclose()

    updated = await get_monitor(db_conn, monitor["id"])
    assert updated is not None
    assert updated["status"] == MonitorStatus.UP.value
    assert updated["consecutive_failures"] == 2

    cursor = await db_conn.execute(
        "SELECT COUNT(*) FROM transitions WHERE monitor_id = ?", (monitor["id"],)
    )
    assert (await cursor.fetchone())[0] == 0
