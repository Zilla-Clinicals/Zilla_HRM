from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models._base import TimestampMixin


class Goal(Base, TimestampMixin):
    """A yearly, employee-owned goal tracked with progress + dated check-ins."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False, default="performance")
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100
    status: Mapped[str] = mapped_column(Text, nullable=False, default="not_started")

    checkins: Mapped[list["GoalCheckin"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )


class GoalCheckin(Base):
    """A progress update (owner) or comment (manager/HR) on a goal."""

    __tablename__ = "goal_checkins"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    goal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    goal: Mapped["Goal"] = relationship(back_populates="checkins")
