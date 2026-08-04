from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_cap
from app.auth.email import send_invite_email
from app.auth.passwords import hash_password, verify_password
from app.auth.permissions import Cap, can
from app.auth.totp import (
    generate_recovery_codes,
    generate_secret,
    hash_recovery_code,
    provisioning_uri,
    verify_totp,
)
from app.config import settings
from app.db import get_session
from app.models._base import Role
from app.models.employees import Employee
from app.models.users import RecoveryCode, RefreshToken, User
from app.schemas.employees import EmployeeOut
from app.schemas.users import (
    ChangePasswordIn,
    InviteIn,
    InviteOut,
    MeOut,
    MeUpdate,
    TwoFactorDisableIn,
    TwoFactorEnableIn,
    TwoFactorEnableOut,
    TwoFactorSetupOut,
    UserAdminUpdate,
    UserOut,
)
from app.services import audit
from app.services.documents import has_photo
from app.services.invitations import create_invitation, resend_invitation

router = APIRouter(prefix="/api/users", tags=["users"])


async def _employee_for(db: AsyncSession, user: User) -> Employee | None:
    return await db.scalar(select(Employee).where(Employee.user_id == user.id))


async def _employee_out(db: AsyncSession, employee: Employee | None) -> EmployeeOut | None:
    if not employee:
        return None
    return EmployeeOut.model_validate(employee).model_copy(
        update={"has_photo": await has_photo(db, employee.id)}
    )


@router.get("/me", response_model=MeOut)
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    employee = await _employee_for(db, user)
    return MeOut(user=UserOut.model_validate(user), employee=await _employee_out(db, employee))


@router.patch("/me", response_model=MeOut)
async def update_me(
    payload: MeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    employee = await _employee_for(db, user)
    if employee:
        if payload.full_name is not None:
            employee.full_name = payload.full_name
        if payload.phone is not None:
            employee.phone = payload.phone
        await db.commit()
        await db.refresh(employee)
    return MeOut(user=UserOut.model_validate(user), employee=await _employee_out(db, employee))


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    user.password_hash = hash_password(payload.new_password)
    now = datetime.now(UTC)
    for rt in (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
            )
        )
    ).all():
        rt.revoked_at = now
    await db.commit()


# ------------------------------------------------------- 2FA (self-service)
@router.post("/me/2fa/setup", response_model=TwoFactorSetupOut)
async def two_factor_setup(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-factor is already enabled")
    secret = generate_secret()
    user.totp_secret = secret  # pending until confirmed with a valid code
    await db.commit()
    return TwoFactorSetupOut(secret=secret, otpauth_uri=provisioning_uri(secret, user.email))


@router.post("/me/2fa/enable", response_model=TwoFactorEnableOut)
async def two_factor_enable(
    payload: TwoFactorEnableIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Two-factor is already enabled")
    if not user.totp_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Start 2FA setup first")
    if not verify_totp(user.totp_secret, payload.code):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That code isn't valid — try again")

    user.totp_enabled = True
    codes = generate_recovery_codes()
    for code in codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=hash_recovery_code(code)))
    await db.commit()
    return TwoFactorEnableOut(recovery_codes=codes)


@router.post("/me/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def two_factor_disable(
    payload: TwoFactorDisableIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is incorrect")
    user.totp_enabled = False
    user.totp_secret = None
    for rc in (
        await db.scalars(select(RecoveryCode).where(RecoveryCode.user_id == user.id))
    ).all():
        await db.delete(rc)
    await db.commit()


@router.get("", response_model=list[UserOut])
async def list_users(
    _: User = Depends(require_cap(Cap.VIEW_ORG)),
    db: AsyncSession = Depends(get_session),
):
    users = (await db.scalars(select(User).order_by(User.id))).all()
    return [UserOut.model_validate(u) for u in users]


@router.post("/invite", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteIn,
    admin: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    # Only role-managers may hand out elevated (executive/admin) roles.
    if payload.role in (Role.admin, Role.executive) and not can(admin.role, Cap.MANAGE_ROLES):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "You cannot invite executive or admin users"
        )
    user, raw_token = await create_invitation(
        db,
        email=payload.email,
        role=payload.role,
        initial_employee=payload.initial_employee,
        invited_by=admin.id,
    )
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="user.invite",
        target_type="user",
        target_id=user.id,
        detail={"email": user.email, "role": user.role.value},
    )
    await db.commit()
    sent = send_invite_email(user.email, raw_token)

    # Surface the link if we're in console/dev mode, or if the email failed to send.
    invite_link = None
    if settings.email_provider != "resend" or not sent:
        invite_link = f"{settings.app_base_url}/accept-invite?token={raw_token}"

    return InviteOut(
        user_id=user.id, email=user.email, role=user.role, invite_link=invite_link
    )


async def _revoke_all_refresh(db: AsyncSession, user_id: int) -> None:
    now = datetime.now(UTC)
    for rt in (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )
    ).all():
        rt.revoked_at = now


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    admin: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if payload.is_active is False and target.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate yourself")
    if payload.role is not None:
        # Changing access roles is reserved for executives/admins.
        if not can(admin.role, Cap.MANAGE_ROLES):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot change user roles")
        target.role = payload.role
    if payload.is_active is not None:
        # Reactivating a never-accepted user makes no sense (no password yet).
        if payload.is_active and target.password_hash is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "This user hasn't accepted their invite yet — resend the invite instead",
            )
        target.is_active = payload.is_active
        if not payload.is_active:
            await _revoke_all_refresh(db, target.id)  # kill active sessions immediately
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="user.update",
        target_type="user",
        target_id=target.id,
        detail=payload.model_dump(exclude_unset=True, mode="json"),
    )
    await db.commit()
    await db.refresh(target)
    return UserOut.model_validate(target)


@router.post("/{user_id}/resend-invite", response_model=InviteOut)
async def resend_invite(
    user_id: int,
    admin: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    user, raw_token = await resend_invitation(db, user_id=user_id, invited_by=admin.id)
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="user.resend_invite",
        target_type="user",
        target_id=user.id,
        detail={"email": user.email},
    )
    await db.commit()
    sent = send_invite_email(user.email, raw_token)

    invite_link = None
    if settings.email_provider != "resend" or not sent:
        invite_link = f"{settings.app_base_url}/accept-invite?token={raw_token}"
    return InviteOut(
        user_id=user.id, email=user.email, role=user.role, invite_link=invite_link
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: int,
    admin: User = Depends(require_cap(Cap.MANAGE_PEOPLE)),
    db: AsyncSession = Depends(get_session),
):
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if target.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate yourself")
    target.is_active = False  # soft-deactivate, never hard-delete
    await _revoke_all_refresh(db, target.id)
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="user.deactivate",
        target_type="user",
        target_id=target.id,
    )
    await db.commit()
