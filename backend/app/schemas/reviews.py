from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models._base import CycleStatus, CycleType, KpiStatus, ReviewStatus


# ---------- Cycles ----------
class CycleCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    type: CycleType
    opens_at: datetime
    closes_at: datetime


class CycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    type: CycleType
    status: CycleStatus
    opens_at: datetime
    closes_at: datetime
    created_at: datetime
    updated_at: datetime


class AssignOverride(BaseModel):
    subject_employee_id: int
    reviewer_employee_id: int


class AssignIn(BaseModel):
    # Optional manual overrides; anything not listed is auto-derived from manager_id.
    overrides: list[AssignOverride] = Field(default_factory=list)
    # If true, only create assignments for employees who have a manager set.
    skip_without_manager: bool = True


class ReassignIn(BaseModel):
    reviewer_employee_id: int


class AssignmentAdminOut(BaseModel):
    """Assignment enriched with subject + reviewer names, for the HR cycle screen."""

    id: int
    cycle_id: int
    subject_employee_id: int
    subject_name: str
    reviewer_employee_id: int
    reviewer_name: str
    status: ReviewStatus


# ---------- Assignments / scores ----------
class ScoreIn(BaseModel):
    status: KpiStatus
    comment: str | None = None


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kpi_id: int
    status: KpiStatus
    comment: str | None = None


class SubmitIn(BaseModel):
    summary_comment: str | None = None


class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cycle_id: int
    subject_employee_id: int
    reviewer_employee_id: int
    status: ReviewStatus
    submitted_at: datetime | None = None
    summary_comment: str | None = None
    self_status: ReviewStatus = ReviewStatus.not_started


class AssignmentSubjectOut(AssignmentOut):
    """Assignment enriched with the subject's name/team and cycle label."""

    subject_name: str
    subject_team: str | None = None
    cycle_year: int
    cycle_type: CycleType
    cycle_status: CycleStatus


class AssignmentDetailOut(AssignmentSubjectOut):
    scores: list[ScoreOut] = Field(default_factory=list)
    # The subject's self-assessment, shown to the reviewer side by side.
    self_comment: str | None = None
    self_scores: list[ScoreOut] = Field(default_factory=list)


# ---------- Self-assessment (subject-facing) ----------
class SelfAssignmentOut(BaseModel):
    """A subject's own assignment, from their self-assessment perspective."""

    id: int
    cycle_id: int
    cycle_year: int
    cycle_type: CycleType
    cycle_status: CycleStatus
    self_status: ReviewStatus
    self_submitted_at: datetime | None = None


class SelfDetailOut(SelfAssignmentOut):
    self_comment: str | None = None
    scores: list[ScoreOut] = Field(default_factory=list)  # the subject's own self scores


class ReviewHistoryItem(BaseModel):
    """One past review of an employee (as subject)."""

    assignment_id: int
    cycle_id: int
    cycle_year: int
    cycle_type: CycleType
    cycle_status: CycleStatus
    status: ReviewStatus
    submitted_at: datetime | None = None
    summary_comment: str | None = None
    weighted_total: float | None = None
    scores: list[ScoreOut] = Field(default_factory=list)
