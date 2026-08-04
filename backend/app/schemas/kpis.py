from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class KpiBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = None
    measurement: str | None = None
    target: str | None = None


class KpiCreate(KpiBase):
    pass


class KpiUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    measurement: str | None = None
    target: str | None = None
    is_active: bool | None = None


class KpiOut(KpiBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    # Derived from the KPI's category (weight / # active KPIs in category).
    category_weight: float | None = None
    points: float = 0.0
    created_at: datetime
    updated_at: datetime


# ---------- Categories ----------
class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    weight: Decimal
    is_active: bool
    kpi_count: int = 0
    points_per_kpi: float = 0.0


class CategoryUpdate(BaseModel):
    weight: Decimal = Field(ge=0, le=100)
