"""surveys: forms, questions, assignments, responses, answers

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-15

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "surveys",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closes_at", _TS, nullable=True),
        sa.Column("created_at", _TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", _TS, server_default=sa.text("now()"), nullable=False),
    )
    op.execute(
        "CREATE TRIGGER trg_surveys_set_updated_at BEFORE UPDATE ON surveys "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
    )

    op.create_table(
        "survey_questions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("survey_id", sa.BigInteger(), sa.ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("options", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_survey_questions_survey_id", "survey_questions", ["survey_id"])

    op.create_table(
        "survey_assignments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("survey_id", sa.BigInteger(), sa.ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.BigInteger(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", _TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_survey_assignment", "survey_assignments", ["survey_id", "employee_id"])
    op.create_index("ix_survey_assignments_survey_id", "survey_assignments", ["survey_id"])
    op.create_index("ix_survey_assignments_employee_id", "survey_assignments", ["employee_id"])

    op.create_table(
        "survey_responses",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("survey_id", sa.BigInteger(), sa.ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False),
        sa.Column("respondent_employee_id", sa.BigInteger(), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("submitted_at", _TS, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_survey_responses_survey_id", "survey_responses", ["survey_id"])

    op.create_table(
        "survey_answers",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("response_id", sa.BigInteger(), sa.ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question_id", sa.BigInteger(), sa.ForeignKey("survey_questions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_survey_answers_response_id", "survey_answers", ["response_id"])


def downgrade() -> None:
    op.drop_table("survey_answers")
    op.drop_table("survey_responses")
    op.drop_table("survey_assignments")
    op.drop_table("survey_questions")
    op.execute("DROP TRIGGER IF EXISTS trg_surveys_set_updated_at ON surveys;")
    op.drop_table("surveys")
