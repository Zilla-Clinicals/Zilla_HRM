from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._base import (
    CycleStatus,
    CycleType,
    KpiStatus,
    ReviewStatus,
    ScoreAuthor,
    TimestampMixin,
)

cycle_type_enum = Enum(
    CycleType, name="cycle_type_enum", values_callable=lambda e: [m.value for m in e]
)
cycle_status_enum = Enum(
    CycleStatus, name="cycle_status_enum", values_callable=lambda e: [m.value for m in e]
)
review_status_enum = Enum(
    ReviewStatus, name="review_status_enum", values_callable=lambda e: [m.value for m in e]
)
score_author_enum = Enum(
    ScoreAuthor, name="score_author_enum", values_callable=lambda e: [m.value for m in e]
)
kpi_status_enum = Enum(
    KpiStatus, name="kpi_status_enum", values_callable=lambda e: [m.value for m in e]
)


class ReviewCycle(Base, TimestampMixin):
    __tablename__ = "review_cycles"
    __table_args__ = (UniqueConstraint("year", "type", name="uq_cycle_year_type"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[CycleType] = mapped_column(cycle_type_enum, nullable=False)
    status: Mapped[CycleStatus] = mapped_column(
        cycle_status_enum, nullable=False, default=CycleStatus.draft
    )
    opens_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    assignments: Mapped[list["ReviewAssignment"]] = relationship(
        back_populates="cycle", cascade="all, delete-orphan"
    )


class ReviewAssignment(Base, TimestampMixin):
    __tablename__ = "review_assignments"
    __table_args__ = (
        UniqueConstraint(
            "cycle_id", "subject_employee_id", name="uq_assignment_cycle_subject"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cycle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("review_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject_employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ReviewStatus] = mapped_column(
        review_status_enum, nullable=False, default=ReviewStatus.not_started
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    summary_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Subject's self-assessment, tracked independently of the reviewer's.
    self_status: Mapped[ReviewStatus] = mapped_column(
        review_status_enum, nullable=False, default=ReviewStatus.not_started
    )
    self_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    self_comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    cycle: Mapped["ReviewCycle"] = relationship(back_populates="assignments")
    scores: Mapped[list["ReviewScore"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class ReviewScore(Base, TimestampMixin):
    __tablename__ = "review_scores"
    __table_args__ = (
        UniqueConstraint(
            "assignment_id", "kpi_id", "author", name="uq_score_assignment_kpi_author"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("review_assignments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kpi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kpis.id", ondelete="RESTRICT"), nullable=False
    )
    author: Mapped[ScoreAuthor] = mapped_column(
        score_author_enum, nullable=False, default=ScoreAuthor.reviewer
    )
    status: Mapped[KpiStatus] = mapped_column(kpi_status_enum, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    assignment: Mapped["ReviewAssignment"] = relationship(back_populates="scores")
    kpi: Mapped["Kpi"] = relationship()  # noqa: F821
