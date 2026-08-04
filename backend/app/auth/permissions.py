"""Capability-based permissions.

Roles map to a set of capabilities. Routes check capabilities (not raw roles),
so adding/adjusting a role is a one-line change here.

Reporting relationships (who reviews whom) are separate — those come from
employees.manager_id, independent of these access capabilities.
"""
from app.models._base import Role


class Cap:
    VIEW_ORG = "view_org"  # see all employees, cycles, dashboards
    MANAGE_PEOPLE = "manage_people"  # invite / edit / deactivate employees
    MANAGE_ROLES = "manage_roles"  # change a user's access role
    MANAGE_CYCLES = "manage_cycles"  # create / assign / open / close cycles
    MANAGE_KPIS = "manage_kpis"  # edit the KPI catalog + category weights
    VIEW_ANALYTICS = "view_analytics"
    VIEW_AUDIT = "view_audit"
    OVERRIDE_REVIEW = "override_review"  # bypass the self-first submit gate
    CREATE_SURVEYS = "create_surveys"  # create surveys (managers: for their team only)
    MANAGE_SURVEYS = "manage_surveys"  # assign to anyone/everyone + see all surveys


_ALL = {
    Cap.VIEW_ORG,
    Cap.MANAGE_PEOPLE,
    Cap.MANAGE_ROLES,
    Cap.MANAGE_CYCLES,
    Cap.MANAGE_KPIS,
    Cap.VIEW_ANALYTICS,
    Cap.VIEW_AUDIT,
    Cap.OVERRIDE_REVIEW,
    Cap.CREATE_SURVEYS,
    Cap.MANAGE_SURVEYS,
}

ROLE_CAPS: dict[Role, set[str]] = {
    Role.admin: set(_ALL),
    Role.executive: set(_ALL),
    # HR runs the people + review process, but can't hand out access roles.
    Role.hr: {
        Cap.VIEW_ORG,
        Cap.MANAGE_PEOPLE,
        Cap.MANAGE_CYCLES,
        Cap.MANAGE_KPIS,
        Cap.VIEW_ANALYTICS,
        Cap.VIEW_AUDIT,
        Cap.OVERRIDE_REVIEW,
        Cap.CREATE_SURVEYS,
        Cap.MANAGE_SURVEYS,
    },
    # Team leads: no admin capabilities, but they CAN run surveys for their own
    # team (assignment is scoped to their reports in the surveys router). Their
    # other power comes from being a reviewer (manager_id) + team visibility.
    Role.manager: {Cap.CREATE_SURVEYS},
    Role.employee: set(),
}


def can(role: Role, capability: str) -> bool:
    return capability in ROLE_CAPS.get(role, set())
