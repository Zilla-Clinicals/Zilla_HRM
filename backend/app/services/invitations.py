from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import generate_raw_token, hash_token
from app.models._base import Role
from app.models.employees import Employee
from app.models.users import Invitation, User
from app.schemas.employees import EmployeeCreate
from app.services.employee_ids import generate_unique_employee_number

INVITE_TTL_DAYS = 7


async def create_invitation(
    db: AsyncSession,
    *,
    email: str,
    role: Role,
    initial_employee: EmployeeCreate,
    invited_by: int | None,
) -> tuple[User, str]:
    """Create the (inactive) user + employee row and a one-time invite token.

    Returns (user, raw_token). Store only sha256(raw_token); email the raw one.
    """
    email = email.strip().lower()

    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with that email already exists")

    user = User(email=email, role=role, password_hash=None, is_active=False)
    db.add(user)
    await db.flush()  # assigns user.id

    # Auto-assign a unique employee number unless HR supplied one.
    employee_number = initial_employee.employee_number or (
        await generate_unique_employee_number(db, initial_employee.full_name)
    )

    employee = Employee(
        user_id=user.id,
        full_name=initial_employee.full_name,
        employee_number=employee_number,
        job_title=initial_employee.job_title,
        team=initial_employee.team,
        hire_date=initial_employee.hire_date,
        phone=initial_employee.phone,
        manager_id=initial_employee.manager_id,
    )
    db.add(employee)

    raw_token = generate_raw_token()
    invitation = Invitation(
        email=email,
        role=role,
        token_hash=hash_token(raw_token),
        invited_by=invited_by,
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=INVITE_TTL_DAYS),
    )
    db.add(invitation)
    await db.flush()

    return user, raw_token


async def resend_invitation(
    db: AsyncSession, *, user_id: int, invited_by: int | None
) -> tuple[User, str]:
    """Issue a fresh invite token for a user who hasn't accepted yet.

    Expires any still-pending invitations for that user, then mints a new one.
    Returns (user, raw_token).
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.password_hash is not None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "User has already accepted their invitation"
        )

    now = datetime.now(UTC)
    for inv in (
        await db.scalars(
            select(Invitation).where(
                Invitation.user_id == user.id, Invitation.accepted_at.is_(None)
            )
        )
    ).all():
        inv.expires_at = now  # invalidate old links

    raw_token = generate_raw_token()
    db.add(
        Invitation(
            email=user.email,
            role=user.role,
            token_hash=hash_token(raw_token),
            invited_by=invited_by,
            user_id=user.id,
            expires_at=now + timedelta(days=INVITE_TTL_DAYS),
        )
    )
    await db.flush()
    return user, raw_token


async def consume_invitation(
    db: AsyncSession, *, raw_token: str, full_name: str, password_hash: str
) -> User:
    """Validate + burn an invite, activating the user and setting the password."""
    invitation = await db.scalar(
        select(Invitation).where(Invitation.token_hash == hash_token(raw_token))
    )
    if not invitation:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid invitation token")
    if invitation.accepted_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation already used")
    if invitation.expires_at < datetime.now(UTC):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation expired")

    user = await db.scalar(select(User).where(User.email == invitation.email))
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation user missing")

    user.password_hash = password_hash
    user.is_active = True
    invitation.accepted_at = datetime.now(UTC)

    employee = await db.scalar(select(Employee).where(Employee.user_id == user.id))
    if employee and full_name:
        employee.full_name = full_name

    await db.flush()
    return user
