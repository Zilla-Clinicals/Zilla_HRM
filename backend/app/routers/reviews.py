from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_cap
from app.auth.permissions import Cap, can
from app.db import get_session
from app.models._base import CycleStatus, ReviewStatus, ScoreAuthor
from app.models.employees import Employee
from app.models.reviews import ReviewAssignment, ReviewCycle, ReviewScore
from app.models.users import User
from app.schemas.reviews import (
    AssignIn,
    AssignmentAdminOut,
    AssignmentDetailOut,
    AssignmentOut,
    AssignmentSubjectOut,
    CycleCreate,
    CycleOut,
    ReassignIn,
    ScoreIn,
    ScoreOut,
    SelfAssignmentOut,
    SelfDetailOut,
    SubmitIn,
)
from app.services import audit
from app.services.reviews import (
    auto_assign,
    close_cycle,
    ensure_editable,
    missing_scored_kpis,
    open_cycle,
    submit_assignment,
)

router = APIRouter(prefix="/api", tags=["reviews"])


# ---------------------------------------------------------------- Cycles (HR)
@router.get("/cycles", response_model=list[CycleOut])
async def list_cycles(
    _: User = Depends(require_cap(Cap.MANAGE_CYCLES)),
    db: AsyncSession = Depends(get_session),
):
    cycles = (
        await db.scalars(
            select(ReviewCycle).order_by(ReviewCycle.year.desc(), ReviewCycle.type)
        )
    ).all()
    return [CycleOut.model_validate(c) for c in cycles]


@router.post("/cycles", response_model=CycleOut, status_code=status.HTTP_201_CREATED)
async def create_cycle(
    payload: CycleCreate,
    admin: User = Depends(require_cap(Cap.MANAGE_CYCLES)),
    db: AsyncSession = Depends(get_session),
):
    if payload.closes_at <= payload.opens_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "closes_at must be after opens_at")
    exists = await db.scalar(
        select(ReviewCycle).where(
            ReviewCycle.year == payload.year, ReviewCycle.type == payload.type
        )
    )
    if exists:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "A cycle for that year and type already exists"
        )
    cycle = ReviewCycle(
        year=payload.year,
        type=payload.type,
        opens_at=payload.opens_at,
        closes_at=payload.closes_at,
        created_by=admin.id,
    )
    db.add(cycle)
    await db.flush()
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="cycle.create",
        target_type="cycle",
        target_id=cycle.id,
        detail={"year": cycle.year, "type": cycle.type.value},
    )
    await db.commit()
    await db.refresh(cycle)
    return CycleOut.model_validate(cycle)


async def _get_cycle_or_404(db: AsyncSession, cycle_id: int) -> ReviewCycle:
    cycle = await db.get(ReviewCycle, cycle_id)
    if not cycle:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cycle not found")
    return cycle


@router.post("/cycles/{cycle_id}/assign", response_model=list[AssignmentOut])
async def assign_cycle(
    cycle_id: int,
    payload: AssignIn,
    admin: User = Depends(require_cap(Cap.MANAGE_CYCLES)),
    db: AsyncSession = Depends(get_session),
):
    cycle = await _get_cycle_or_404(db, cycle_id)
    overrides = {o.subject_employee_id: o.reviewer_employee_id for o in payload.overrides}
    assignments = await auto_assign(
        db,
        cycle=cycle,
        overrides=overrides,
        skip_without_manager=payload.skip_without_manager,
    )
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="cycle.assign",
        target_type="cycle",
        target_id=cycle.id,
        detail={"assignments": len(assignments)},
    )
    await db.commit()
    return [AssignmentOut.model_validate(a) for a in assignments]


@router.post("/cycles/{cycle_id}/open", response_model=CycleOut)
async def open_cycle_route(
    cycle_id: int,
    admin: User = Depends(require_cap(Cap.MANAGE_CYCLES)),
    db: AsyncSession = Depends(get_session),
):
    cycle = await _get_cycle_or_404(db, cycle_id)
    await open_cycle(db, cycle)
    await audit.record(
        db, actor_user_id=admin.id, action="cycle.open", target_type="cycle", target_id=cycle.id
    )
    await db.commit()
    await db.refresh(cycle)
    return CycleOut.model_validate(cycle)


