from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionType = Literal[
    "short_text",
    "long_text",
    "single_choice",
    "multi_choice",
    "dropdown",
    "rating",
    "yes_no",
    "date",
]

CHOICE_TYPES = {"single_choice", "multi_choice", "dropdown"}


# ---------------------------------------------------------------- Questions
class QuestionIn(BaseModel):
    type: QuestionType
    prompt: str = Field(min_length=1, max_length=500)
    required: bool = False
    choices: list[str] | None = None  # for choice types
    scale_max: int | None = Field(default=None, ge=2, le=10)  # for rating


class QuestionOut(BaseModel):
    id: int
    position: int
    type: QuestionType
    prompt: str
    required: bool
    choices: list[str] | None = None
    scale_max: int | None = None


# ---------------------------------------------------------------- Surveys
class SurveyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    anonymous: bool = False


class SurveyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    anonymous: bool | None = None
    closes_at: datetime | None = None


class SurveyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    status: str
    anonymous: bool
    created_by: int | None = None
    closes_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    question_count: int = 0
    assigned_count: int = 0
    response_count: int = 0


class SurveyDetailOut(SurveyOut):
    questions: list[QuestionOut] = Field(default_factory=list)


# ---------------------------------------------------------------- Assignment
class AssignIn(BaseModel):
    scope: Literal["all", "team", "employees"]
    employee_ids: list[int] = Field(default_factory=list)


class AssignmentStatusOut(BaseModel):
    employee_id: int
    name: str
    completed: bool


# ---------------------------------------------------------------- Respond
class AnswerIn(BaseModel):
    question_id: int
    value: Any = None


class RespondIn(BaseModel):
    answers: list[AnswerIn] = Field(default_factory=list)


class AssignedSurveyOut(BaseModel):
    """A survey as seen by someone it's assigned to."""

    id: int
    title: str
    description: str | None = None
    status: str
    anonymous: bool
    completed: bool
    closes_at: datetime | None = None


class SurveyFillOut(BaseModel):
    """The survey + questions to fill in (respondent view)."""

    id: int
    title: str
    description: str | None = None
    anonymous: bool
    completed: bool
    questions: list[QuestionOut] = Field(default_factory=list)


# ---------------------------------------------------------------- Results
class OptionCount(BaseModel):
    label: str
    count: int


class QuestionResult(BaseModel):
    question_id: int
    prompt: str
    type: QuestionType
    total_answers: int
    counts: list[OptionCount] | None = None  # choice/yes_no
    average: float | None = None  # rating
    texts: list[str] | None = None  # text/date


class SurveyResultsOut(BaseModel):
    survey_id: int
    title: str
    anonymous: bool
    assigned_count: int
    response_count: int
    questions: list[QuestionResult] = Field(default_factory=list)
