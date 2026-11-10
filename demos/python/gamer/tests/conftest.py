import pytest
from fastapi.testclient import TestClient
from gamer.app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())   # fresh in-memory state per test
