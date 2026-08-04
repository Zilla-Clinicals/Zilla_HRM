from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._base import TimestampMixin


class Survey(Base, TimestampMixin):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")  # draft|open|closed
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    questions: Mapped[list["SurveyQuestion"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan", order_by="SurveyQuestion.position"
    )


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # {"choices": [...]} for choice types, {"max": 5} for rating
    options: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    survey: Mapped["Survey"] = relationship(back_populates="questions")


class SurveyAssignment(Base):
    __tablename__ = "survey_assignments"
    __table_args__ = (
        UniqueConstraint("survey_id", "employee_id", name="uq_survey_assignment"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # NULL when the survey is anonymous — responses can't be linked to a person
    respondent_employee_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    answers: Mapped[list["SurveyAnswer"]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )


class SurveyAnswer(Base):
    __tablename__ = "survey_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    response_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("survey_responses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {"v": <answer>}

    response: Mapped["SurveyResponse"] = relationship(back_populates="answers")
