from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.permissions import Cap, can
from app.db import get_session
from app.models._base import Role
from app.models.employees import Employee
from app.models.reviews import ReviewAssignment, ReviewCycle, ReviewScore
from app.models.users import User
from app.schemas.employees import EmployeeOut, EmployeeStatus, EmployeeUpdate
from app.schemas.reviews import ReviewHistoryItem, ScoreOut
from app.services import audit
from app.services.documents import employees_with_photo, has_photo
from app.services.reviews import weighted_total

router = APIRouter(prefix="/api/employees", tags=["employees"])


def _status(user: User | None) -> EmployeeStatus:
    if user is None:
        return "inactive"
    if user.is_active:
        return "active"
    if user.password_hash is None:
        return "pending"  # invited but never accepted
    return "inactive"  # was active, since deactivated


def _out(employee: Employee, user: User | None, has_photo: bool = False) -> EmployeeOut:
    return EmployeeOut.model_validate(employee).model_copy(
        update={
            "email": user.email if user else None,
            "role": user.role.value if user else None,
            "is_active": bool(user and user.is_active),
            "status": _status(user),
            "has_photo": has_photo,
        }
    )


async def _my_employee(db: AsyncSession, user: User) -> Employee | None:
    return await db.scalar(select(Employee).where(Employee.user_id == user.id))


async def _can_view(db: AsyncSession, user: User, target: Employee) -> bool:
    if can(user.role, Cap.VIEW_ORG):
        return True
    me = await _my_employee(db, user)
    if not me:
        return False
    if me.id == target.id:
        return True
    # Manager can view direct reports.
    return user.role == Role.manager and target.manager_id == me.id


@router.get("", response_model=list[EmployeeOut])
async def list_employees(
    team: str | None = Query(default=None),
    active: bool | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Employee).order_by(Employee.full_name)
    if team:
        stmt = stmt.where(Employee.team == team)
    employees = (await db.scalars(stmt)).all()

    if can(user.role, Cap.VIEW_ORG):
        visible = employees
    else:
        me = await _my_employee(db, user)
        if not me:
            visible = []
        elif user.role == Role.manager:
            visible = [e for e in employees if e.id == me.id or e.manager_id == me.id]
        else:
            visible = [e for e in employees if e.id == me.id]

    users = {
        u.id: u
        for u in (
            await db.scalars(
                select(User).where(User.id.in_([e.user_id for e in visible]))
            )
        ).all()
    }
    photo_ids = await employees_with_photo(db, [e.id for e in visible])
    out = [_out(e, users.get(e.user_id), e.id in photo_ids) for e in visible]
    if active is not None:
        out = [o for o in out if o.is_active == active]
    return out


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    target = await db.get(Employee, employee_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    if not await _can_view(db, user, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return _out(
        target, await db.get(User, target.user_id), await has_photo(db, target.id)
    )


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if not can(user.role, Cap.MANAGE_PEOPLE):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    target = await db.get(Employee, employee_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")

    data = payload.model_dump(exclude_unset=True)
    if data.get("manager_id") == employee_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "An employee cannot manage themselves")

    new_number = data.get("employee_number")
    if new_number and new_number != target.employee_number:
        clash = await db.scalar(
            select(Employee).where(
                Employee.employee_number == new_number, Employee.id != employee_id
            )
        )
        if clash:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "That employee number is already in use"
            )

    for field, value in data.items():
        setattr(target, field, value)
    # Audit the biodata change. Log which fields changed, not their values, to
    # keep employee PII out of the audit trail.
    await audit.record(
        db,
        actor_user_id=user.id,
        action="employee.update",
        target_type="employee",
        target_id=target.id,
        detail={"fields": sorted(data.keys())},
    )
    await db.commit()
    await db.refresh(target)
    return _out(
        target, await db.get(User, target.user_id), await has_photo(db, target.id)
    )


@router.get("/{employee_id}/reviews", response_model=list[ReviewHistoryItem])
async def employee_reviews(
    employee_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    target = await db.get(Employee, employee_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    if not await _can_view(db, user, target):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")

    assignments = (
        await db.scalars(
            select(ReviewAssignment)
            .where(ReviewAssignment.subject_employee_id == employee_id)
            .order_by(ReviewAssignment.cycle_id.desc())
        )
    ).all()

    items: list[ReviewHistoryItem] = []
    for a in assignments:
        cycle = await db.get(ReviewCycle, a.cycle_id)
        scores = (
            await db.scalars(
                select(ReviewScore).where(ReviewScore.assignment_id == a.id)
            )
        ).all()
        items.append(
            ReviewHistoryItem(
                assignment_id=a.id,
                cycle_id=a.cycle_id,
                cycle_year=cycle.year,
                cycle_type=cycle.type,
                cycle_status=cycle.status,
                status=a.status,
                submitted_at=a.submitted_at,
                summary_comment=a.summary_comment,
                weighted_total=await weighted_total(db, a.id),
                scores=[ScoreOut.model_validate(s) for s in scores],
            )
        )
    return items
