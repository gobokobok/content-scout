"""add display_name to users

Revision ID: c2275f27bb18
Revises: a1b2c3d4e5f7
Create Date: 2026-07-21 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2275f27bb18"
down_revision: str | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=50), nullable=True))
    op.execute(
        "UPDATE users SET display_name = 'Пользователь' || floor(random() * 9000 + 1000)::int "
        "WHERE display_name IS NULL"
    )
    op.alter_column("users", "display_name", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "display_name")
