from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_JWT_SECRET = "change-me-to-a-random-64-char-string"

# Query params that libpq/psql accept in a connection URL but asyncpg does NOT —
# Neon (and other managed Postgres) hand out URLs containing these, and asyncpg
# raises on the unknown kwargs. We strip them from the URL and re-express TLS via
# connect args instead (see Settings.db_connect_args).
_LIBPQ_ONLY_QUERY_PARAMS = frozenset(
    {"sslmode", "channel_binding", "connect_timeout", "gssencmode", "options"}
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Deployment environment: "dev" (permissive defaults) or "production"
    # (fails fast on insecure config — see _guard_production below).
    env: str = "dev"

    # Database
    database_url: str = "postgresql+asyncpg://hrm:hrm@localhost:5432/hrm"

    @field_validator("database_url", mode="before")
    @classmethod
    def _ensure_async_driver(cls, v: str) -> str:
        """Managed platforms (Render/Neon) hand out `postgresql://` URLs.
        Our engine + Alembic both need the asyncpg driver."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Auth
    jwt_secret: str = "change-me-to-a-random-64-char-string"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # Cookies
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_domain: str = ""
    refresh_cookie_name: str = "hrm_refresh"

    # Rate limiting (per client IP). Disable in tests.
    rate_limit_enabled: bool = True
    login_rate_limit: str = "10/minute"
    sensitive_rate_limit: str = "5/minute"  # forgot / reset / accept-invite
    # Shared rate-limit storage. Empty => in-memory (correct only for a single
    # instance). On serverless / multi-instance, set to a Redis URI (e.g. Upstash
    # `rediss://default:<pwd>@<host>:<port>`) so per-IP counters are shared across
    # instances. Consumed by slowapi/limits as its storage backend.
    rate_limit_storage_uri: str = ""

    # File storage
    storage_backend: str = "db"  # "db" (in-Postgres) — swap for "s3" later
    max_photo_mb: int = 5
    max_document_mb: int = 15

    # Email
    email_provider: str = "console"  # "resend" | "console"
    resend_api_key: str = ""
    email_from: str = "HRM <noreply@zillaclinicals.com>"
    app_base_url: str = "http://localhost:5173"

    @property
    def cookie_domain_or_none(self) -> str | None:
        return self.cookie_domain or None

    @property
    def sqlalchemy_url(self) -> str:
        """`database_url` with libpq-only query params (sslmode, channel_binding,
        …) stripped so asyncpg can parse it. TLS and pooler tuning move to
        `db_connect_args`. Use this everywhere an engine is built."""
        parts = urlsplit(self.database_url)
        kept = [
            (k, v)
            for k, v in parse_qsl(parts.query, keep_blank_values=True)
            if k not in _LIBPQ_ONLY_QUERY_PARAMS
        ]
        return urlunsplit(parts._replace(query=urlencode(kept)))

    @property
    def db_connect_args(self) -> dict:
        """asyncpg connect args by target. For any non-local host we require TLS
        (Neon and most managed Postgres do) and set statement_cache_size=0 so a
        pooled PgBouncer endpoint can't raise 'prepared statement already exists'.
        Local Postgres/sqlite get no extra args."""
        host = (urlsplit(self.database_url).hostname or "").lower()
        if host in ("", "localhost", "127.0.0.1", "::1"):
            return {}
        return {"ssl": "require", "statement_cache_size": 0}

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        """Refuse to start a production process with insecure auth config."""
        if self.env.lower() != "production":
            return self
        problems: list[str] = []
        if self.jwt_secret == PLACEHOLDER_JWT_SECRET or len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be a strong random value of at least 32 chars")
        if not self.cookie_secure:
            problems.append("COOKIE_SECURE must be true (HTTPS) in production")
        if problems:
            raise ValueError(
                "Insecure production configuration (ENV=production):\n  - "
                + "\n  - ".join(problems)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
