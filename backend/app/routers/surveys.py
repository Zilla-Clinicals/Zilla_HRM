from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_cap
from app.auth.permissions import Cap, can
from app.db import get_session
from app.models.employees import Employee
from app.models.surveys import (
    Survey,
    SurveyAnswer,
    SurveyAssignment,
    SurveyQuestion,
    SurveyResponse,
)
from app.models.users import User
from app.schemas.surveys import (
    CHOICE_TYPES,
    AssignedSurveyOut,
    AssignIn,
    AssignmentStatusOut,
    OptionCount,
    QuestionIn,
    QuestionOut,
    QuestionResult,
    RespondIn,
    SurveyCreate,
    SurveyDetailOut,
    SurveyFillOut,
    SurveyOut,
    SurveyResultsOut,
    SurveyUpdate,
)
from app.services import audit

router = APIRouter(prefix="/api/surveys", tags=["surveys"])


# --------------------------------------------------------------- helpers
async def _my_employee(db: AsyncSession, user: User) -> Employee:
    emp = await db.scalar(select(Employee).where(Employee.user_id == user.id))
    if not emp:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record linked to user")
    return emp


def _question_out(q: SurveyQuestion) -> QuestionOut:
    opts = q.options or {}
    return QuestionOut(
        id=q.id,
        position=q.position,
        type=q.type,
        prompt=q.prompt,
        required=q.required,
        choices=opts.get("choices"),
        scale_max=opts.get("max"),
    )


def _options_for(payload: QuestionIn) -> dict | None:
    if payload.type in CHOICE_TYPES:
        choices = [c.strip() for c in (payload.choices or []) if c.strip()]
        if len(choices) < 2:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Choice questions need at least 2 options"
            )
        return {"choices": choices}
    if payload.type == "rating":
        return {"max": payload.scale_max or 5}
    return None


async def _load_survey(db: AsyncSession, survey_id: int) -> Survey:
    s = await db.get(Survey, survey_id)
    if not s:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Survey not found")
    return s


def _can_manage(user: User, survey: Survey) -> bool:
    return can(user.role, Cap.MANAGE_SURVEYS) or survey.created_by == user.id


async def _assert_manage(user: User, survey: Survey) -> None:
    if not _can_manage(user, survey):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your survey")


async def _count(db: AsyncSession, model, survey_id: int) -> int:
    n = await db.scalar(
        select(func.count()).select_from(model).where(model.survey_id == survey_id)
    )
    return n or 0


async def _counts(db: AsyncSession, survey_id: int) -> tuple[int, int, int]:
    return (
        await _count(db, SurveyQuestion, survey_id),
        await _count(db, SurveyAssignment, survey_id),
        await _count(db, SurveyResponse, survey_id),
    )


async def _survey_out(db: AsyncSession, survey: Survey) -> SurveyOut:
    qn, an, rn = await _counts(db, survey.id)
    return SurveyOut.model_validate(survey).model_copy(
        update={"question_count": qn, "assigned_count": an, "response_count": rn}
    )


# --------------------------------------------------------- create / list
@router.post("", response_model=SurveyDetailOut, status_code=status.HTTP_201_CREATED)
async def create_survey(
    payload: SurveyCreate,
    user: User = Depends(require_cap(Cap.CREATE_SURVEYS)),
    db: AsyncSession = Depends(get_session),
):
    survey = Survey(
        title=payload.title,
        description=payload.description,
        anonymous=payload.anonymous,
        created_by=user.id,
    )
    db.add(survey)
    await db.flush()  # assign survey.id for the audit entry
    await audit.record(
        db,
        actor_user_id=user.id,
        action="survey.create",
        target_type="survey",
        target_id=survey.id,
        detail={"title": survey.title, "anonymous": survey.anonymous},
    )
    await db.commit()
    await db.refresh(survey)
    base = await _survey_out(db, survey)
    return SurveyDetailOut(**base.model_dump(), questions=[])


