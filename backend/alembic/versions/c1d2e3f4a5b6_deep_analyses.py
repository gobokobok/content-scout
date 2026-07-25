"""deep_analyses table

Revision ID: c1d2e3f4a5b6
Revises: b3c4d5e6f7a8
Create Date: 2026-07-25 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deep_analyses",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "extracting",
                "synthesizing",
                "done",
                "failed",
                name="deepanalysisstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("tokens_charged", sa.Integer(), nullable=False),
        sa.Column("report_stats", postgresql.JSONB(), nullable=True),
        sa.Column("report_recommendations", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["analysis_runs.id"], name=op.f("fk_deep_analyses_run_id_analysis_runs")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_deep_analyses_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"], ["users.id"], name=op.f("fk_deep_analyses_requested_by_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deep_analyses")),
    )
    op.create_index(
        op.f("ix_deep_analyses_run_id"), "deep_analyses", ["run_id"], unique=False
    )
    op.create_index(
        op.f("ix_deep_analyses_project_id"), "deep_analyses", ["project_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_deep_analyses_project_id"), table_name="deep_analyses")
    op.drop_index(op.f("ix_deep_analyses_run_id"), table_name="deep_analyses")
    op.drop_table("deep_analyses")
