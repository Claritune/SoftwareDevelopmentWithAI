import pytest


@pytest.mark.anyio
async def test_hello_world(client):
    resp = await client.get("/api/v1/monitors/hello-world")
    assert resp.status_code == 200
    assert resp.json() == {"message": "hello-world"}


@pytest.mark.anyio
async def test_create_monitor_returns_unknown_status(client):
    resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "UNKNOWN"
    assert data["url"] == "https://example.com/"


@pytest.mark.anyio
async def test_list_monitors_paginated(client):
    await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    await client.post("/api/v1/monitors", json={"url": "https://example.org"})

    resp = await client.get("/api/v1/monitors", params={"limit": 1, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 1
    assert data["limit"] == 1
    assert data["offset"] == 0


@pytest.mark.anyio
async def test_get_monitor_not_found(client):
    resp = await client.get("/api/v1/monitors/999")
    assert resp.status_code == 404
    assert resp.json() == {"error": "NOT_FOUND", "message": "Monitor 999 not found"}


@pytest.mark.anyio
async def test_update_monitor(client):
    create_resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    monitor_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/monitors/{monitor_id}",
        json={"display_name": "Example", "enabled": False},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["display_name"] == "Example"
    assert data["enabled"] is False


@pytest.mark.anyio
async def test_delete_monitor(client):
    create_resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    monitor_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/monitors/{monitor_id}")
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/monitors/{monitor_id}")
    assert get_resp.status_code == 404


@pytest.mark.anyio
async def test_create_monitor_with_tags(client):
    resp = await client.post(
        "/api/v1/monitors",
        json={"url": "https://example.com", "tags": ["prod", "api"]},
    )
    assert resp.status_code == 201
    assert resp.json()["tags"] == ["prod", "api"]


@pytest.mark.anyio
async def test_create_monitor_without_tags_returns_empty_list(client):
    resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    assert resp.status_code == 201
    assert resp.json()["tags"] == []


@pytest.mark.anyio
async def test_update_monitor_tags(client):
    create_resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    monitor_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/monitors/{monitor_id}",
        json={"tags": ["staging"]},
    )
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["staging"]


@pytest.mark.anyio
async def test_duplicate_url_returns_conflict(client):
    await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    resp = await client.post("/api/v1/monitors", json={"url": "https://example.com"})
    assert resp.status_code == 409
    assert resp.json()["error"] == "CONFLICT"
