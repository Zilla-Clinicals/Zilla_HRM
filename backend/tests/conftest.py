"""Test harness.

Uses the real Postgres (the `postgres:16` container from the README) but on a
dedicated `hrm_test` database that is created fresh and migrated once per session.
Tables are truncated between tests, and a fresh hr_admin is seeded each test.
"""
import os

# Point the app at the test database BEFORE anything imports app.config.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://hrm:hrm@localhost:5432/hrm_test"
)
os.environ.setdefault("EMAIL_PROVIDER", "console")
os.environ.setdefault("JWT_SECRET", "test-secret-please-ignore-0123456789abcdef")
os.environ["TESTING"] = "1"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # don't throttle the test suite's many logins

import asyncpg  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from alembic.config import Config  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from alembic import command  # noqa: E402

ADMIN_EMAIL = "admin@zillaclinicals.com"
ADMIN_PASSWORD = "AdminPass123!"

TABLES = [
    "survey_answers",
    "survey_responses",
    "survey_assignments",
    "survey_questions",
    "surveys",
    "document_blobs",
    "employee_documents",
    "goal_checkins",
    "goals",
    "review_scores",
    "review_assignments",
    "review_cycles",
    "kpis",
    "kpi_categories",
    "audit_logs",
    "employees",
    "recovery_codes",
    "refresh_tokens",
    "password_resets",
    "invitations",
    "users",
]


async def _recreate_test_db() -> None:
    admin = await asyncpg.connect("postgresql://hrm:hrm@localhost:5432/hrm")
    try:
        await admin.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = 'hrm_test' AND pid <> pg_backend_pid()"
        )
        await admin.execute("DROP DATABASE IF EXISTS hrm_test")
        await admin.execute("CREATE DATABASE hrm_test")
    finally:
        await admin.close()


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    import asyncio

    asyncio.run(_recreate_test_db())
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    yield


@pytest_asyncio.fixture(autouse=True)
async def _clean_and_seed():
    """Truncate all tables and seed a fresh hr_admin + the KPI framework."""
    from decimal import Decimal

    from sqlalchemy import text

    from app.auth.passwords import hash_password
    from app.db import async_session_factory
    from app.models._base import Role
    from app.models.employees import Employee
    from app.models.kpis import Kpi, KpiCategory
    from app.models.users import User
    from app.seed_data import CATEGORIES, KPIS

    async with async_session_factory() as db:
        await db.execute(
            text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
        )
        admin = User(
            email=ADMIN_EMAIL,
            role=Role.admin,
            is_active=True,
            password_hash=hash_password(ADMIN_PASSWORD),
        )
        db.add(admin)
        await db.flush()
        db.add(Employee(user_id=admin.id, full_name="HR Admin", job_title="HR"))
        for name, weight in CATEGORIES:
            db.add(KpiCategory(name=name, weight=Decimal(weight)))
        for category, name, description, measurement, target in KPIS:
            db.add(
                Kpi(
                    name=name,
                    category=category,
                    description=description,
                    measurement=measurement,
                    target=target,
                )
            )
        await db.commit()
    yield


@pytest_asyncio.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest_asyncio.fixture
async def admin_token(client):
    return await _login(client, ADMIN_EMAIL, ADMIN_PASSWORD)


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
