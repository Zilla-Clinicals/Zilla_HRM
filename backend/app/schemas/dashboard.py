from pydantic import BaseModel

from app.models._base import CycleStatus, CycleType


class StatusBucket(BaseModel):
    label: str  # "Met" | "Partial" | "Not Met"
    count: int


class TeamAverage(BaseModel):
    team: str
    average_score: float  # out of 100
    subject_count: int


class CategoryRollup(BaseModel):
    category: str
    max_points: float  # category weight
    earned_avg: float  # average points earned across scored assignments
    status_band: str  # "On Track" | "Needs Attention" | "Improve"


class Breakdown(BaseModel):
    label: str
    count: int


class OrgOverviewOut(BaseModel):
    total_employees: int
    active_employees: int
    pending_employees: int
    inactive_employees: int
    managers: int
    teams: int
    new_hires_90d: int
    open_cycles: int
    headcount_by_team: list[Breakdown]
    employment_type_breakdown: list[Breakdown]
    gender_breakdown: list[Breakdown]


class CycleDashboardOut(BaseModel):
    cycle_id: int
    year: int
    type: CycleType
    status: CycleStatus
    total_assignments: int
    submitted_assignments: int
    completion_rate: float  # 0..1
    average_score: float | None  # out of 100
    status_distribution: list[StatusBucket]
    category_rollup: list[CategoryRollup]
    team_averages: list[TeamAverage]
