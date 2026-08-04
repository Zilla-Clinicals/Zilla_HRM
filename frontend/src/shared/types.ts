export type Role = "admin" | "executive" | "hr" | "manager" | "employee";
export type CycleType = "mid_year" | "end_year";
export type CycleStatus = "draft" | "open" | "closed";
export type ReviewStatus = "not_started" | "in_progress" | "submitted";
export type KpiStatus = "met" | "partial" | "not_met";

export interface User {
  id: number;
  email: string;
  role: Role;
  is_active: boolean;
  mfa_enabled: boolean;
  created_at: string;
}

export type EmployeeStatus = "active" | "pending" | "inactive";
export type Gender = "male" | "female" | "other" | "prefer_not_to_say";
export type MaritalStatus = "single" | "married" | "divorced" | "widowed";
export type EmploymentType = "full_time" | "part_time" | "contract" | "intern";

export interface Employee {
  id: number;
  user_id: number;
  email: string | null;
  role: Role | null;
  is_active: boolean;
  status: EmployeeStatus;
  has_photo: boolean;
  full_name: string;
  // Personal
  date_of_birth: string | null;
  gender: Gender | null;
  marital_status: MaritalStatus | null;
  nationality: string | null;
  personal_email: string | null;
  phone: string | null;
  address: string | null;
  city: string | null;
  country: string | null;
  // Employment
  employee_number: string | null;
  job_title: string | null;
  team: string | null;
  employment_type: EmploymentType | null;
  work_location: string | null;
  hire_date: string | null;
  manager_id: number | null;
  // Emergency contact
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  emergency_contact_relationship: string | null;
  created_at: string;
  updated_at: string;
}

export interface Me {
  user: User;
  employee: Employee | null;
}

export interface Kpi {
  id: number;
  name: string;
  category: string;
  description: string | null;
  measurement: string | null;
  target: string | null;
  is_active: boolean;
  category_weight: string | null;
  points: number;
  created_at: string;
  updated_at: string;
}

export interface KpiCategory {
  id: number;
  name: string;
  weight: string;
  is_active: boolean;
  kpi_count: number;
  points_per_kpi: number;
}

export interface Cycle {
  id: number;
  year: number;
  type: CycleType;
  status: CycleStatus;
  opens_at: string;
  closes_at: string;
  created_at: string;
  updated_at: string;
}

export interface Score {
  id: number;
  kpi_id: number;
  status: KpiStatus;
  comment: string | null;
}

export interface Assignment {
  id: number;
  cycle_id: number;
  subject_employee_id: number;
  reviewer_employee_id: number;
  status: ReviewStatus;
  submitted_at: string | null;
  summary_comment: string | null;
  self_status: ReviewStatus;
}

export interface AssignmentSubject extends Assignment {
  subject_name: string;
  subject_team: string | null;
  cycle_year: number;
  cycle_type: CycleType;
  cycle_status: CycleStatus;
}

export interface AssignmentDetail extends AssignmentSubject {
  scores: Score[];
  self_comment: string | null;
  self_scores: Score[];
}

export interface SelfAssignment {
  id: number;
  cycle_id: number;
  cycle_year: number;
  cycle_type: CycleType;
  cycle_status: CycleStatus;
  self_status: ReviewStatus;
  self_submitted_at: string | null;
}

export interface SelfDetail extends SelfAssignment {
  self_comment: string | null;
  scores: Score[];
}

export interface AssignmentAdmin {
  id: number;
  cycle_id: number;
  subject_employee_id: number;
  subject_name: string;
  reviewer_employee_id: number;
  reviewer_name: string;
  status: ReviewStatus;
}

export interface ReviewHistoryItem {
  assignment_id: number;
  cycle_id: number;
  cycle_year: number;
  cycle_type: CycleType;
  cycle_status: CycleStatus;
  status: ReviewStatus;
  submitted_at: string | null;
  summary_comment: string | null;
  weighted_total: number | null;
  scores: Score[];
}

export interface StatusBucket {
  label: string;
  count: number;
}

export interface TeamAverage {
  team: string;
  average_score: number; // out of 100
  subject_count: number;
}

export interface CategoryRollup {
  category: string;
  max_points: number;
  earned_avg: number;
  status_band: string; // "On Track" | "Needs Attention" | "Improve"
}

export interface Breakdown {
  label: string;
  count: number;
}

export interface OrgOverview {
  total_employees: number;
  active_employees: number;
  pending_employees: number;
  inactive_employees: number;
  managers: number;
  teams: number;
  new_hires_90d: number;
  open_cycles: number;
  headcount_by_team: Breakdown[];
  employment_type_breakdown: Breakdown[];
  gender_breakdown: Breakdown[];
}

