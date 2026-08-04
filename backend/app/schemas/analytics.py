from pydantic import BaseModel

from app.models._base import CycleType


class TrendCycle(BaseModel):
    cycle_id: int
    label: str
    year: int
    type: CycleType
    avg_score: float | None  # /100, reviewer scores
    completion_rate: float
    reviewed_count: int


class Series(BaseModel):
    name: str
    max_points: float | None = None  # for category series
    values: list[float | None]  # aligned to cycles order


class SummaryOut(BaseModel):
    cycles: list[TrendCycle]
    category_series: list[Series]
    team_series: list[Series]
    latest_cycle_id: int | None


class KpiInsight(BaseModel):
    name: str
    category: str
    max_points: float
    earned_avg: float
    pct: float  # 0..1 of max
    met: int
    partial: int
    not_met: int


class CalibrationCategory(BaseModel):
    category: str
    self_pct: float  # 0..1 of max
    reviewer_pct: float


class CycleAnalyticsOut(BaseModel):
    cycle_id: int
    label: str
    kpis: list[KpiInsight]
    calibration: list[CalibrationCategory]
    calibration_overall_self: float | None
    calibration_overall_reviewer: float | None
    calibration_pairs: int


class EmployeeTrajectory(BaseModel):
    employee_id: int
    name: str
    team: str | None
    values: list[float | None]  # score per cycle (aligned to cycles)
    latest: float | None
    delta: float | None  # latest vs the previous scored cycle


class EmployeesOut(BaseModel):
    cycles: list[str]  # labels
    employees: list[EmployeeTrajectory]
