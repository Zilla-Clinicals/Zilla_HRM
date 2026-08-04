import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: int, role: str) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_ttl_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    # Guard against token-purpose confusion: only real access tokens are accepted
    # here. The MFA-challenge token (purpose="mfa") shares the signing secret but
    # must NOT authorize protected routes — that would bypass the second factor.
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def create_mfa_token(user_id: int) -> str:
    """Short-lived token proving the password step passed, pending a 2FA code."""
    now = _now()
    payload = {
        "sub": str(user_id),
        "purpose": "mfa",
        "type": "mfa",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_mfa_token(token: str) -> int:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("purpose") != "mfa":
        raise jwt.InvalidTokenError("Not an MFA token")
    return int(payload["sub"])


def generate_raw_token(nbytes: int = 32) -> str:
    """Opaque URL-safe token handed out in emails / refresh cookies."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw: str) -> str:
    """sha256 hex digest of an opaque token; only this is stored server-side."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def refresh_expiry() -> datetime:
    return _now() + timedelta(days=settings.refresh_token_ttl_days)
