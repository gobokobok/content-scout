"""add display_name and avatar_url to accounts

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-07-22 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4f5a6b7c8d9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("display_name", sa.String(length=200), nullable=True))
    op.add_column("accounts", sa.Column("avatar_url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "avatar_url")
    op.drop_column("accounts", "display_name")
