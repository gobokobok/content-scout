"""add run_type to analysis_runs and scheduled_runs

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-26 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("run_type", sa.String(32), nullable=False, server_default="stat_collection"),
    )
    op.add_column(
        "scheduled_runs",
        sa.Column("run_type", sa.String(32), nullable=False, server_default="stat_collection"),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "run_type")
    op.drop_column("scheduled_runs", "run_type")
