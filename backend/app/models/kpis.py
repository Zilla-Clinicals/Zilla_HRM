from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models._base import TimestampMixin


class KpiCategory(Base, TimestampMixin):
    """A weighted scoring category. Category weights are meant to sum to 100."""

    __tablename__ = "kpi_categories"
    __table_args__ = (UniqueConstraint("name", name="uq_kpi_categories_name"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Kpi(Base, TimestampMixin):
    __tablename__ = "kpis"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)  # matches KpiCategory.name
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurement: Mapped[str | None] = mapped_column(Text, nullable=True)
    target: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
