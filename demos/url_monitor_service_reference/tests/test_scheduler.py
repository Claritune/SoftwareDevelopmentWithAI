import httpx
import pytest

from app.repositories.checks import count_checks_for_monitor
from app.repositories.monitors import get_monitor
from app.schemas.monitors import MonitorStatus
from app.services.scheduler import run_cycle
from tests.test_checker import mock_transport, seed_monitor


@pytest.mark.anyio
async def test_run_cycle_checks_due_monitors(db_conn, test_settings):
    monitor = await seed_monitor(db_conn, test_settings, check_interval_seconds=1)
    client = httpx.AsyncClient(transport=mock_transport(200))

    await run_cycle(db_conn, client, test_settings)
    await client.aclose()

    updated = await get_monitor(db_conn, monitor["id"])
    assert updated is not None
    assert updated["status"] == MonitorStatus.UP.value
    assert updated["last_checked_at"] is not None
    assert await count_checks_for_monitor(db_conn, monitor["id"]) == 1


@pytest.mark.anyio
async def test_run_cycle_skips_disabled(db_conn, test_settings):
    monitor = await seed_monitor(db_conn, test_settings, enabled=False)
    client = httpx.AsyncClient(transport=mock_transport(200))

    await run_cycle(db_conn, client, test_settings)
    await client.aclose()

    assert await count_checks_for_monitor(db_conn, monitor["id"]) == 0


@pytest.mark.anyio
async def test_run_cycle_respects_interval(db_conn, test_settings):
    from app.util.time import utc_now

    monitor = await seed_monitor(
        db_conn,
        test_settings,
        check_interval_seconds=60,
        last_checked_at=utc_now(),
    )
    client = httpx.AsyncClient(transport=mock_transport(200))

    await run_cycle(db_conn, client, test_settings)
    await client.aclose()

    assert await count_checks_for_monitor(db_conn, monitor["id"]) == 0


@pytest.mark.anyio
async def test_run_cycle_failure_then_recovery(db_conn, test_settings):
    monitor = await seed_monitor(
        db_conn, test_settings, failure_threshold=3, check_interval_seconds=1
    )
    fail_client = httpx.AsyncClient(transport=mock_transport(500))

    for _ in range(3):
        await db_conn.execute(
            "UPDATE monitors SET last_checked_at = NULL WHERE id = ?",
            (monitor["id"],),
        )
        await db_conn.commit()
        await run_cycle(db_conn, fail_client, test_settings)

    updated = await get_monitor(db_conn, monitor["id"])
    assert updated is not None
    assert updated["status"] == MonitorStatus.DOWN.value

    await db_conn.execute(
        "UPDATE monitors SET last_checked_at = NULL WHERE id = ?",
        (monitor["id"],),
    )
    await db_conn.commit()

    ok_client = httpx.AsyncClient(transport=mock_transport(200))
    await run_cycle(db_conn, ok_client, test_settings)
    await fail_client.aclose()
    await ok_client.aclose()

    recovered = await get_monitor(db_conn, monitor["id"])
    assert recovered is not None
    assert recovered["status"] == MonitorStatus.UP.value
    assert await count_checks_for_monitor(db_conn, monitor["id"]) == 4
