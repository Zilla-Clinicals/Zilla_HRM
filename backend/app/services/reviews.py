from collections import Counter
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models._base import (
    STATUS_FACTOR,
    CycleStatus,
    ReviewStatus,
    ScoreAuthor,
)
from app.models.employees import Employee
from app.models.kpis import Kpi, KpiCategory
from app.models.reviews import ReviewAssignment, ReviewCycle, ReviewScore


async def auto_assign(
    db: AsyncSession,
    *,
    cycle: ReviewCycle,
    overrides: dict[int, int],
    skip_without_manager: bool,
) -> list[ReviewAssignment]:
    """Populate assignments from employees.manager_id (with optional overrides).

    overrides maps subject_employee_id -> reviewer_employee_id.
    Idempotent: existing (cycle, subject) rows are updated, not duplicated.
    """
    if cycle.status != CycleStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Assignments can only be (re)generated on a draft cycle"
        )

    employees = (await db.scalars(select(Employee))).all()
    existing = {
        a.subject_employee_id: a
        for a in (
            await db.scalars(
                select(ReviewAssignment).where(ReviewAssignment.cycle_id == cycle.id)
            )
        ).all()
    }

    result: list[ReviewAssignment] = []
    for emp in employees:
        reviewer_id = overrides.get(emp.id, emp.manager_id)
        if reviewer_id is None:
            if skip_without_manager:
                continue
            reviewer_id = emp.id  # self-review fallback

        assignment = existing.get(emp.id)
        if assignment:
            assignment.reviewer_employee_id = reviewer_id
        else:
            assignment = ReviewAssignment(
                cycle_id=cycle.id,
                subject_employee_id=emp.id,
                reviewer_employee_id=reviewer_id,
                status=ReviewStatus.not_started,
            )
            db.add(assignment)
        result.append(assignment)

    await db.flush()
    return result


async def open_cycle(db: AsyncSession, cycle: ReviewCycle) -> ReviewCycle:
    if cycle.status == CycleStatus.closed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cycle is already closed")
    count = await db.scalar(
        select(ReviewAssignment).where(ReviewAssignment.cycle_id == cycle.id).limit(1)
    )
    if count is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Assign reviewers before opening the cycle"
        )
    cycle.status = CycleStatus.open
    await db.flush()
    return cycle


async def close_cycle(db: AsyncSession, cycle: ReviewCycle) -> ReviewCycle:
    if cycle.status == CycleStatus.draft:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cannot close a draft cycle")
    cycle.status = CycleStatus.closed
    await db.flush()
    return cycle


async def kpi_points_map(db: AsyncSession) -> dict[int, float]:
    """Points per active KPI = its category weight / # active KPIs in that category.

    Across all active KPIs these sum to ~100 (the workbook's total).
    """
    kpis = (await db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))).all()
    weights = {
        c.name: float(c.weight)
        for c in (
            await db.scalars(select(KpiCategory).where(KpiCategory.is_active.is_(True)))
        ).all()
    }
    counts = Counter(k.category for k in kpis)
    return {
        k.id: (weights.get(k.category, 0.0) / counts[k.category]) if counts[k.category] else 0.0
        for k in kpis
    }


async def kpi_category_map(db: AsyncSession) -> dict[int, str]:
    kpis = (await db.scalars(select(Kpi))).all()
    return {k.id: k.category for k in kpis}


async def weighted_total(
    db: AsyncSession, assignment_id: int, points: dict[int, float] | None = None
) -> float | None:
    """Points earned out of 100 for an assignment's reviewer scores.

    earned = sum(kpi_points * status_factor) over the reviewer's scores.
    """
    if points is None:
        points = await kpi_points_map(db)
    scores = (
        await db.scalars(
            select(ReviewScore).where(
                ReviewScore.assignment_id == assignment_id,
                ReviewScore.author == ScoreAuthor.reviewer,
            )
        )
    ).all()
    if not scores:
        return None
    earned = sum(points.get(s.kpi_id, 0.0) * STATUS_FACTOR[s.status] for s in scores)
    return round(earned, 2)


async def missing_scored_kpis(
    db: AsyncSession, *, assignment_id: int, author: ScoreAuthor
) -> list[str]:
    """Names of active KPIs lacking a status+comment for this author (blocks submit)."""
    active = (await db.scalars(select(Kpi).where(Kpi.is_active.is_(True)))).all()
    scored = {
        s.kpi_id
        for s in (
            await db.scalars(
                select(ReviewScore).where(
                    ReviewScore.assignment_id == assignment_id,
                    ReviewScore.author == author,
                )
            )
        ).all()
        if s.comment and s.comment.strip()
    }
    return [k.name for k in active if k.id not in scored]


def ensure_editable(cycle: ReviewCycle, assignment: ReviewAssignment) -> None:
    """Guard: scores are editable only while the cycle is open and not yet submitted."""
    if cycle.status != CycleStatus.open:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cycle is not open for editing")
    if assignment.status == ReviewStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT, "Review already submitted")


async def submit_assignment(
    db: AsyncSession, *, cycle: ReviewCycle, assignment: ReviewAssignment, summary: str | None
) -> ReviewAssignment:
    if cycle.status != CycleStatus.open:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cycle is not open")
    if assignment.status == ReviewStatus.submitted:
        return assignment  # idempotent
    assignment.status = ReviewStatus.submitted
    assignment.submitted_at = datetime.now(UTC)
    if summary is not None:
        assignment.summary_comment = summary
    await db.flush()
    return assignment
