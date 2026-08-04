"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

role_enum = postgresql.ENUM(
    "hr_admin", "manager", "employee", name="role_enum", create_type=False
)
cycle_type_enum = postgresql.ENUM(
    "mid_year", "end_year", name="cycle_type_enum", create_type=False
)
cycle_status_enum = postgresql.ENUM(
    "draft", "open", "closed", name="cycle_status_enum", create_type=False
)
review_status_enum = postgresql.ENUM(
    "not_started", "in_progress", "submitted", name="review_status_enum", create_type=False
)

_TIMESTAMP = sa.DateTime(timezone=True)
_TABLES_WITH_UPDATED_AT = [
    "users",
    "invitations",
    "password_resets",
    "refresh_tokens",
    "employees",
    "kpis",
    "review_cycles",
    "review_assignments",
    "review_scores",
]


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", _TIMESTAMP, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", _TIMESTAMP, server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (role_enum, cycle_type_enum, cycle_status_enum, review_status_enum):
        enum.create(bind, checkfirst=True)

    # ---- updated_at trigger function ----
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # ---- users ----
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("role", role_enum, nullable=False, server_default="employee"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])

    # ---- invitations ----
    op.create_table(
        "invitations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column(
            "invited_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("expires_at", _TIMESTAMP, nullable=False),
        sa.Column("accepted_at", _TIMESTAMP, nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_invitations_token_hash", "invitations", ["token_hash"])
    op.create_index("ix_invitations_token_hash", "invitations", ["token_hash"])
    op.create_index("ix_invitations_invited_by", "invitations", ["invited_by"])
    op.create_index("ix_invitations_user_id", "invitations", ["user_id"])

    # ---- password_resets ----
    op.create_table(
        "password_resets",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", _TIMESTAMP, nullable=False),
        sa.Column("consumed_at", _TIMESTAMP, nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint(
        "uq_password_resets_token_hash", "password_resets", ["token_hash"]
    )
    op.create_index("ix_password_resets_token_hash", "password_resets", ["token_hash"])
    op.create_index("ix_password_resets_user_id", "password_resets", ["user_id"])

    # ---- refresh_tokens ----
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("expires_at", _TIMESTAMP, nullable=False),
        sa.Column("revoked_at", _TIMESTAMP, nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint(
        "uq_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"]
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # ---- employees ----
    op.create_table(
        "employees",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("job_title", sa.Text(), nullable=True),
        sa.Column("team", sa.Text(), nullable=True),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column(
            "manager_id",
            sa.BigInteger(),
            sa.ForeignKey("employees.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_employees_user_id", "employees", ["user_id"])
    op.create_index("ix_employees_manager_id", "employees", ["manager_id"])
    op.create_index("ix_employees_team", "employees", ["team"])

    # ---- kpis ----
    op.create_table(
        "kpis",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "weight", sa.Numeric(5, 2), nullable=False, server_default=sa.text("1.00")
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_timestamps(),
    )

    # ---- review_cycles ----
    op.create_table(
        "review_cycles",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("type", cycle_type_enum, nullable=False),
        sa.Column("status", cycle_status_enum, nullable=False, server_default="draft"),
        sa.Column("opens_at", _TIMESTAMP, nullable=False),
        sa.Column("closes_at", _TIMESTAMP, nullable=False),
        sa.Column(
            "created_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_timestamps(),
    )
    op.create_unique_constraint("uq_cycle_year_type", "review_cycles", ["year", "type"])

    # ---- review_assignments ----
    op.create_table(
        "review_assignments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "cycle_id",
            sa.BigInteger(),
            sa.ForeignKey("review_cycles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_employee_id",
            sa.BigInteger(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_employee_id",
            sa.BigInteger(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", review_status_enum, nullable=False, server_default="not_started"
        ),
        sa.Column("submitted_at", _TIMESTAMP, nullable=True),
        sa.Column("summary_comment", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint(
        "uq_assignment_cycle_subject",
        "review_assignments",
        ["cycle_id", "subject_employee_id"],
    )
    op.create_index(
        "ix_review_assignments_cycle_status",
        "review_assignments",
        ["cycle_id", "status"],
    )
    op.create_index(
        "ix_review_assignments_subject", "review_assignments", ["subject_employee_id"]
    )
    op.create_index(
        "ix_review_assignments_reviewer", "review_assignments", ["reviewer_employee_id"]
    )

    # ---- review_scores ----
    op.create_table(
        "review_scores",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.BigInteger(),
            sa.ForeignKey("review_assignments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kpi_id",
            sa.BigInteger(),
            sa.ForeignKey("kpis.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(4, 2), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        *_timestamps(),
    )
    op.create_unique_constraint(
        "uq_score_assignment_kpi", "review_scores", ["assignment_id", "kpi_id"]
    )
    op.create_index("ix_review_scores_assignment", "review_scores", ["assignment_id"])
    op.create_index("ix_review_scores_kpi", "review_scores", ["kpi_id"])

    # ---- per-table updated_at triggers ----
    for table in _TABLES_WITH_UPDATED_AT:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_set_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    for table in _TABLES_WITH_UPDATED_AT:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_set_updated_at ON {table};")

    op.drop_table("review_scores")
    op.drop_table("review_assignments")
    op.drop_table("review_cycles")
    op.drop_table("kpis")
    op.drop_table("employees")
    op.drop_table("refresh_tokens")
    op.drop_table("password_resets")
    op.drop_table("invitations")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    bind = op.get_bind()
    # Explicit enum drops — without this, downgrade+re-upgrade fails on "type already exists".
    for enum in (review_status_enum, cycle_status_enum, cycle_type_enum, role_enum):
        enum.drop(bind, checkfirst=True)
