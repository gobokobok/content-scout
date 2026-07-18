"""analysis_runs.account_ids

Revision ID: b2c1a4f9d7e3
Revises: 3a1974cc55cf
Create Date: 2026-07-18 06:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c1a4f9d7e3"
down_revision: str | None = "3a1974cc55cf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("account_ids", sa.ARRAY(sa.Uuid()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("analysis_runs", "account_ids")
