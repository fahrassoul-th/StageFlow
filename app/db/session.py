from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

# pool_size/max_overflow are QueuePool (Postgres) options - SQLite engines
# default to NullPool, which rejects them outright. Only pass them for a
# real Postgres DATABASE_URL, so switching to sqlite+aiosqlite for local
# dev (as the README suggests) doesn't crash at import time.
_engine_kwargs = {}
if not settings.database_url.startswith("sqlite"):
    _engine_kwargs = {"pool_size": 10, "max_overflow": 20}

async_engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """One session per request; commits once the route handler succeeds,
    rolls back on any exception. Repositories only flush/refresh - they
    never call commit() themselves."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
