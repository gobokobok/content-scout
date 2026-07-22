"""add run-level AI summary fields to analysis_runs

Revision ID: a9b8c7d6e5f4
Revises: b8c4d5e6f7a1
Create Date: 2026-07-22 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a9b8c7d6e5f4"
down_revision: str | None = "b8c4d5e6f7a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column(
            "summary_status",
            sa.Enum(
                "pending", "done", "failed", name="runsummarystatus", native_enum=False, length=20
            ),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("analysis_runs", sa.Column("summary_text", sa.Text(), nullable=True))
    op.add_column(
        "analysis_runs",
        sa.Column("summary_topics", sa.ARRAY(sa.String(length=100)), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("summary_generated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "summary_generated_at")
    op.drop_column("analysis_runs", "summary_topics")
    op.drop_column("analysis_runs", "summary_text")
    op.drop_column("analysis_runs", "summary_status")
