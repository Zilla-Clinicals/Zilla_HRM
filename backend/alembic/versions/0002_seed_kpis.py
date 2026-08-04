"""seed starter KPI catalog

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 12 KPIs across 6 categories — a sensible starter catalog HR can edit.
SEED_KPIS = [
    ("Task completion rate", "Productivity", "Proportion of assigned work delivered on time", "1.50"),
    ("Quality of output", "Productivity", "Accuracy and thoroughness of delivered work", "1.50"),
    ("Communication", "Behavior", "Clarity and responsiveness with team and stakeholders", "1.00"),
    ("Collaboration", "Behavior", "Works effectively across the team", "1.00"),
    ("Technical skills", "Competency", "Depth and currency of role-specific expertise", "1.25"),
    ("Problem solving", "Competency", "Diagnoses and resolves issues independently", "1.25"),
    ("Reliability", "Dependability", "Consistency and follow-through on commitments", "1.00"),
    ("Attendance & punctuality", "Dependability", "Presence and timeliness", "0.75"),
    ("Initiative", "Leadership", "Proactively identifies and drives improvements", "1.00"),
    ("Mentoring", "Leadership", "Supports the growth of peers and reports", "0.75"),
    ("Adaptability", "Growth", "Adjusts well to change and new priorities", "1.00"),
    ("Learning & development", "Growth", "Actively builds new skills", "0.75"),
]


def upgrade() -> None:
    kpis = sa.table(
        "kpis",
        sa.column("name", sa.Text),
        sa.column("category", sa.Text),
        sa.column("description", sa.Text),
        sa.column("weight", sa.Numeric),
    )
    op.bulk_insert(
        kpis,
        [
            {"name": n, "category": c, "description": d, "weight": w}
            for (n, c, d, w) in SEED_KPIS
        ],
    )


def downgrade() -> None:
    names = tuple(n for (n, _c, _d, _w) in SEED_KPIS)
    op.execute(
        sa.text("DELETE FROM kpis WHERE name IN :names").bindparams(
            sa.bindparam("names", value=names, expanding=True)
        )
    )
