"""add followers_count to accounts

Revision ID: d3e4f5a6b7c8
Revises: c2275f27bb18
Create Date: 2026-07-22 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2275f27bb18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("followers_count", sa.Integer(), nullable=True))
    op.add_column(
        "accounts", sa.Column("followers_updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("accounts", "followers_updated_at")
    op.drop_column("accounts", "followers_count")
