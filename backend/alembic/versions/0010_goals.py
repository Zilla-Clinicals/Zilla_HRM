"""goals + goal check-ins

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-15

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "employee_id",
            sa.BigInteger(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False, server_default="performance"),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_started"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_goals_employee_id", "goals", ["employee_id"])
    op.create_index("ix_goals_year", "goals", ["year"])
    op.execute(
        """
        CREATE TRIGGER trg_goals_set_updated_at
        BEFORE UPDATE ON goals
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    op.create_table(
        "goal_checkins",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "goal_id",
            sa.BigInteger(),
            sa.ForeignKey("goals.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("progress", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_goal_checkins_goal_id", "goal_checkins", ["goal_id"])


def downgrade() -> None:
    op.drop_table("goal_checkins")
    op.execute("DROP TRIGGER IF EXISTS trg_goals_set_updated_at ON goals;")
    op.drop_table("goals")
