"""expand employee master record (personal / employment / emergency)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-14

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_COLUMNS = [
    ("date_of_birth", sa.Date()),
    ("gender", sa.Text()),
    ("marital_status", sa.Text()),
    ("nationality", sa.Text()),
    ("personal_email", sa.Text()),
    ("address", sa.Text()),
    ("city", sa.Text()),
    ("country", sa.Text()),
    ("employee_number", sa.Text()),
    ("employment_type", sa.Text()),
    ("work_location", sa.Text()),
    ("emergency_contact_name", sa.Text()),
    ("emergency_contact_phone", sa.Text()),
    ("emergency_contact_relationship", sa.Text()),
]


def upgrade() -> None:
    for name, coltype in _NEW_COLUMNS:
        op.add_column("employees", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_NEW_COLUMNS):
        op.drop_column("employees", name)
