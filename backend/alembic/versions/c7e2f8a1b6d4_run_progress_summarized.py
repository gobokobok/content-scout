"""analysis_runs.progress_summarized

Revision ID: c7e2f8a1b6d4
Revises: b2c1a4f9d7e3
Create Date: 2026-07-18 06:40:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7e2f8a1b6d4"
down_revision: str | None = "b2c1a4f9d7e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("progress_summarized", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("analysis_runs", "progress_summarized", server_default=None)


def downgrade() -> None:
    op.drop_column("analysis_runs", "progress_summarized")
