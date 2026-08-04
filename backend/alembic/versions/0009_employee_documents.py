"""employee documents + blob storage

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-15

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employee_documents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "employee_id",
            sa.BigInteger(),
            sa.ForeignKey("employees.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_backend", sa.Text(), nullable=False, server_default="db"),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column(
            "uploaded_by",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_employee_documents_storage_key", "employee_documents", ["storage_key"]
    )
    op.create_index(
        "ix_employee_documents_employee_id", "employee_documents", ["employee_id"]
    )

    op.create_table(
        "document_blobs",
        sa.Column("storage_key", sa.Text(), primary_key=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("document_blobs")
    op.drop_table("employee_documents")