export interface CycleDashboard {
  cycle_id: number;
  year: number;
  type: CycleType;
  status: CycleStatus;
  total_assignments: number;
  submitted_assignments: number;
  completion_rate: number;
  average_score: number | null; // out of 100
  status_distribution: StatusBucket[];
  category_rollup: CategoryRollup[];
  team_averages: TeamAverage[];
}

// ---------- Goals ----------
export type GoalCategory = "performance" | "development" | "business" | "other";
export type GoalStatus = "not_started" | "in_progress" | "completed" | "cancelled";

export interface Goal {
  id: number;
  employee_id: number;
  employee_name: string | null;
  year: number;
  title: string;
  description: string | null;
  category: GoalCategory;
  target_date: string | null;
  progress: number;
  status: GoalStatus;
  checkin_count: number;
  created_at: string;
  updated_at: string;
}

export interface GoalCheckin {
  id: number;
  progress: number | null;
  note: string | null;
  created_by: number | null;
  author_name: string | null;
  created_at: string;
}

export interface GoalDetail extends Goal {
  checkins: GoalCheckin[];
}

// ---------- Surveys ----------
export type SurveyStatus = "draft" | "open" | "closed";
export type SurveyQuestionType =
  | "short_text"
  | "long_text"
  | "single_choice"
  | "multi_choice"
  | "dropdown"
  | "rating"
  | "yes_no"
  | "date";

export interface SurveyQuestion {
  id: number;
  position: number;
  type: SurveyQuestionType;
  prompt: string;
  required: boolean;
  choices: string[] | null;
  scale_max: number | null;
}

export interface Survey {
  id: number;
  title: string;
  description: string | null;
  status: SurveyStatus;
  anonymous: boolean;
  created_by: number | null;
  closes_at: string | null;
  created_at: string;
  updated_at: string;
  question_count: number;
  assigned_count: number;
  response_count: number;
}

export interface SurveyDetail extends Survey {
  questions: SurveyQuestion[];
}

export interface AssignedSurvey {
  id: number;
  title: string;
  description: string | null;
  status: SurveyStatus;
  anonymous: boolean;
  completed: boolean;
  closes_at: string | null;
}

export interface SurveyFill {
  id: number;
  title: string;
  description: string | null;
  anonymous: boolean;
  completed: boolean;
  questions: SurveyQuestion[];
}

export interface SurveyAssignmentStatus {
  employee_id: number;
  name: string;
  completed: boolean;
}

export interface SurveyOptionCount {
  label: string;
  count: number;
}

export interface SurveyQuestionResult {
  question_id: number;
  prompt: string;
  type: SurveyQuestionType;
  total_answers: number;
  counts: SurveyOptionCount[] | null;
  average: number | null;
  texts: string[] | null;
}

export interface SurveyResults {
  survey_id: number;
  title: string;
  anonymous: boolean;
  assigned_count: number;
  response_count: number;
  questions: SurveyQuestionResult[];
}

// ---------- Documents ----------
export type DocumentKind =
  | "degree"
  | "id_document"
  | "offer_letter"
  | "employment_letter"
  | "promotion_letter"
  | "other";

export interface EmployeeDocument {
  id: number;
  employee_id: number;
  kind: DocumentKind;
  title: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

// ---------- Analytics ----------
export interface TrendCycle {
  cycle_id: number;
  label: string;
  year: number;
  type: CycleType;
  avg_score: number | null;
  completion_rate: number;
  reviewed_count: number;
}

export interface AnalyticsSeries {
  name: string;
  max_points: number | null;
  values: (number | null)[];
}

export interface AnalyticsSummary {
  cycles: TrendCycle[];
  category_series: AnalyticsSeries[];
  team_series: AnalyticsSeries[];
  latest_cycle_id: number | null;
}

export interface KpiInsight {
  name: string;
  category: string;
  max_points: number;
  earned_avg: number;
  pct: number;
  met: number;
  partial: number;
  not_met: number;
}

export interface CalibrationCategory {
  category: string;
  self_pct: number;
  reviewer_pct: number;
}

export interface CycleAnalytics {
  cycle_id: number;
  label: string;
  kpis: KpiInsight[];
  calibration: CalibrationCategory[];
  calibration_overall_self: number | null;
  calibration_overall_reviewer: number | null;
  calibration_pairs: number;
}

export interface EmployeeTrajectory {
  employee_id: number;
  name: string;
  team: string | null;
  values: (number | null)[];
  latest: number | null;
  delta: number | null;
}

export interface AnalyticsEmployees {
  cycles: string[];
  employees: EmployeeTrajectory[];
}

export interface InviteResult {
  user_id: number;
  email: string;
  role: Role;
  invite_link: string | null;
}

export interface AuditEntry {
  id: number;
  actor_user_id: number | null;
  actor_email: string | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  detail: Record<string, unknown> | null;
  created_at: string;
}
