import httpx
import pytest
from httpx import ASGITransport

from app.db.connection import close_db, init_schema, open_db
from app.main import create_app
from app.settings import Settings, get_settings


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(database_path=str(tmp_path / "test.db"))


@pytest.fixture
async def db_conn(test_settings):
    conn = await open_db(test_settings.database_path)
    await init_schema(conn)
    yield conn
    await close_db(conn)


@pytest.fixture
async def app(test_settings, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", test_settings.database_path)
    get_settings.cache_clear()
    application = create_app()
    yield application
    get_settings.cache_clear()


@pytest.fixture
async def client(app):
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
