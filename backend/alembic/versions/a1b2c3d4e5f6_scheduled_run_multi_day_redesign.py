"""scheduled_run multi-day redesign (E14-S6): days_of_week array, mode, notify_enabled;
analysis_runs.notify_on_complete

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-07-25 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scheduled_runs", sa.Column("days_of_week", sa.ARRAY(sa.Integer()), nullable=True)
    )
    op.add_column(
        "scheduled_runs",
        sa.Column(
            "mode", sa.String(length=20), nullable=False, server_default="recurring"
        ),
    )
    op.add_column(
        "scheduled_runs",
        sa.Column(
            "notify_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    # Backfill: every pre-existing row was one weekday per row under the old model —
    # each becomes its own single-day recurring schedule (behaviorally identical: fires
    # every week on that day, same as before).
    op.execute("UPDATE scheduled_runs SET days_of_week = ARRAY[day_of_week]")
    op.alter_column("scheduled_runs", "days_of_week", nullable=False)
    op.alter_column("scheduled_runs", "mode", server_default=None)
    op.alter_column("scheduled_runs", "notify_enabled", server_default=None)

    op.drop_constraint("day_of_week_range", "scheduled_runs", type_="check")
    op.drop_column("scheduled_runs", "day_of_week")
    op.create_check_constraint(
        "days_of_week_range",
        "scheduled_runs",
        "days_of_week <@ ARRAY[0,1,2,3,4,5,6] AND cardinality(days_of_week) >= 1",
    )

    op.add_column(
        "analysis_runs",
        sa.Column(
            "notify_on_complete", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.alter_column("analysis_runs", "notify_on_complete", server_default=None)


def downgrade() -> None:
    op.drop_column("analysis_runs", "notify_on_complete")

    op.drop_constraint("days_of_week_range", "scheduled_runs", type_="check")
    op.add_column(
        "scheduled_runs", sa.Column("day_of_week", sa.Integer(), nullable=True)
    )
    op.execute("UPDATE scheduled_runs SET day_of_week = days_of_week[1]")
    op.alter_column("scheduled_runs", "day_of_week", nullable=False)
    op.create_check_constraint(
        "day_of_week_range", "scheduled_runs", "day_of_week BETWEEN 0 AND 6"
    )
    op.drop_column("scheduled_runs", "notify_enabled")
    op.drop_column("scheduled_runs", "mode")
    op.drop_column("scheduled_runs", "days_of_week")
