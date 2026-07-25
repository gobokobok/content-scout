"""scheduled_runs: last_skip_reason / last_skip_at (E14-S6 follow-up)

Revision ID: b3c4d5e6f7a8
Revises: 5517fb8a1b2c
Create Date: 2026-07-25 12:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scheduled_runs", sa.Column("last_skip_reason", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "scheduled_runs",
        sa.Column("last_skip_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheduled_runs", "last_skip_at")
    op.drop_column("scheduled_runs", "last_skip_reason")
