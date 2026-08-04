from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_cap
from app.auth.permissions import Cap
from app.db import get_session
from app.models._base import STATUS_FACTOR, CycleStatus, KpiStatus, ReviewStatus, ScoreAuthor
from app.models.employees import Employee
from app.models.kpis import KpiCategory
from app.models.reviews import ReviewAssignment, ReviewCycle, ReviewScore
from app.models.users import User
from app.schemas.dashboard import (
    Breakdown,
    CategoryRollup,
    CycleDashboardOut,
    OrgOverviewOut,
    StatusBucket,
    TeamAverage,
)
from app.services.reviews import kpi_category_map, kpi_points_map

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_EMPLOYMENT_LABELS = {
    "full_time": "Full-time",
    "part_time": "Part-time",
    "contract": "Contract",
    "intern": "Intern",
}
_GENDER_LABELS = {
    "male": "Male",
    "female": "Female",
    "other": "Other",
    "prefer_not_to_say": "Undisclosed",
}


@router.get("/overview", response_model=OrgOverviewOut)
async def org_overview(
    _: User = Depends(require_cap(Cap.VIEW_ORG)),
    db: AsyncSession = Depends(get_session),
):
    employees = (await db.scalars(select(Employee))).all()
    users = {
        u.id: u
        for u in (
            await db.scalars(
                select(User).where(User.id.in_([e.user_id for e in employees]))
            )
        ).all()
    }

    active = pending = inactive = 0
    teams: Counter = Counter()
    employment: Counter = Counter()
    gender: Counter = Counter()
    today = datetime.now(UTC).date()
    new_hires = 0

    for e in employees:
        u = users.get(e.user_id)
        if u and u.is_active:
            active += 1
        elif u and u.password_hash is None:
            pending += 1
        else:
            inactive += 1
        # breakdowns count active people (the current workforce)
        if u and u.is_active:
            if e.team:
                teams[e.team] += 1
            if e.employment_type:
                employment[e.employment_type] += 1
            if e.gender:
                gender[e.gender] += 1
        if e.hire_date and (today - e.hire_date) <= timedelta(days=90):
            new_hires += 1

    managers = len({e.manager_id for e in employees if e.manager_id is not None})
    open_cycles_count = len(
        (
            await db.scalars(
                select(ReviewCycle.id).where(ReviewCycle.status == CycleStatus.open)
            )
        ).all()
    )

    return OrgOverviewOut(
        total_employees=len(employees),
        active_employees=active,
        pending_employees=pending,
        inactive_employees=inactive,
        managers=managers,
        teams=len(teams),
        new_hires_90d=new_hires,
        open_cycles=open_cycles_count,
        headcount_by_team=[
            Breakdown(label=t, count=c) for t, c in teams.most_common()
        ],
        employment_type_breakdown=[
            Breakdown(label=_EMPLOYMENT_LABELS.get(t, t), count=c)
            for t, c in employment.most_common()
        ],
        gender_breakdown=[
            Breakdown(label=_GENDER_LABELS.get(g, g), count=c)
            for g, c in gender.most_common()
        ],
    )

_STATUS_LABELS = [
    (KpiStatus.met, "Met"),
    (KpiStatus.partial, "Partial"),
    (KpiStatus.not_met, "Not Met"),
]


def _band(ratio: float) -> str:
    if ratio >= 0.85:
        return "On Track"
    if ratio >= 0.60:
        return "Needs Attention"
    return "Improve"


@router.get("/cycle/{cycle_id}", response_model=CycleDashboardOut)
async def cycle_dashboard(
    cycle_id: int,
    _: User = Depends(require_cap(Cap.VIEW_ORG)),
    db: AsyncSession = Depends(get_session),
):
    cycle = await db.get(ReviewCycle, cycle_id)
    if not cycle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found")

    assignments = (
        await db.scalars(
            select(ReviewAssignment).where(ReviewAssignment.cycle_id == cycle_id)
        )
    ).all()
    total = len(assignments)
    submitted = sum(1 for a in assignments if a.status == ReviewStatus.submitted)

    points = await kpi_points_map(db)
    catmap = await kpi_category_map(db)
    cat_weight = {
        c.name: float(c.weight)
        for c in (
            await db.scalars(select(KpiCategory).where(KpiCategory.is_active.is_(True)))
        ).all()
    }

    per_assignment_total: list[float] = []
    team_scores: dict[str, list[float]] = defaultdict(list)
    cat_earned: dict[str, list[float]] = defaultdict(list)
    status_counts: Counter = Counter()

    for a in assignments:
        scores = (
            await db.scalars(
                select(ReviewScore).where(
                    ReviewScore.assignment_id == a.id,
                    ReviewScore.author == ScoreAuthor.reviewer,
                )
            )
        ).all()
        if not scores:
            continue
        per_cat: dict[str, float] = defaultdict(float)
        earned = 0.0
        for s in scores:
            status_counts[s.status] += 1
            pts = points.get(s.kpi_id, 0.0) * STATUS_FACTOR[s.status]
            earned += pts
            per_cat[catmap.get(s.kpi_id, "—")] += pts
        per_assignment_total.append(earned)
        subject = await db.get(Employee, a.subject_employee_id)
        team = subject.team if subject and subject.team else "Unassigned"
        team_scores[team].append(earned)
        for cat in cat_weight:
            cat_earned[cat].append(per_cat.get(cat, 0.0))

    average = (
        round(sum(per_assignment_total) / len(per_assignment_total), 2)
        if per_assignment_total
        else None
    )

    status_distribution = [
        StatusBucket(label=label, count=status_counts.get(st, 0))
        for st, label in _STATUS_LABELS
    ]

    category_rollup = []
    for name, weight in sorted(cat_weight.items(), key=lambda kv: -kv[1]):
        vals = cat_earned.get(name, [])
        avg = round(sum(vals) / len(vals), 2) if vals else 0.0
        category_rollup.append(
            CategoryRollup(
                category=name,
                max_points=weight,
                earned_avg=avg,
                status_band=_band(avg / weight if weight else 0.0),
            )
        )

    team_averages = [
        TeamAverage(
            team=team,
            average_score=round(sum(vals) / len(vals), 2),
            subject_count=len(vals),
        )
        for team, vals in sorted(team_scores.items())
    ]

    return CycleDashboardOut(
        cycle_id=cycle.id,
        year=cycle.year,
        type=cycle.type,
        status=cycle.status,
        total_assignments=total,
        submitted_assignments=submitted,
        completion_rate=round(submitted / total, 3) if total else 0.0,
        average_score=average,
        status_distribution=status_distribution,
        category_rollup=category_rollup,
        team_averages=team_averages,
    )
