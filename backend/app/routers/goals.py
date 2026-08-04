from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.permissions import Cap, can
from app.db import get_session
from app.models.employees import Employee
from app.models.goals import Goal, GoalCheckin
from app.models.users import User
from app.schemas.goals import (
    CheckinCreate,
    CheckinOut,
    GoalCreate,
    GoalDetailOut,
    GoalOut,
    GoalUpdate,
)

router = APIRouter(prefix="/api", tags=["goals"])


async def _my_employee(db: AsyncSession, user: User) -> Employee:
    emp = await db.scalar(select(Employee).where(Employee.user_id == user.id))
    if not emp:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record linked to user")
    return emp


async def _load_goal(db: AsyncSession, goal_id: int) -> Goal:
    goal = await db.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    return goal


async def _can_view_goal(db: AsyncSession, user: User, goal: Goal) -> bool:
    if can(user.role, Cap.VIEW_ORG):
        return True
    me = await db.scalar(select(Employee).where(Employee.user_id == user.id))
    if not me:
        return False
    if goal.employee_id == me.id:
        return True
    owner = await db.get(Employee, goal.employee_id)
    return owner is not None and owner.manager_id == me.id


async def _checkin_counts(db: AsyncSession, goal_ids: list[int]) -> dict[int, int]:
    if not goal_ids:
        return {}
    rows = (
        await db.execute(
            select(GoalCheckin.goal_id, func.count())
            .where(GoalCheckin.goal_id.in_(goal_ids))
            .group_by(GoalCheckin.goal_id)
        )
    ).all()
    return {gid: n for gid, n in rows}


def _goal_out(goal: Goal, employee_name: str | None, checkin_count: int) -> GoalOut:
    return GoalOut.model_validate(goal).model_copy(
        update={"employee_name": employee_name, "checkin_count": checkin_count}
    )


async def _list_for_employee(
    db: AsyncSession, employee: Employee, year: int | None
) -> list[GoalOut]:
    stmt = select(Goal).where(Goal.employee_id == employee.id)
    if year is not None:
        stmt = stmt.where(Goal.year == year)
    stmt = stmt.order_by(Goal.year.desc(), Goal.id.desc())
    goals = (await db.scalars(stmt)).all()
    counts = await _checkin_counts(db, [g.id for g in goals])
    return [_goal_out(g, employee.full_name, counts.get(g.id, 0)) for g in goals]


# ------------------------------------------------------------------ my goals
@router.get("/goals/mine", response_model=list[GoalOut])
async def my_goals(
    year: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    me = await _my_employee(db, user)
    return await _list_for_employee(db, me, year)


@router.post("/goals", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: GoalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    me = await _my_employee(db, user)
    goal = Goal(
        employee_id=me.id,
        year=payload.year,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        target_date=payload.target_date,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return _goal_out(goal, me.full_name, 0)


@router.get("/goals/{goal_id}", response_model=GoalDetailOut)
async def get_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    goal = await _load_goal(db, goal_id)
    if not await _can_view_goal(db, user, goal):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    owner = await db.get(Employee, goal.employee_id)
    checkins = (
        await db.scalars(
            select(GoalCheckin)
            .where(GoalCheckin.goal_id == goal_id)
            .order_by(GoalCheckin.id.desc())
        )
    ).all()
    # resolve check-in author names
    author_ids = [c.created_by for c in checkins if c.created_by]
    names: dict[int, str] = {}
    if author_ids:
        rows = (
            await db.execute(
                select(User.id, Employee.full_name)
                .join(Employee, Employee.user_id == User.id)
                .where(User.id.in_(author_ids))
            )
        ).all()
        names = {uid: name for uid, name in rows}

    base = _goal_out(goal, owner.full_name if owner else None, len(checkins))
    return GoalDetailOut(
        **base.model_dump(),
        checkins=[
            CheckinOut.model_validate(c).model_copy(
                update={"author_name": names.get(c.created_by)}
            )
            for c in checkins
        ],
    )


@router.patch("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: int,
    payload: GoalUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    goal = await _load_goal(db, goal_id)
    me = await _my_employee(db, user)
    if goal.employee_id != me.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit your own goals")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal)
    return _goal_out(goal, me.full_name, await _one_count(db, goal.id))


async def _one_count(db: AsyncSession, goal_id: int) -> int:
    return (await _checkin_counts(db, [goal_id])).get(goal_id, 0)


@router.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    goal = await _load_goal(db, goal_id)
    me = await _my_employee(db, user)
    if goal.employee_id != me.id and not can(user.role, Cap.VIEW_ORG):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    await db.delete(goal)
    await db.commit()


@router.post("/goals/{goal_id}/checkins", response_model=CheckinOut, status_code=201)
async def add_checkin(
    goal_id: int,
    payload: CheckinCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    goal = await _load_goal(db, goal_id)
    me = await db.scalar(select(Employee).where(Employee.user_id == user.id))
    is_owner = me is not None and goal.employee_id == me.id
    if not is_owner and not await _can_view_goal(db, user, goal):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")

    # Only the owner's check-ins move the goal's progress; others are comments.
    progress = payload.progress if is_owner else None
    checkin = GoalCheckin(
        goal_id=goal_id, progress=progress, note=payload.note, created_by=user.id
    )
    db.add(checkin)
    if is_owner and progress is not None:
        goal.progress = progress
        if goal.status == "not_started":
            goal.status = "in_progress"
    await db.commit()
    await db.refresh(checkin)
    author = me.full_name if me else None
    return CheckinOut.model_validate(checkin).model_copy(update={"author_name": author})


# ------------------------------------------------ another employee's goals
@router.get("/employees/{employee_id}/goals", response_model=list[GoalOut])
async def employee_goals(
    employee_id: int,
    year: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    target = await db.get(Employee, employee_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found")
    # self, manager-of, or org viewers
    allowed = can(user.role, Cap.VIEW_ORG)
    if not allowed:
        me = await db.scalar(select(Employee).where(Employee.user_id == user.id))
        allowed = me is not None and (me.id == target.id or target.manager_id == me.id)
    if not allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
    return await _list_for_employee(db, target, year)
