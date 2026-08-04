import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# Under pytest, each test runs in its own event loop. A pooled asyncpg connection
# created in one loop cannot be reused in another, so disable pooling for tests.
if os.getenv("TESTING") == "1":
    engine = create_async_engine(settings.database_url, poolclass=NullPool, future=True)
else:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)

async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
