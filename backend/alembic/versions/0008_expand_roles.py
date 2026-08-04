"""expand roles: admin / executive / hr / manager / employee

Old 'hr_admin' becomes 'admin' (the developer superuser). New 'executive' and
'hr' roles are added. Done by swapping the enum type so it's transaction-safe.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-14

"""
from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE role_enum_new AS ENUM ('admin','executive','hr','manager','employee')")
    for table in ("users", "invitations"):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN role DROP DEFAULT")
        op.execute(
            f"""
            ALTER TABLE {table} ALTER COLUMN role TYPE role_enum_new
            USING (CASE role::text WHEN 'hr_admin' THEN 'admin' ELSE role::text END::role_enum_new)
            """
        )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'employee'")
    op.execute("DROP TYPE role_enum")
    op.execute("ALTER TYPE role_enum_new RENAME TO role_enum")


def downgrade() -> None:
    # Collapse the new roles back to the original three.
    op.execute("CREATE TYPE role_enum_old AS ENUM ('hr_admin','manager','employee')")
    for table in ("users", "invitations"):
        op.execute(f"ALTER TABLE {table} ALTER COLUMN role DROP DEFAULT")
        op.execute(
            f"""
            ALTER TABLE {table} ALTER COLUMN role TYPE role_enum_old
            USING (
                CASE role::text
                    WHEN 'admin' THEN 'hr_admin'
                    WHEN 'executive' THEN 'hr_admin'
                    WHEN 'hr' THEN 'hr_admin'
                    ELSE role::text
                END::role_enum_old
            )
            """
        )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'employee'")
    op.execute("DROP TYPE role_enum")
    op.execute("ALTER TYPE role_enum_old RENAME TO role_enum")
