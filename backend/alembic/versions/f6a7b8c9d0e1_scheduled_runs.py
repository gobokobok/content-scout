"""scheduled_runs table

Revision ID: f6a7b8c9d0e1
Revises: a9b8c7d6e5f4
Create Date: 2026-07-22 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "a9b8c7d6e5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_runs",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("account_ids", sa.ARRAY(sa.Uuid()), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("item_limit", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("time_of_day", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_run_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(duration_days IS NOT NULL AND item_limit IS NULL"
            " AND duration_days BETWEEN 1 AND 7)"
            " OR (item_limit IS NOT NULL AND duration_days IS NULL"
            " AND item_limit BETWEEN 1 AND 50)",
            name=op.f("ck_scheduled_runs_duration_or_item_limit_range"),
        ),
        sa.CheckConstraint(
            "day_of_week BETWEEN 0 AND 6", name=op.f("ck_scheduled_runs_day_of_week_range")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_scheduled_runs_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_scheduled_runs_created_by_users")
        ),
        sa.ForeignKeyConstraint(
            ["last_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_scheduled_runs_last_run_id_analysis_runs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_runs")),
    )
    op.create_index(
        op.f("ix_scheduled_runs_project_id"), "scheduled_runs", ["project_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_runs_project_id"), table_name="scheduled_runs")
    op.drop_table("scheduled_runs")
