from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GoalCategory = Literal["performance", "development", "business", "other"]
GoalStatus = Literal["not_started", "in_progress", "completed", "cancelled"]


class GoalCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    category: GoalCategory = "performance"
    target_date: date | None = None


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    category: GoalCategory | None = None
    target_date: date | None = None
    status: GoalStatus | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class CheckinCreate(BaseModel):
    progress: int | None = Field(default=None, ge=0, le=100)
    note: str | None = None


class CheckinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    progress: int | None = None
    note: str | None = None
    created_by: int | None = None
    author_name: str | None = None
    created_at: datetime


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    employee_name: str | None = None
    year: int
    title: str
    description: str | None = None
    category: GoalCategory
    target_date: date | None = None
    progress: int
    status: GoalStatus
    checkin_count: int = 0
    created_at: datetime
    updated_at: datetime


class GoalDetailOut(GoalOut):
    checkins: list[CheckinOut] = Field(default_factory=list)