@router.post("/cycles/{cycle_id}/close", response_model=CycleOut)
async def close_cycle_route(
    cycle_id: int,
    admin: User = Depends(require_cap(Cap.MANAGE_CYCLES)),
    db: AsyncSession = Depends(get_session),
):
    cycle = await _get_cycle_or_404(db, cycle_id)
    await close_cycle(db, cycle)
    await audit.record(
        db, actor_user_id=admin.id, action="cycle.close", target_type="cycle", target_id=cycle.id
    )
    await db.commit()
    await db.refresh(cycle)
    return CycleOut.model_validate(cycle)


@router.get("/cycles/{cycle_id}/assignments", response_model=list[AssignmentAdminOut])
async def list_cycle_assignments(
    cycle_id: int,
    _: User = Depends(require_cap(Cap.MANAGE_CYCLES)),
    db: AsyncSession = Depends(get_session),
):
    await _get_cycle_or_404(db, cycle_id)
    assignments = (
        await db.scalars(
            select(ReviewAssignment)
            .where(ReviewAssignment.cycle_id == cycle_id)
            .order_by(ReviewAssignment.id)
        )
    ).all()
    names = {
        e.id: e.full_name for e in (await db.scalars(select(Employee))).all()
    }
    return [
        AssignmentAdminOut(
            id=a.id,
            cycle_id=a.cycle_id,
            subject_employee_id=a.subject_employee_id,
            subject_name=names.get(a.subject_employee_id, ""),
            reviewer_employee_id=a.reviewer_employee_id,
            reviewer_name=names.get(a.reviewer_employee_id, ""),
            status=a.status,
        )
        for a in assignments
    ]


@router.patch(
    "/cycles/{cycle_id}/assignments/{assignment_id}", response_model=AssignmentAdminOut
)
async def reassign_reviewer(
    cycle_id: int,
    assignment_id: int,
    payload: ReassignIn,
    admin: User = Depends(require_cap(Cap.MANAGE_CYCLES)),
    db: AsyncSession = Depends(get_session),
):
    cycle = await _get_cycle_or_404(db, cycle_id)
    if cycle.status != CycleStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Reviewers can only be changed on a draft cycle"
        )
    assignment = await db.get(ReviewAssignment, assignment_id)
    if not assignment or assignment.cycle_id != cycle_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    if payload.reviewer_employee_id == assignment.subject_employee_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "An employee cannot review themselves"
        )
    reviewer = await db.get(Employee, payload.reviewer_employee_id)
    if not reviewer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reviewer not found")

    assignment.reviewer_employee_id = payload.reviewer_employee_id
    await audit.record(
        db,
        actor_user_id=admin.id,
        action="cycle.reassign",
        target_type="assignment",
        target_id=assignment.id,
        detail={"reviewer_employee_id": reviewer.id},
    )
    await db.commit()

    subject = await db.get(Employee, assignment.subject_employee_id)
    return AssignmentAdminOut(
        id=assignment.id,
        cycle_id=assignment.cycle_id,
        subject_employee_id=assignment.subject_employee_id,
        subject_name=subject.full_name if subject else "",
        reviewer_employee_id=reviewer.id,
        reviewer_name=reviewer.full_name,
        status=assignment.status,
    )


# ------------------------------------------------------------- Reviewer flow
async def _my_employee(db: AsyncSession, user: User) -> Employee:
    emp = await db.scalar(select(Employee).where(Employee.user_id == user.id))
    if not emp:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record linked to user")
    return emp


