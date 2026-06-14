import pytest

from app.schemas.checks import CheckResult
from app.repositories.checks import insert_check
from app.repositories.transitions import insert_transition


@pytest.mark.anyio
async def test_list_checks_empty(client):
    create_resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    monitor_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/monitors/{monitor_id}/checks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.anyio
async def test_list_checks_after_manual_insert(client, db_conn):
    create_resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    monitor_id = create_resp.json()["id"]

    await insert_check(
        db_conn,
        monitor_id,
        CheckResult(success=True, http_status=200, response_time_ms=42, error_message=None),
    )

    resp = await client.get(f"/api/v1/monitors/{monitor_id}/checks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["http_status"] == 200
    assert data["items"][0]["success"] is True


@pytest.mark.anyio
async def test_list_transitions(client, db_conn):
    create_resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    monitor_id = create_resp.json()["id"]

    check_id = await insert_check(
        db_conn,
        monitor_id,
        CheckResult(success=True, http_status=200, response_time_ms=10, error_message=None),
    )
    await insert_transition(db_conn, monitor_id, "UNKNOWN", "UP", check_id)

    resp = await client.get(f"/api/v1/monitors/{monitor_id}/transitions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["from_status"] == "UNKNOWN"
    assert data["items"][0]["to_status"] == "UP"


@pytest.mark.anyio
async def test_status_summary(client):
    await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    await client.post("/api/v1/monitors", json={"url": "https://example.org"})

    resp = await client.get("/api/v1/status/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["unknown"] == 2
    assert len(data["monitors"]) == 2


@pytest.mark.anyio
async def test_checks_not_found_monitor(client):
    resp = await client.get("/api/v1/monitors/999/checks")
    assert resp.status_code == 404