@router.get("", response_model=list[SurveyOut])
async def list_surveys(
    user: User = Depends(require_cap(Cap.CREATE_SURVEYS)),
    db: AsyncSession = Depends(get_session),
):
    stmt = select(Survey).order_by(Survey.id.desc())
    if not can(user.role, Cap.MANAGE_SURVEYS):
        stmt = stmt.where(Survey.created_by == user.id)
    surveys = (await db.scalars(stmt)).all()
    return [await _survey_out(db, s) for s in surveys]


# --------------------------------------------------- respondent: assigned
@router.get("/assigned", response_model=list[AssignedSurveyOut])
async def my_assigned_surveys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    me = await _my_employee(db, user)
    rows = (
        await db.execute(
            select(Survey, SurveyAssignment.completed)
            .join(SurveyAssignment, SurveyAssignment.survey_id == Survey.id)
            .where(
                SurveyAssignment.employee_id == me.id,
                Survey.status == "open",
            )
            .order_by(Survey.id.desc())
        )
    ).all()
    return [
        AssignedSurveyOut(
            id=s.id,
            title=s.title,
            description=s.description,
            status=s.status,
            anonymous=s.anonymous,
            completed=completed,
            closes_at=s.closes_at,
        )
        for s, completed in rows
    ]


# ------------------------------------------------------- get / edit survey
@router.get("/{survey_id}", response_model=SurveyDetailOut)
async def get_survey(
    survey_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    questions = (
        await db.scalars(
            select(SurveyQuestion)
            .where(SurveyQuestion.survey_id == survey_id)
            .order_by(SurveyQuestion.position)
        )
    ).all()
    base = await _survey_out(db, survey)
    return SurveyDetailOut(**base.model_dump(), questions=[_question_out(q) for q in questions])


@router.patch("/{survey_id}", response_model=SurveyOut)
async def update_survey(
    survey_id: int,
    payload: SurveyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    if survey.status != "draft" and (payload.anonymous is not None):
        raise HTTPException(status.HTTP_409_CONFLICT, "Can't change anonymity after opening")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(survey, field, value)
    await db.commit()
    await db.refresh(survey)
    return await _survey_out(db, survey)


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(
    survey_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    await db.delete(survey)
    await db.commit()


# ------------------------------------------------------------- questions
def _assert_draft(survey: Survey) -> None:
    if survey.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Questions can only be edited while the survey is a draft"
        )


@router.post("/{survey_id}/questions", response_model=QuestionOut, status_code=201)
async def add_question(
    survey_id: int,
    payload: QuestionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    _assert_draft(survey)
    n = await _count(db, SurveyQuestion, survey_id)
    q = SurveyQuestion(
        survey_id=survey_id,
        position=n + 1,
        type=payload.type,
        prompt=payload.prompt,
        required=payload.required,
        options=_options_for(payload),
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return _question_out(q)


@router.patch("/{survey_id}/questions/{qid}", response_model=QuestionOut)
async def update_question(
    survey_id: int,
    qid: int,
    payload: QuestionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    _assert_draft(survey)
    q = await db.get(SurveyQuestion, qid)
    if not q or q.survey_id != survey_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    q.type = payload.type
    q.prompt = payload.prompt
    q.required = payload.required
    q.options = _options_for(payload)
    await db.commit()
    await db.refresh(q)
    return _question_out(q)


@router.delete("/{survey_id}/questions/{qid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    survey_id: int,
    qid: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    _assert_draft(survey)
    q = await db.get(SurveyQuestion, qid)
    if not q or q.survey_id != survey_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found")
    await db.delete(q)
    await db.commit()


# -------------------------------------------------------------- assign
@router.post("/{survey_id}/assign", response_model=SurveyOut)
async def assign_survey(
    survey_id: int,
    payload: AssignIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)

    if can(user.role, Cap.MANAGE_SURVEYS):
        # HR / exec / admin: anyone or everyone
        if payload.scope == "all":
            targets = set(
                (await db.scalars(select(Employee.id))).all()
            )
        else:  # "team" is not meaningful for org-wide managers; treat as explicit list
            targets = set(payload.employee_ids)
    else:
        # Team leads: only their direct reports
        me = await _my_employee(db, user)
        reports = set(
            (await db.scalars(select(Employee.id).where(Employee.manager_id == me.id))).all()
        )
        if payload.scope in ("all", "team"):
            targets = reports
        else:
            targets = set(payload.employee_ids) & reports  # never outside the team

    if not targets:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No valid recipients to assign")

    existing = set(
        (
            await db.scalars(
                select(SurveyAssignment.employee_id).where(
                    SurveyAssignment.survey_id == survey_id
                )
            )
        ).all()
    )
    new_targets = targets - existing
    for eid in new_targets:
        db.add(SurveyAssignment(survey_id=survey_id, employee_id=eid))
    await audit.record(
        db,
        actor_user_id=user.id,
        action="survey.assign",
        target_type="survey",
        target_id=survey_id,
        detail={"added": len(new_targets)},
    )
    await db.commit()
    await db.refresh(survey)
    return await _survey_out(db, survey)


@router.post("/{survey_id}/open", response_model=SurveyOut)
async def open_survey(
    survey_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    qn, an, _ = await _counts(db, survey_id)
    if qn == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Add at least one question first")
    if an == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Assign recipients first")
    survey.status = "open"
    await audit.record(
        db,
        actor_user_id=user.id,
        action="survey.open",
        target_type="survey",
        target_id=survey_id,
    )
    await db.commit()
    await db.refresh(survey)
    return await _survey_out(db, survey)


@router.post("/{survey_id}/close", response_model=SurveyOut)
async def close_survey(
    survey_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    survey.status = "closed"
    await audit.record(
        db,
        actor_user_id=user.id,
        action="survey.close",
        target_type="survey",
        target_id=survey_id,
    )
    await db.commit()
    await db.refresh(survey)
    return await _survey_out(db, survey)


@router.get("/{survey_id}/assignments", response_model=list[AssignmentStatusOut])
async def survey_assignments(
    survey_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    rows = (
        await db.execute(
            select(
                SurveyAssignment.employee_id, Employee.full_name, SurveyAssignment.completed
            )
            .join(Employee, Employee.id == SurveyAssignment.employee_id)
            .where(SurveyAssignment.survey_id == survey_id)
            .order_by(Employee.full_name)
        )
    ).all()
    return [
        AssignmentStatusOut(employee_id=eid, name=name, completed=completed)
        for eid, name, completed in rows
    ]


# --------------------------------------------------------- respond / fill
@router.get("/{survey_id}/fill", response_model=SurveyFillOut)
async def get_fill(
    survey_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    me = await _my_employee(db, user)
    assignment = await db.scalar(
        select(SurveyAssignment).where(
            SurveyAssignment.survey_id == survey_id, SurveyAssignment.employee_id == me.id
        )
    )
    if not assignment:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This survey isn't assigned to you")
    if survey.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This survey isn't open")
    questions = (
        await db.scalars(
            select(SurveyQuestion)
            .where(SurveyQuestion.survey_id == survey_id)
            .order_by(SurveyQuestion.position)
        )
    ).all()
    return SurveyFillOut(
        id=survey.id,
        title=survey.title,
        description=survey.description,
        anonymous=survey.anonymous,
        completed=assignment.completed,
        questions=[_question_out(q) for q in questions],
    )


def _validate_answer(q: SurveyQuestion, value) -> None:
    opts = q.options or {}
    if q.type in CHOICE_TYPES:
        choices = opts.get("choices", [])
        if q.type == "multi_choice":
            if not isinstance(value, list) or any(v not in choices for v in value):
                raise HTTPException(400, f"Invalid selection for '{q.prompt}'")
        else:
            if value not in choices:
                raise HTTPException(400, f"Invalid selection for '{q.prompt}'")
    elif q.type == "rating":
        mx = opts.get("max", 5)
        if not isinstance(value, int) or not (1 <= value <= mx):
            raise HTTPException(400, f"Invalid rating for '{q.prompt}'")
    elif q.type == "yes_no":
        if value not in (True, False, "yes", "no"):
            raise HTTPException(400, f"Invalid answer for '{q.prompt}'")


def _is_empty(value) -> bool:
    return value is None or value == "" or value == []


@router.post("/{survey_id}/respond", status_code=status.HTTP_204_NO_CONTENT)
async def respond(
    survey_id: int,
    payload: RespondIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    me = await _my_employee(db, user)
    assignment = await db.scalar(
        select(SurveyAssignment).where(
            SurveyAssignment.survey_id == survey_id, SurveyAssignment.employee_id == me.id
        )
    )
    if not assignment:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This survey isn't assigned to you")
    if survey.status != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "This survey isn't open")
    if assignment.completed:
        raise HTTPException(status.HTTP_409_CONFLICT, "You've already responded")

    questions = {
        q.id: q
        for q in (
            await db.scalars(
                select(SurveyQuestion).where(SurveyQuestion.survey_id == survey_id)
            )
        ).all()
    }
    answers = {a.question_id: a.value for a in payload.answers}

    # validate required + values
    for qid, q in questions.items():
        val = answers.get(qid)
        if q.required and _is_empty(val):
            raise HTTPException(400, f"'{q.prompt}' is required")
        if not _is_empty(val):
            _validate_answer(q, val)

    response = SurveyResponse(
        survey_id=survey_id,
        respondent_employee_id=None if survey.anonymous else me.id,
    )
    db.add(response)
    await db.flush()
    for a in payload.answers:
        if a.question_id in questions and not _is_empty(a.value):
            db.add(
                SurveyAnswer(
                    response_id=response.id,
                    question_id=a.question_id,
                    value={"v": a.value},
                )
            )
    assignment.completed = True
    await audit.record(
        db,
        # Preserve anonymity — never attribute a response to a user on an
        # anonymous survey, even in the audit trail.
        actor_user_id=None if survey.anonymous else user.id,
        action="survey.respond",
        target_type="survey",
        target_id=survey_id,
        detail={"anonymous": survey.anonymous},
    )
    await db.commit()


# ------------------------------------------------------------- results
@router.get("/{survey_id}/results", response_model=SurveyResultsOut)
async def survey_results(
    survey_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    survey = await _load_survey(db, survey_id)
    await _assert_manage(user, survey)
    _, an, rn = await _counts(db, survey_id)

    questions = (
        await db.scalars(
            select(SurveyQuestion)
            .where(SurveyQuestion.survey_id == survey_id)
            .order_by(SurveyQuestion.position)
        )
    ).all()

    # all answers for this survey, grouped by question
    rows = (
        await db.execute(
            select(SurveyAnswer.question_id, SurveyAnswer.value)
            .join(SurveyResponse, SurveyResponse.id == SurveyAnswer.response_id)
            .where(SurveyResponse.survey_id == survey_id)
        )
    ).all()
    by_q: dict[int, list] = {}
    for qid, value in rows:
        by_q.setdefault(qid, []).append((value or {}).get("v"))

    results: list[QuestionResult] = []
    for q in questions:
        vals = by_q.get(q.id, [])
        opts = q.options or {}
        res = QuestionResult(
            question_id=q.id, prompt=q.prompt, type=q.type, total_answers=len(vals)
        )
        if q.type in CHOICE_TYPES:
            counter: Counter = Counter()
            for v in vals:
                if isinstance(v, list):
                    counter.update(v)
                elif v is not None:
                    counter[v] += 1
            labels = opts.get("choices", [])
            res.counts = [OptionCount(label=lbl, count=counter.get(lbl, 0)) for lbl in labels]
        elif q.type == "yes_no":
            counter = Counter(
                "Yes" if v in (True, "yes") else "No" for v in vals if v is not None
            )
            res.counts = [
                OptionCount(label=lbl, count=counter.get(lbl, 0)) for lbl in ("Yes", "No")
            ]
        elif q.type == "rating":
            nums = [v for v in vals if isinstance(v, int)]
            res.average = round(sum(nums) / len(nums), 2) if nums else None
            mx = opts.get("max", 5)
            c = Counter(nums)
            res.counts = [OptionCount(label=str(i), count=c.get(i, 0)) for i in range(1, mx + 1)]
        else:  # text / date
            res.texts = [str(v) for v in vals if v is not None]
        results.append(res)

    return SurveyResultsOut(
        survey_id=survey.id,
        title=survey.title,
        anonymous=survey.anonymous,
        assigned_count=an,
        response_count=rn,
        questions=results,
    )
