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

# Disable SQLAlchemy connection pooling when:
#   - Under pytest: each test runs in its own event loop, and a pooled asyncpg
#     connection created in one loop cannot be reused in another.
#   - On Vercel (serverless): each function invocation is short-lived and may run
#     in its own isolated instance. A per-instance pool would multiply across
#     concurrent cold starts and exhaust Postgres connections. NullPool opens and
#     closes one connection per checkout, which is the serverless-safe behavior.
#     (Point DATABASE_URL at a pooled/serverless Postgres endpoint — e.g. Neon or
#     Supabase's pooler — so the DB side tolerates many short connections.)
_connect_args = settings.db_connect_args

if os.getenv("TESTING") == "1" or os.getenv("VERCEL"):
    engine = create_async_engine(
        settings.sqlalchemy_url,
        poolclass=NullPool,
        connect_args=_connect_args,
        future=True,
    )
else:
    engine = create_async_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        connect_args=_connect_args,
        future=True,
    )

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
