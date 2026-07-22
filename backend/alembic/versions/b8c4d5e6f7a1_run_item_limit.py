"""add item_limit to analysis_runs, make duration_days optional

Revision ID: b8c4d5e6f7a1
Revises: e4f5a6b7c8d9
Create Date: 2026-07-22 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c4d5e6f7a1"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("analysis_runs", sa.Column("item_limit", sa.Integer(), nullable=True))
    op.alter_column("analysis_runs", "duration_days", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("duration_days_range", "analysis_runs", type_="check")
    op.create_check_constraint(
        "duration_or_item_limit_range",
        "analysis_runs",
        "(duration_days IS NOT NULL AND item_limit IS NULL AND duration_days BETWEEN 1 AND 7)"
        " OR (item_limit IS NOT NULL AND duration_days IS NULL AND item_limit BETWEEN 1 AND 50)",
    )


def downgrade() -> None:
    op.drop_constraint("duration_or_item_limit_range", "analysis_runs", type_="check")
    op.execute("UPDATE analysis_runs SET duration_days = 7 WHERE duration_days IS NULL")
    op.alter_column("analysis_runs", "duration_days", existing_type=sa.Integer(), nullable=False)
    op.create_check_constraint(
        "duration_days_range", "analysis_runs", "duration_days BETWEEN 1 AND 7"
    )
    op.drop_column("analysis_runs", "item_limit")
