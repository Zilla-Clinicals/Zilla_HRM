"""auto employee numbers: backfill + UNIQUE constraint

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-14

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.services.employee_ids import make_candidate

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, full_name, employee_number FROM employees")
    ).fetchall()

    taken = {r.employee_number for r in rows if r.employee_number}
    for r in rows:
        if r.employee_number:
            continue
        candidate = make_candidate(r.full_name or "Employee")
        while candidate in taken:
            candidate = make_candidate(r.full_name or "Employee")
        taken.add(candidate)
        bind.execute(
            sa.text("UPDATE employees SET employee_number = :n WHERE id = :id"),
            {"n": candidate, "id": r.id},
        )

    op.create_unique_constraint(
        "uq_employees_employee_number", "employees", ["employee_number"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_employees_employee_number", "employees", type_="unique"
    )
