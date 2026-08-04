"""Wipe all demo/operational data for a fresh production start.

KEEPS:
  - the KPI scoring framework (kpi_categories, kpis) — this is company config
  - ONE admin login (default admin@zillaclinicals.com), plus its Employee record

REMOVES everything else: all other users/employees, invitations, tokens,
review cycles/assignments/scores, goals, surveys, uploaded documents/photos,
recovery codes and audit logs. Also clears the kept admin's 2FA so the new
owner starts from a clean second-factor state (the password is untouched).

This is DESTRUCTIVE and irreversible. Run against the target database only.

Usage:
    uv run python -m scripts.reset_clean_slate --email admin@zillaclinicals.com --yes
"""
import argparse
import asyncio

from sqlalchemy import delete, func, select, text

from app.db import async_session_factory
from app.models._base import Role
from app.models.employees import Employee
from app.models.users import User

# Activity/demo tables cleared wholesale (identities reset). Order doesn't matter
# with CASCADE, but we exclude kpis / kpi_categories (kept) and users / employees
# (handled selectively below so the admin survives).
WIPE_TABLES = [
    "survey_answers",
    "survey_responses",
    "survey_assignments",
    "survey_questions",
    "surveys",
    "document_blobs",
    "employee_documents",
    "goal_checkins",
    "goals",
    "review_scores",
    "review_assignments",
    "review_cycles",
    "audit_logs",
    "recovery_codes",
    "refresh_tokens",
    "password_resets",
    "invitations",
]


async def main(email: str) -> None:
    email = email.strip().lower()
    async with async_session_factory() as db:
        admin = await db.scalar(select(User).where(User.email == email))
        if not admin:
            raise SystemExit(f"No user found with email {email!r} — aborting, nothing changed.")
        if admin.role != Role.admin:
            raise SystemExit(
                f"User {email!r} is role {admin.role.value!r}, not admin — aborting."
            )
        admin_emp = await db.scalar(select(Employee).where(Employee.user_id == admin.id))

        # 1. Clear all activity/demo tables.
        await db.execute(
            text(f"TRUNCATE {', '.join(WIPE_TABLES)} RESTART IDENTITY CASCADE")
        )

        # 2. Drop every employee except the admin's (their child rows are already gone).
        if admin_emp is not None:
            await db.execute(delete(Employee).where(Employee.id != admin_emp.id))
        else:
            await db.execute(delete(Employee))

        # 3. Drop every user except the admin.
        await db.execute(delete(User).where(User.id != admin.id))

        # 4. Reset the kept admin's second factor (password left as-is).
        admin.totp_enabled = False
        admin.totp_secret = None
        admin.totp_last_used_step = None

        await db.commit()

        remaining_users = await db.scalar(select(func.count()).select_from(User))
        remaining_emps = await db.scalar(select(func.count()).select_from(Employee))

    print("Clean slate complete.")
    print(f"  Kept admin login : {email}")
    print(f"  Users remaining  : {remaining_users}")
    print(f"  Employees remain : {remaining_emps}")
    print("  KPI framework    : preserved")
    print("  Admin 2FA        : reset (re-enrol in Settings if desired)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wipe demo data, keep one admin + KPI framework.")
    parser.add_argument("--email", default="admin@zillaclinicals.com", help="admin login to keep")
    parser.add_argument("--yes", action="store_true", help="confirm the destructive wipe")
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("Refusing to run without --yes (this permanently deletes data).")
    asyncio.run(main(args.email))
