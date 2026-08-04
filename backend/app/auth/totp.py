"""TOTP (authenticator-app) two-factor helpers + one-time recovery codes."""
import hashlib
import secrets
import time

import pyotp

ISSUER = "Zilla Clinicals HRM"
_WINDOW = 1  # tolerate ±30s of clock drift


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str) -> str:
    """otpauth:// URI that authenticator apps turn into a QR code."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=ISSUER)


def verify_totp(secret: str | None, code: str) -> bool:
    return match_totp_step(secret, code) is not None


def match_totp_step(secret: str | None, code: str) -> int | None:
    """Verify a TOTP code and return the time-step counter it matched, else None.

    The returned step lets callers enforce single-use: a code from a step already
    consumed must be rejected, so a captured code (or a replayed MFA-challenge
    token) can't be reused within its validity window.
    """
    if not secret or not code:
        return None
    normalized = code.strip().replace(" ", "")
    if not normalized.isdigit():
        return None
    totp = pyotp.TOTP(secret)
    now = time.time()
    current_step = int(now // totp.interval)
    for offset in range(-_WINDOW, _WINDOW + 1):
        if secrets.compare_digest(totp.at(now, counter_offset=offset), normalized):
            return current_step + offset
    return None


def generate_recovery_codes(n: int = 10) -> list[str]:
    # Human-friendly, e.g. "a1b2-c3d4"
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(n)]


def hash_recovery_code(code: str) -> str:
    normalized = code.strip().lower().replace("-", "").replace(" ", "")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
