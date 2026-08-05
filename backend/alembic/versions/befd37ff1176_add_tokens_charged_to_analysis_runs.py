"""add tokens_charged to analysis_runs

Revision ID: befd37ff1176
Revises: e5f6a7b8c9d1
Create Date: 2026-08-05 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "befd37ff1176"
down_revision: str | None = "e5f6a7b8c9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # D52: Review's own real per-run token total, mirroring DeepAnalysis.tokens_charged.
    # Existing rows (progress_summarized items already charged, pre-base-charge) backfill from
    # progress_summarized so historical runs aren't reported as 0 in the ledger.
    op.add_column(
        "analysis_runs",
        sa.Column("tokens_charged", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("UPDATE analysis_runs SET tokens_charged = progress_summarized")


def downgrade() -> None:
    op.drop_column("analysis_runs", "tokens_charged")
