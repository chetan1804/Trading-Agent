import httpx
import pytest
from app.config import Settings
from app.main import create_app
from fastapi import FastAPI


class FakeConnection:
    async def __aenter__(self) -> "FakeConnection":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def execute(self, query: object) -> None:
        return None


class FakeDatabase:
    def connect(self) -> FakeConnection:
        return FakeConnection()


class FakeRedis:
    async def ping(self) -> bool:
        return True


async def get_client(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def app() -> FastAPI:
    application = create_app(Settings())
    application.state.database_engine = FakeDatabase()
    application.state.redis_client = FakeRedis()
    return application


@pytest.mark.asyncio
async def test_liveness_is_ok(app: FastAPI) -> None:
    async with await get_client(app) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_requires_database_and_redis(app: FastAPI) -> None:
    async with await get_client(app) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}


@pytest.mark.asyncio
async def test_readiness_returns_unavailable_when_redis_is_down(app: FastAPI) -> None:
    class UnavailableRedis:
        async def ping(self) -> bool:
            from redis.exceptions import ConnectionError

            raise ConnectionError("private connection details")

    app.state.redis_client = UnavailableRedis()
    async with await get_client(app) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {"database": "ok", "redis": "unavailable"},
    }
    assert "private connection details" not in response.text
