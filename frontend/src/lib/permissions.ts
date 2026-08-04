import type { Role } from "../shared/types";

// Mirrors backend app/auth/permissions.py — keep the two in sync.
export type Cap =
  | "view_org"
  | "manage_people"
  | "manage_roles"
  | "manage_cycles"
  | "manage_kpis"
  | "view_analytics"
  | "view_audit"
  | "override_review"
  | "create_surveys"
  | "manage_surveys";

const ALL: Cap[] = [
  "view_org",
  "manage_people",
  "manage_roles",
  "manage_cycles",
  "manage_kpis",
  "view_analytics",
  "view_audit",
  "override_review",
  "create_surveys",
  "manage_surveys",
];

const ROLE_CAPS: Record<Role, Cap[]> = {
  admin: ALL,
  executive: ALL,
  hr: [
    "view_org",
    "manage_people",
    "manage_cycles",
    "manage_kpis",
    "view_analytics",
    "view_audit",
    "override_review",
    "create_surveys",
    "manage_surveys",
  ],
  manager: ["create_surveys"],
  employee: [],
};

export function roleCan(role: Role | null | undefined, cap: Cap): boolean {
  return role ? (ROLE_CAPS[role]?.includes(cap) ?? false) : false;
}

export const ROLE_LABELS: Record<Role, string> = {
  admin: "Admin",
  executive: "Executive",
  hr: "HR",
  manager: "Team Lead",
  employee: "Employee",
};
