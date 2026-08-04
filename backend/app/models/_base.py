import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class Role(enum.StrEnum):
    admin = "admin"  # developer superuser — all rights
    executive = "executive"  # CEO / VP Operations — org-wide view + all actions
    hr = "hr"  # manages people + runs the review process
    manager = "manager"  # team lead — reviews their reports
    employee = "employee"  # self-assessment + own results


class CycleType(enum.StrEnum):
    mid_year = "mid_year"
    end_year = "end_year"


class CycleStatus(enum.StrEnum):
    draft = "draft"
    open = "open"
    closed = "closed"


class ReviewStatus(enum.StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    submitted = "submitted"


class ScoreAuthor(enum.StrEnum):
    self = "self"  # the subject's own self-assessment
    reviewer = "reviewer"  # the assigned reviewer's official scores


class KpiStatus(enum.StrEnum):
    """Workbook scoring: Met = 100%, Partial = 50%, Not Met = 0% of KPI points."""

    met = "met"
    partial = "partial"
    not_met = "not_met"


# Fraction of a KPI's points earned for each status.
STATUS_FACTOR: dict[KpiStatus, float] = {
    KpiStatus.met: 1.0,
    KpiStatus.partial: 0.5,
    KpiStatus.not_met: 0.0,
}


class TimestampMixin:
    """Adds server-defaulted created_at / updated_at (TIMESTAMPTZ).

    updated_at is maintained by a DB trigger (installed in migration 0001);
    the onupdate here keeps ORM-side flushes consistent too.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
