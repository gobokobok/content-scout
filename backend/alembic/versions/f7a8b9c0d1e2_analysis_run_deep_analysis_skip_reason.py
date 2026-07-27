"""analysis_runs: deep_analysis_skip_reason

A deep_analysis-type run auto-chains a DeepAnalysis once its base scrape finishes (nav
overhaul). When that chain is skipped -- insufficient token balance, or an unexpected error --
no DeepAnalysis row is ever created, so the run silently looks identical to a plain
stat_collection run with nothing to explain why. This mirrors scheduled_runs.last_skip_reason
(b3c4d5e6f7a8) for the same reason: make a silent skip visible instead of invisible.

Revision ID: f7a8b9c0d1e2
Revises: e3f4a5b6c7d8
Create Date: 2026-07-27 17:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("deep_analysis_skip_reason", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "deep_analysis_skip_reason")
