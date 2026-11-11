from contextlib import asynccontextmanager

import httpx
import pytest
from fakes import FakeGame

from gamer.app import create_app


@asynccontextmanager
async def _client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def client():
    async with _client(create_app()) as c:
        yield c


@pytest.fixture
async def fake_client():
    async with _client(create_app(games={"fake": FakeGame()})) as c:
        yield c
