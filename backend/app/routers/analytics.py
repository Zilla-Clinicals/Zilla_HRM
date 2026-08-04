from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_cap
from app.auth.permissions import Cap
from app.db import get_session
from app.models._base import STATUS_FACTOR, ReviewStatus, ScoreAuthor
from app.models.employees import Employee
from app.models.kpis import Kpi
from app.models.reviews import ReviewAssignment, ReviewCycle, ReviewScore
from app.models.users import User
from app.schemas.analytics import (
    CalibrationCategory,
    CycleAnalyticsOut,
    EmployeesOut,
    EmployeeTrajectory,
    KpiInsight,
    Series,
    SummaryOut,
    TrendCycle,
)
from app.services import analytics as an
from app.services.reviews import kpi_category_map, kpi_points_map

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def _employees(db: AsyncSession) -> dict[int, Employee]:
    return {e.id: e for e in (await db.scalars(select(Employee))).all()}


@router.get("/summary", response_model=SummaryOut)
async def summary(
    _: User = Depends(require_cap(Cap.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_session),
):
    cycles = await an.ran_cycles(db)
    points = await kpi_points_map(db)
    catmap = await kpi_category_map(db)
    weights = await an.category_weights(db)
    emps = await _employees(db)

    trend: list[TrendCycle] = []
    cat_vals: dict[str, list[float | None]] = {c: [] for c in weights}
    team_vals: dict[str, list[float | None]] = defaultdict(lambda: [None] * len(cycles))

    for idx, cyc in enumerate(cycles):
        subjects = await an.assignment_subjects(db, cyc.id)
        statuses = (
            await db.execute(
                select(ReviewAssignment.status).where(ReviewAssignment.cycle_id == cyc.id)
            )
        ).scalars().all()
        total = len(statuses)
        submitted = sum(1 for s in statuses if s == ReviewStatus.submitted)
        earned = await an.earned_by_assignment(
            db, cycle_id=cyc.id, author=ScoreAuthor.reviewer, points=points, catmap=catmap
        )
        totals = [v["total"] for v in earned.values()]
        trend.append(
            TrendCycle(
                cycle_id=cyc.id,
                label=an.cycle_label(cyc),
                year=cyc.year,
                type=cyc.type,
                avg_score=an._avg(totals),
                completion_rate=round(submitted / total, 3) if total else 0.0,
                reviewed_count=len(totals),
            )
        )
        # per-category average this cycle
        for cat in weights:
            vals = [v["by_cat"].get(cat, 0.0) for v in earned.values()]
            cat_vals[cat].append(an._avg(vals))
        # per-team average this cycle
        team_bucket: dict[str, list[float]] = defaultdict(list)
        for aid, v in earned.items():
            emp = emps.get(subjects.get(aid))
            team = emp.team if emp and emp.team else "Unassigned"
            team_bucket[team].append(v["total"])
        for team, vals in team_bucket.items():
            team_vals[team][idx] = an._avg(vals)

    category_series = [
        Series(name=cat, max_points=weights[cat], values=cat_vals[cat]) for cat in weights
    ]
    team_series = [Series(name=t, values=v) for t, v in sorted(team_vals.items())]
    latest = next(
        (t.cycle_id for t in reversed(trend) if t.reviewed_count > 0),
        trend[-1].cycle_id if trend else None,
    )
    return SummaryOut(
        cycles=trend,
        category_series=category_series,
        team_series=team_series,
        latest_cycle_id=latest,
    )


@router.get("/cycle/{cycle_id}", response_model=CycleAnalyticsOut)
async def cycle_analytics(
    cycle_id: int,
    _: User = Depends(require_cap(Cap.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_session),
):
    cycle = await db.get(ReviewCycle, cycle_id)
    if not cycle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found")
    points = await kpi_points_map(db)
    catmap = await kpi_category_map(db)
    weights = await an.category_weights(db)
    kpis = {k.id: k for k in (await db.scalars(select(Kpi))).all()}

    # ---- per-KPI leaderboard (reviewer scores) ----
    rows = (
        await db.execute(
            select(ReviewScore.kpi_id, ReviewScore.status)
            .join(ReviewAssignment, ReviewAssignment.id == ReviewScore.assignment_id)
            .where(
                ReviewAssignment.cycle_id == cycle_id,
                ReviewScore.author == ScoreAuthor.reviewer,
            )
        )
    ).all()
    def _blank() -> dict:
        return {"met": 0, "partial": 0, "not_met": 0, "earned": 0.0, "n": 0}

    agg: dict[int, dict] = defaultdict(_blank)
    for kpi_id, st in rows:
        a = agg[kpi_id]
        a[st.value] += 1
        a["earned"] += points.get(kpi_id, 0.0) * STATUS_FACTOR[st]
        a["n"] += 1
    kpi_insights: list[KpiInsight] = []
    for kpi_id, a in agg.items():
        k = kpis.get(kpi_id)
        if not k:
            continue
        maxp = points.get(kpi_id, 0.0)
        earned_avg = round(a["earned"] / a["n"], 2) if a["n"] else 0.0
        kpi_insights.append(
            KpiInsight(
                name=k.name,
                category=k.category,
                max_points=round(maxp, 2),
                earned_avg=earned_avg,
                pct=round(earned_avg / maxp, 3) if maxp else 0.0,
                met=a["met"],
                partial=a["partial"],
                not_met=a["not_met"],
            )
        )
    kpi_insights.sort(key=lambda x: x.pct, reverse=True)

    # ---- self vs reviewer calibration (assignments scored by both) ----
    rev = await an.earned_by_assignment(
        db, cycle_id=cycle_id, author=ScoreAuthor.reviewer, points=points, catmap=catmap
    )
    slf = await an.earned_by_assignment(
        db, cycle_id=cycle_id, author=ScoreAuthor.self, points=points, catmap=catmap
    )
    paired = [aid for aid in rev if aid in slf]
    calibration: list[CalibrationCategory] = []
    for cat, weight in weights.items():
        if not weight:
            continue
        s_vals = [slf[a]["by_cat"].get(cat, 0.0) / weight for a in paired]
        r_vals = [rev[a]["by_cat"].get(cat, 0.0) / weight for a in paired]
        calibration.append(
            CalibrationCategory(
                category=cat,
                self_pct=round(sum(s_vals) / len(s_vals), 3) if s_vals else 0.0,
                reviewer_pct=round(sum(r_vals) / len(r_vals), 3) if r_vals else 0.0,
            )
        )
    overall_self = an._avg([slf[a]["total"] for a in paired])
    overall_rev = an._avg([rev[a]["total"] for a in paired])

    return CycleAnalyticsOut(
        cycle_id=cycle.id,
        label=an.cycle_label(cycle),
        kpis=kpi_insights,
        calibration=calibration,
        calibration_overall_self=(overall_self / 100) if overall_self is not None else None,
        calibration_overall_reviewer=(overall_rev / 100) if overall_rev is not None else None,
        calibration_pairs=len(paired),
    )


@router.get("/employees", response_model=EmployeesOut)
async def employee_trajectories(
    _: User = Depends(require_cap(Cap.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_session),
):
    cycles = await an.ran_cycles(db)
    points = await kpi_points_map(db)
    catmap = await kpi_category_map(db)
    emps = await _employees(db)

    # employee_id -> list of scores aligned to cycles (None where not reviewed)
    scores: dict[int, list[float | None]] = defaultdict(lambda: [None] * len(cycles))
    for idx, cyc in enumerate(cycles):
        subjects = await an.assignment_subjects(db, cyc.id)
        earned = await an.earned_by_assignment(
            db, cycle_id=cyc.id, author=ScoreAuthor.reviewer, points=points, catmap=catmap
        )
        for aid, v in earned.items():
            sid = subjects.get(aid)
            if sid is not None:
                scores[sid][idx] = round(v["total"], 2)

    result: list[EmployeeTrajectory] = []
    for eid, vals in scores.items():
        emp = emps.get(eid)
        if not emp:
            continue
        present = [v for v in vals if v is not None]
        latest = present[-1] if present else None
        delta = round(present[-1] - present[-2], 2) if len(present) >= 2 else None
        result.append(
            EmployeeTrajectory(
                employee_id=eid,
                name=emp.full_name,
                team=emp.team,
                values=vals,
                latest=latest,
                delta=delta,
            )
        )
    result.sort(key=lambda e: (e.latest is None, -(e.latest or 0)))
    return EmployeesOut(cycles=[an.cycle_label(c) for c in cycles], employees=result)
