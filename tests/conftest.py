import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models  # noqa: F401  (populates Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.role import RoleEnum

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Function-scoped on purpose (the fil rouge's own conftest.py uses a
    session-scoped engine): a fresh empty database per test means no test
    can leak state into another regardless of run order, at the cost of
    recreating the schema each time - negligible for an in-memory SQLite."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Session for repository-level tests (no HTTP)."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncClient:
    """HTTP client with get_db overridden to use the test database."""
    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def register_and_login(client: AsyncClient):
    """Register + log in a user of the given role, returning
    (user_dict, auth_headers) for quick use in integration tests."""

    async def _do(
        username: str, role: RoleEnum, password: str = "secret123"
    ) -> tuple[dict, dict]:
        response = await client.post(
            "/auth/register",
            json={
                "username": username,
                "email": f"{username}@x.com",
                "password": password,
                "full_name": username,
                "role": role.value,
            },
        )
        assert response.status_code == 201, response.text
        user = response.json()

        response = await client.post(
            "/auth/login", data={"username": username, "password": password}
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]

        return user, {"Authorization": f"Bearer {token}"}

    return _do
