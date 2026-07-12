import httpx
import pytest

from app.repositories.checks import count_checks_for_monitor
from app.services.scheduler import run_cycle
from tests.test_checker import mock_transport


@pytest.mark.anyio
async def test_create_monitor_check_via_scheduler(client, db_conn, test_settings):
    create_resp = await client.post(
        "/api/v1/monitors",
        json={
            "url": "https://example.com",
            "failure_threshold": 3,
            "check_interval_seconds": 2,
        },
    )
    monitor_id = create_resp.json()["id"]
    http_client = httpx.AsyncClient(transport=mock_transport(500))

    for _ in range(3):
        await db_conn.execute(
            "UPDATE monitors SET last_checked_at = NULL WHERE id = ?",
            (monitor_id,),
        )
        await db_conn.commit()
        await run_cycle(db_conn, http_client, test_settings)
    await http_client.aclose()

    detail_resp = await client.get(f"/api/v1/monitors/{monitor_id}")
    assert detail_resp.json()["status"] == "DOWN"

    checks_resp = await client.get(f"/api/v1/monitors/{monitor_id}/checks")
    assert checks_resp.json()["total"] == 3


@pytest.mark.anyio
async def test_disable_stops_checks(client, db_conn, test_settings):
    create_resp = await client.post(
        "/api/v1/monitors",
        json={"url": "https://example.org", "check_interval_seconds": 1},
    )
    monitor_id = create_resp.json()["id"]
    http_client = httpx.AsyncClient(transport=mock_transport(200))

    await run_cycle(db_conn, http_client, test_settings)
    count_after_first = await count_checks_for_monitor(db_conn, monitor_id)
    assert count_after_first == 1

    await client.patch(f"/api/v1/monitors/{monitor_id}", json={"enabled": False})
    await db_conn.execute(
        "UPDATE monitors SET last_checked_at = NULL WHERE id = ?",
        (monitor_id,),
    )
    await db_conn.commit()
    await run_cycle(db_conn, http_client, test_settings)
    await http_client.aclose()

    assert await count_checks_for_monitor(db_conn, monitor_id) == count_after_first


@pytest.mark.anyio
async def test_delete_monitor_removes_history(client, db_conn, test_settings):
    create_resp = await client.post(
        "/api/v1/monitors",
        json={"url": "https://example.net", "check_interval_seconds": 1},
    )
    monitor_id = create_resp.json()["id"]
    http_client = httpx.AsyncClient(transport=mock_transport(200))

    await run_cycle(db_conn, http_client, test_settings)
    await http_client.aclose()

    delete_resp = await client.delete(f"/api/v1/monitors/{monitor_id}")
    assert delete_resp.status_code == 204

    checks_resp = await client.get(f"/api/v1/monitors/{monitor_id}/checks")
    assert checks_resp.status_code == 404
