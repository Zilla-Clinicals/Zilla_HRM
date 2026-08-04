"""Cross-cycle analytics aggregation.

All scoring uses the current points map (category weight / # active KPIs), so
numbers are comparable across cycles. Only reviewer-authored scores count toward
official performance; self scores are surfaced separately for calibration.
"""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models._base import STATUS_FACTOR, CycleStatus, ScoreAuthor
from app.models.kpis import KpiCategory
from app.models.reviews import ReviewAssignment, ReviewCycle, ReviewScore

_TYPE_ORDER = {"mid_year": 0, "end_year": 1}


def cycle_label(cycle: ReviewCycle) -> str:
    return f"{cycle.year} {cycle.type.value.replace('_', ' ')}"


async def ran_cycles(db: AsyncSession) -> list[ReviewCycle]:
    """Cycles that actually ran (open or closed), oldest first."""
    cycles = (
        await db.scalars(
            select(ReviewCycle).where(
                ReviewCycle.status.in_([CycleStatus.open, CycleStatus.closed])
            )
        )
    ).all()
    return sorted(cycles, key=lambda c: (c.year, _TYPE_ORDER.get(c.type.value, 9)))


async def category_weights(db: AsyncSession) -> dict[str, float]:
    return {
        c.name: float(c.weight)
        for c in (
            await db.scalars(select(KpiCategory).where(KpiCategory.is_active.is_(True)))
        ).all()
    }


async def earned_by_assignment(
    db: AsyncSession,
    *,
    cycle_id: int,
    author: ScoreAuthor,
    points: dict[int, float],
    catmap: dict[int, str],
) -> dict[int, dict]:
    """assignment_id -> {'total': pts, 'by_cat': {category: pts}}."""
    rows = (
        await db.execute(
            select(
                ReviewScore.assignment_id, ReviewScore.kpi_id, ReviewScore.status
            )
            .join(ReviewAssignment, ReviewAssignment.id == ReviewScore.assignment_id)
            .where(
                ReviewAssignment.cycle_id == cycle_id,
                ReviewScore.author == author,
            )
        )
    ).all()
    out: dict[int, dict] = defaultdict(lambda: {"total": 0.0, "by_cat": defaultdict(float)})
    for aid, kpi_id, st in rows:
        pts = points.get(kpi_id, 0.0) * STATUS_FACTOR[st]
        out[aid]["total"] += pts
        out[aid]["by_cat"][catmap.get(kpi_id, "—")] += pts
    return out


async def assignment_subjects(db: AsyncSession, cycle_id: int) -> dict[int, int]:
    """assignment_id -> subject_employee_id for a cycle."""
    rows = (
        await db.execute(
            select(ReviewAssignment.id, ReviewAssignment.subject_employee_id).where(
                ReviewAssignment.cycle_id == cycle_id
            )
        )
    ).all()
    return {aid: sid for aid, sid in rows}


def _avg(vals: list[float]) -> float | None:
    return round(sum(vals) / len(vals), 2) if vals else None
