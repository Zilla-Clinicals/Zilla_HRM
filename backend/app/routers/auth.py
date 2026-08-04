from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.email import send_reset_email
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import (
    create_access_token,
    create_mfa_token,
    decode_mfa_token,
    generate_raw_token,
    hash_token,
    refresh_expiry,
)
from app.auth.totp import hash_recovery_code, match_totp_step
from app.config import settings
from app.db import get_session
from app.models.users import PasswordReset, RecoveryCode, RefreshToken, User
from app.rate_limit import limiter
from app.schemas.auth import (
    AcceptInviteIn,
    ForgotPasswordIn,
    LoginIn,
    LoginOut,
    MfaVerifyIn,
    ResetPasswordIn,
    TokenOut,
)
from app.services.invitations import consume_invitation

router = APIRouter(prefix="/api/auth", tags=["auth"])

RESET_TTL_HOURS = 1


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain_or_none,
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        domain=settings.cookie_domain_or_none,
        path="/api/auth",
    )


async def _issue_refresh(db: AsyncSession, user: User, request: Request) -> str:
    raw = generate_raw_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            user_agent=request.headers.get("user-agent"),
            expires_at=refresh_expiry(),
        )
    )
    await db.flush()
    return raw


async def _verify_second_factor(db: AsyncSession, user: User, code: str) -> bool:
    # Authenticator code — enforce single use so a captured code (or a replayed
    # MFA-challenge token) can't be reused within its 30s validity window.
    step = match_totp_step(user.totp_secret, code)
    if step is not None:
        if user.totp_last_used_step is not None and step <= user.totp_last_used_step:
            return False
        user.totp_last_used_step = step
        return True
    # fall back to a one-time recovery code
    rc = await db.scalar(
        select(RecoveryCode).where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == hash_recovery_code(code),
            RecoveryCode.used_at.is_(None),
        )
    )
    if rc:
        rc.used_at = datetime.now(UTC)
        return True
    return False


async def _issue_login(
    db: AsyncSession, user: User, request: Request, response: Response
) -> TokenOut:
    raw_refresh = await _issue_refresh(db, user, request)
    await db.commit()
    _set_refresh_cookie(response, raw_refresh)
    return TokenOut(access_token=create_access_token(user.id, user.role.value))


@router.post("/login", response_model=LoginOut)
@limiter.limit(settings.login_rate_limit)
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    email = payload.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    # 2FA enabled → issue a short-lived challenge instead of tokens.
    if user.totp_enabled:
        return LoginOut(mfa_required=True, mfa_token=create_mfa_token(user.id))

    token = await _issue_login(db, user, request, response)
    return LoginOut(access_token=token.access_token)


@router.post("/login/verify", response_model=TokenOut)
@limiter.limit(settings.login_rate_limit)
async def login_verify(
    payload: MfaVerifyIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    try:
        user_id = decode_mfa_token(payload.mfa_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Your sign-in session expired — start again"
        ) from exc
    user = await db.get(User, user_id)
    if not user or not user.is_active or not user.totp_enabled:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
    if not await _verify_second_factor(db, user, payload.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authentication code")
    return await _issue_login(db, user, request, response)


@router.post("/refresh", response_model=TokenOut)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    raw = request.cookies.get(settings.refresh_cookie_name)
    if not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token")

    token = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
    )
    now = datetime.now(UTC)
    if not token or token.revoked_at is not None or token.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    user = await db.get(User, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User inactive")

    # Rotate: revoke the old, issue a new one.
    token.revoked_at = now
    raw_refresh = await _issue_refresh(db, user, request)
    await db.commit()
    _set_refresh_cookie(response, raw_refresh)
    return TokenOut(access_token=create_access_token(user.id, user.role.value))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    raw = request.cookies.get(settings.refresh_cookie_name)
    if raw:
        token = await db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
        )
        if token and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
            await db.commit()
    _clear_refresh_cookie(response)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.sensitive_rate_limit)
async def forgot_password(
    payload: ForgotPasswordIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    # Always 202 — never leak whether the email exists.
    email = payload.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user and user.is_active:
        raw = generate_raw_token()
        db.add(
            PasswordReset(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=RESET_TTL_HOURS),
            )
        )
        await db.commit()
        send_reset_email(user.email, raw)
    return {"status": "accepted"}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.sensitive_rate_limit)
async def reset_password(
    payload: ResetPasswordIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    reset = await db.scalar(
        select(PasswordReset).where(PasswordReset.token_hash == hash_token(payload.token))
    )
    now = datetime.now(UTC)
    if not reset or reset.consumed_at is not None or reset.expires_at < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired reset token")

    user = await db.get(User, reset.user_id)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reset token")

    user.password_hash = hash_password(payload.new_password)
    reset.consumed_at = now
    # Revoke all refresh tokens on password change.
    for rt in (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
            )
        )
    ).all():
        rt.revoked_at = now
    await db.commit()


@router.post("/accept-invite", response_model=TokenOut)
@limiter.limit(settings.sensitive_rate_limit)
async def accept_invite(
    payload: AcceptInviteIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    user = await consume_invitation(
        db,
        raw_token=payload.token,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    raw_refresh = await _issue_refresh(db, user, request)
    await db.commit()
    _set_refresh_cookie(response, raw_refresh)
    return TokenOut(access_token=create_access_token(user.id, user.role.value))
