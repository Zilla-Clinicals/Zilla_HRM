import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.rate_limit import limiter
from app.routers import (
    analytics,
    audit,
    auth,
    dashboard,
    documents,
    employees,
    goals,
    kpis,
    reviews,
    surveys,
    users,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Zilla Clinicals HRM",
    version="0.1.0",
    description="HR management + twice-yearly performance reviews.",
)

# Rate limiting: decorated routes enforce per-IP limits; this returns 429 on breach.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(employees.router)
app.include_router(documents.router)
app.include_router(goals.router)
app.include_router(kpis.router)
app.include_router(reviews.router)
app.include_router(surveys.router)
app.include_router(dashboard.router)
app.include_router(audit.router)
app.include_router(analytics.router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
async def health_db():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "db": "reachable"}
