"""self-assessment: score author + self review fields

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

score_author_enum = postgresql.ENUM(
    "self", "reviewer", name="score_author_enum", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    score_author_enum.create(bind, checkfirst=True)

    # review_scores: add author, distinguishing self vs reviewer scores.
    op.add_column(
        "review_scores",
        sa.Column(
            "author",
            score_author_enum,
            nullable=False,
            server_default="reviewer",  # existing rows are reviewer scores
        ),
    )
    op.drop_constraint("uq_score_assignment_kpi", "review_scores", type_="unique")
    op.create_unique_constraint(
        "uq_score_assignment_kpi_author",
        "review_scores",
        ["assignment_id", "kpi_id", "author"],
    )

    # review_assignments: independent self-assessment tracking.
    op.add_column(
        "review_assignments",
        sa.Column(
            "self_status",
            postgresql.ENUM(name="review_status_enum", create_type=False),
            nullable=False,
            server_default="not_started",
        ),
    )
    op.add_column(
        "review_assignments",
        sa.Column("self_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "review_assignments", sa.Column("self_comment", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("review_assignments", "self_comment")
    op.drop_column("review_assignments", "self_submitted_at")
    op.drop_column("review_assignments", "self_status")

    op.drop_constraint(
        "uq_score_assignment_kpi_author", "review_scores", type_="unique"
    )
    op.create_unique_constraint(
        "uq_score_assignment_kpi", "review_scores", ["assignment_id", "kpi_id"]
    )
    op.drop_column("review_scores", "author")

    bind = op.get_bind()
    score_author_enum.drop(bind, checkfirst=True)
