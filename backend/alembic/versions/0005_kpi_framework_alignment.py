"""align KPI framework to KPI_Scoring_Dashboard workbook

- weighted KPI categories (sum to 100)
- 20-KPI catalog with measurement + target
- scores become Met / Partial / Not Met (points out of 100)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-13

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.seed_data import CATEGORIES, KPIS

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

kpi_status_enum = postgresql.ENUM(
    "met", "partial", "not_met", name="kpi_status_enum", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    kpi_status_enum.create(bind, checkfirst=True)

    # ---- kpi_categories ----
    op.create_table(
        "kpi_categories",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("weight", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_unique_constraint("uq_kpi_categories_name", "kpi_categories", ["name"])
    op.execute(
        """
        CREATE TRIGGER trg_kpi_categories_set_updated_at
        BEFORE UPDATE ON kpi_categories
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )

    categories = sa.table(
        "kpi_categories", sa.column("name", sa.Text), sa.column("weight", sa.Numeric)
    )
    op.bulk_insert(
        categories, [{"name": n, "weight": w} for (n, w) in CATEGORIES]
    )

    # ---- kpis: add measurement/target, drop the per-KPI weight ----
    op.add_column("kpis", sa.Column("measurement", sa.Text(), nullable=True))
    op.add_column("kpis", sa.Column("target", sa.Text(), nullable=True))
    op.drop_column("kpis", "weight")

    # Retire the old generic catalog and insert the workbook's 20 KPIs.
    op.execute("UPDATE kpis SET is_active = false")
    kpis = sa.table(
        "kpis",
        sa.column("name", sa.Text),
        sa.column("category", sa.Text),
        sa.column("description", sa.Text),
        sa.column("measurement", sa.Text),
        sa.column("target", sa.Text),
    )
    op.bulk_insert(
        kpis,
        [
            {"category": c, "name": n, "description": d, "measurement": m, "target": t}
            for (c, n, d, m, t) in KPIS
        ],
    )

    # ---- review_scores: numeric score -> Met/Partial/Not Met status ----
    op.add_column("review_scores", sa.Column("status", kpi_status_enum, nullable=True))
    op.execute(
        """
        UPDATE review_scores SET status = CASE
            WHEN score >= 4 THEN 'met'::kpi_status_enum
            WHEN score >= 2 THEN 'partial'::kpi_status_enum
            ELSE 'not_met'::kpi_status_enum
        END
        """
    )
    op.alter_column("review_scores", "status", nullable=False)
    op.drop_column("review_scores", "score")


def downgrade() -> None:
    op.add_column(
        "review_scores",
        sa.Column("score", sa.Numeric(4, 2), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE review_scores SET score = CASE status
            WHEN 'met' THEN 5 WHEN 'partial' THEN 2.5 ELSE 0 END
        """
    )
    op.alter_column("review_scores", "score", server_default=None)
    op.drop_column("review_scores", "status")

    op.execute(
        sa.text("DELETE FROM kpis WHERE category IN :names").bindparams(
            sa.bindparam("names", value=[c for c, _ in CATEGORIES], expanding=True)
        )
    )
    op.add_column(
        "kpis",
        sa.Column("weight", sa.Numeric(5, 2), nullable=False, server_default="1.00"),
    )
    op.drop_column("kpis", "target")
    op.drop_column("kpis", "measurement")

    op.execute("DROP TRIGGER IF EXISTS trg_kpi_categories_set_updated_at ON kpi_categories;")
    op.drop_table("kpi_categories")

    bind = op.get_bind()
    kpi_status_enum.drop(bind, checkfirst=True)