async def _load_assignment(db: AsyncSession, assignment_id: int) -> ReviewAssignment:
    a = await db.get(ReviewAssignment, assignment_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    return a


async def _assert_reviewer_or_admin(
    db: AsyncSession, user: User, assignment: ReviewAssignment
) -> None:
    if can(user.role, Cap.MANAGE_CYCLES):  # HR / executive / admin can act on any
        return
    me = await _my_employee(db, user)
    if assignment.reviewer_employee_id != me.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your assignment")


async def _enrich(db: AsyncSession, a: ReviewAssignment) -> dict:
    subject = await db.get(Employee, a.subject_employee_id)
    cycle = await db.get(ReviewCycle, a.cycle_id)
    return {
        "subject_name": subject.full_name if subject else "",
        "subject_team": subject.team if subject else None,
        "cycle_year": cycle.year,
        "cycle_type": cycle.type,
        "cycle_status": cycle.status,
    }


@router.get("/reviews/mine", response_model=list[AssignmentSubjectOut])
async def my_reviews(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    me = await _my_employee(db, user)
    assignments = (
        await db.scalars(
            select(ReviewAssignment)
            .join(ReviewCycle, ReviewCycle.id == ReviewAssignment.cycle_id)
            .where(
                ReviewAssignment.reviewer_employee_id == me.id,
                ReviewCycle.status == CycleStatus.open,
            )
            .order_by(ReviewAssignment.id)
        )
    ).all()
    out = []
    for a in assignments:
        base = AssignmentOut.model_validate(a).model_dump()
        out.append(AssignmentSubjectOut(**base, **await _enrich(db, a)))
    return out


@router.get("/reviews/{assignment_id}", response_model=AssignmentDetailOut)
async def get_review(
    assignment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    a = await _load_assignment(db, assignment_id)
    # Reviewer, org-viewers (HR/exec/admin), or the subject themselves may view.
    is_org_viewer = can(user.role, Cap.VIEW_ORG)
    is_reviewer = False
    if not is_org_viewer:
        me = await _my_employee(db, user)
        if me.id not in (a.reviewer_employee_id, a.subject_employee_id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        is_reviewer = me.id == a.reviewer_employee_id
    # The subject must not see the reviewer's evaluation (scores + summary) until
    # it is submitted — otherwise in-progress manager feedback leaks early.
    reveal_reviewer = is_org_viewer or is_reviewer or a.status == ReviewStatus.submitted

    all_scores = (
        await db.scalars(select(ReviewScore).where(ReviewScore.assignment_id == a.id))
    ).all()
    reviewer_scores = [s for s in all_scores if s.author == ScoreAuthor.reviewer]
    self_scores = [s for s in all_scores if s.author == ScoreAuthor.self]

    base = AssignmentOut.model_validate(a).model_dump()
    if not reveal_reviewer:
        base["summary_comment"] = None
    return AssignmentDetailOut(
        **base,
        **await _enrich(db, a),
        scores=[ScoreOut.model_validate(s) for s in reviewer_scores] if reveal_reviewer else [],
        self_comment=a.self_comment,
        self_scores=[ScoreOut.model_validate(s) for s in self_scores],
    )


@router.put("/reviews/{assignment_id}/scores/{kpi_id}", response_model=ScoreOut)
async def upsert_score(
    assignment_id: int,
    kpi_id: int,
    payload: ScoreIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    a = await _load_assignment(db, assignment_id)
    await _assert_reviewer_or_admin(db, user, a)
    cycle = await db.get(ReviewCycle, a.cycle_id)
    ensure_editable(cycle, a)

    score = await db.scalar(
        select(ReviewScore).where(
            ReviewScore.assignment_id == assignment_id,
            ReviewScore.kpi_id == kpi_id,
            ReviewScore.author == ScoreAuthor.reviewer,
        )
    )
    if score:
        score.status = payload.status
        score.comment = payload.comment
    else:
        score = ReviewScore(
            assignment_id=assignment_id,
            kpi_id=kpi_id,
            author=ScoreAuthor.reviewer,
            status=payload.status,
            comment=payload.comment,
        )
        db.add(score)

    # First edit flips not_started -> in_progress.
    if a.status == ReviewStatus.not_started:
        a.status = ReviewStatus.in_progress

    await db.commit()
    await db.refresh(score)
    return ScoreOut.model_validate(score)


@router.post("/reviews/{assignment_id}/submit", response_model=AssignmentOut)
async def submit_review(
    assignment_id: int,
    payload: SubmitIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    a = await _load_assignment(db, assignment_id)
    await _assert_reviewer_or_admin(db, user, a)
    cycle = await db.get(ReviewCycle, a.cycle_id)

    missing = await missing_scored_kpis(
        db, assignment_id=a.id, author=ScoreAuthor.reviewer
    )
    if missing:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Every KPI needs a status and a comment before submitting. "
            f"Missing: {', '.join(missing)}",
        )

    # Self-first gate: a manager can only submit after the employee has submitted
    # their self-assessment. HR / executive / admin may override for stragglers.
    if a.self_status != ReviewStatus.submitted and not can(user.role, Cap.OVERRIDE_REVIEW):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The employee must submit their self-assessment before you can submit your review.",
        )

    await submit_assignment(db, cycle=cycle, assignment=a, summary=payload.summary_comment)
    await db.commit()
    await db.refresh(a)
    return AssignmentOut.model_validate(a)


# ------------------------------------------------------- Self-assessment flow
def _self_detail(
    a: ReviewAssignment, cycle: ReviewCycle, scores: list[ReviewScore]
) -> SelfDetailOut:
    return SelfDetailOut(
        id=a.id,
        cycle_id=a.cycle_id,
        cycle_year=cycle.year,
        cycle_type=cycle.type,
        cycle_status=cycle.status,
        self_status=a.self_status,
        self_submitted_at=a.self_submitted_at,
        self_comment=a.self_comment,
        scores=[ScoreOut.model_validate(s) for s in scores],
    )


async def _load_self_assignment(
    db: AsyncSession, user: User, assignment_id: int
) -> ReviewAssignment:
    a = await _load_assignment(db, assignment_id)
    if not can(user.role, Cap.VIEW_ORG):
        me = await _my_employee(db, user)
        if a.subject_employee_id != me.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your self-assessment")
    return a


@router.get("/self-assessments", response_model=list[SelfAssignmentOut])
async def my_self_assessments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    me = await _my_employee(db, user)
    assignments = (
        await db.scalars(
            select(ReviewAssignment)
            .join(ReviewCycle, ReviewCycle.id == ReviewAssignment.cycle_id)
            .where(
                ReviewAssignment.subject_employee_id == me.id,
                ReviewCycle.status == CycleStatus.open,
            )
            .order_by(ReviewAssignment.id)
        )
    ).all()
    out = []
    for a in assignments:
        cycle = await db.get(ReviewCycle, a.cycle_id)
        out.append(
            SelfAssignmentOut(
                id=a.id,
                cycle_id=a.cycle_id,
                cycle_year=cycle.year,
                cycle_type=cycle.type,
                cycle_status=cycle.status,
                self_status=a.self_status,
                self_submitted_at=a.self_submitted_at,
            )
        )
    return out


@router.get("/self-assessments/{assignment_id}", response_model=SelfDetailOut)
async def get_self_assessment(
    assignment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    a = await _load_self_assignment(db, user, assignment_id)
    cycle = await db.get(ReviewCycle, a.cycle_id)
    scores = (
        await db.scalars(
            select(ReviewScore).where(
                ReviewScore.assignment_id == a.id,
                ReviewScore.author == ScoreAuthor.self,
            )
        )
    ).all()
    return _self_detail(a, cycle, scores)


@router.put("/self-assessments/{assignment_id}/scores/{kpi_id}", response_model=ScoreOut)
async def upsert_self_score(
    assignment_id: int,
    kpi_id: int,
    payload: ScoreIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    a = await _load_self_assignment(db, user, assignment_id)
    cycle = await db.get(ReviewCycle, a.cycle_id)
    if cycle.status != CycleStatus.open:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cycle is not open for editing")
    if a.self_status == ReviewStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT, "Self-assessment already submitted")

    score = await db.scalar(
        select(ReviewScore).where(
            ReviewScore.assignment_id == assignment_id,
            ReviewScore.kpi_id == kpi_id,
            ReviewScore.author == ScoreAuthor.self,
        )
    )
    if score:
        score.status = payload.status
        score.comment = payload.comment
    else:
        score = ReviewScore(
            assignment_id=assignment_id,
            kpi_id=kpi_id,
            author=ScoreAuthor.self,
            status=payload.status,
            comment=payload.comment,
        )
        db.add(score)

    if a.self_status == ReviewStatus.not_started:
        a.self_status = ReviewStatus.in_progress

    await db.commit()
    await db.refresh(score)
    return ScoreOut.model_validate(score)


@router.post("/self-assessments/{assignment_id}/submit", response_model=SelfAssignmentOut)
async def submit_self_assessment(
    assignment_id: int,
    payload: SubmitIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    a = await _load_self_assignment(db, user, assignment_id)
    cycle = await db.get(ReviewCycle, a.cycle_id)
    if cycle.status != CycleStatus.open:
        raise HTTPException(status.HTTP_409_CONFLICT, "Cycle is not open")
    if a.self_status != ReviewStatus.submitted:
        missing = await missing_scored_kpis(
            db, assignment_id=a.id, author=ScoreAuthor.self
        )
        if missing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Every KPI needs a status and a comment before submitting. "
                f"Missing: {', '.join(missing)}",
            )
        a.self_status = ReviewStatus.submitted
        a.self_submitted_at = datetime.now(UTC)
    if payload.summary_comment is not None:
        a.self_comment = payload.summary_comment
    await db.commit()
    await db.refresh(a)
    return SelfAssignmentOut(
        id=a.id,
        cycle_id=a.cycle_id,
        cycle_year=cycle.year,
        cycle_type=cycle.type,
        cycle_status=cycle.status,
        self_status=a.self_status,
        self_submitted_at=a.self_submitted_at,
    )
