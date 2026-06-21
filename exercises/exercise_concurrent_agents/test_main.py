import pytest
from fastapi.testclient import TestClient
from main import app, tasks, next_id
import main


@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory state between tests."""
    tasks.clear()
    main.next_id = 1
    yield
    tasks.clear()
    main.next_id = 1


client = TestClient(app)


# --- Issue 1: ID never increments ---

def test_create_multiple_tasks_have_unique_ids():
    r1 = client.post("/tasks", json={"title": "Task A"})
    r2 = client.post("/tasks", json={"title": "Task B"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"], "Each task must get a unique ID"


def test_two_tasks_are_both_stored():
    client.post("/tasks", json={"title": "Task A"})
    client.post("/tasks", json={"title": "Task B"})
    r = client.get("/tasks")
    assert r.json()["count"] == 2, "Both tasks must be stored"


# --- Issue 2: priority filter returns wrong tasks ---

def test_filter_by_priority_returns_only_matching_tasks():
    client.post("/tasks", json={"title": "Low", "priority": 1})
    client.post("/tasks", json={"title": "High", "priority": 3})
    r = client.get("/tasks?priority=3")
    data = r.json()
    assert all(t["priority"] == 3 for t in data["tasks"]), (
        "Filtering by priority=3 should return only high-priority tasks"
    )


def test_filter_by_priority_excludes_other_priorities():
    client.post("/tasks", json={"title": "Low", "priority": 1})
    client.post("/tasks", json={"title": "High", "priority": 3})
    r = client.get("/tasks?priority=1")
    data = r.json()
    assert data["count"] == 1
    assert data["tasks"][0]["title"] == "Low"


# --- Issue 3: list order should be newest first ---

def test_list_tasks_returns_newest_first():
    client.post("/tasks", json={"title": "First"})
    client.post("/tasks", json={"title": "Second"})
    client.post("/tasks", json={"title": "Third"})
    r = client.get("/tasks")
    titles = [t["title"] for t in r.json()["tasks"]]
    assert titles == ["Third", "Second", "First"], (
        "Tasks should be returned newest first (highest ID first)"
    )


# --- Issue 4: priority validation rejects valid value 3 ---

def test_update_priority_to_high_is_accepted():
    r = client.post("/tasks", json={"title": "My Task"})
    task_id = r.json()["id"]
    r2 = client.patch(f"/tasks/{task_id}", json={"priority": 3})
    assert r2.status_code == 200, (
        f"Priority 3 (high) should be valid, got {r2.status_code}: {r2.text}"
    )
    assert r2.json()["priority"] == 3


def test_update_priority_above_3_is_rejected():
    r = client.post("/tasks", json={"title": "My Task"})
    task_id = r.json()["id"]
    r2 = client.patch(f"/tasks/{task_id}", json={"priority": 4})
    assert r2.status_code == 422


# --- Issue 5: delete does not actually remove the task ---

def test_delete_removes_task():
    r = client.post("/tasks", json={"title": "Doomed Task"})
    task_id = r.json()["id"]
    del_r = client.delete(f"/tasks/{task_id}")
    assert del_r.status_code == 200
    get_r = client.get(f"/tasks/{task_id}")
    assert get_r.status_code == 404, "Deleted task must no longer be retrievable"


def test_delete_reduces_task_count():
    client.post("/tasks", json={"title": "Task A"})
    r2 = client.post("/tasks", json={"title": "Task B"})
    task_id = r2.json()["id"]
    client.delete(f"/tasks/{task_id}")
    r = client.get("/tasks")
    assert r.json()["count"] == 1
