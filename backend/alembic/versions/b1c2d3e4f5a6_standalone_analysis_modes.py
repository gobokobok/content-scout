"""standalone Analysis modes on analysis_runs/scheduled_runs (E21-S2, D50)

Analysis (deep_analysis run_type) is decoupled from Review (D40): it gets its own
account-or-post scope instead of chaining off a finished Review run. Adds
analysis_mode ('account'|'post'), target_post_url, and comments_limit to both
analysis_runs and scheduled_runs, relaxes the duration/item_limit XOR constraint to
allow both NULL when analysis_mode='post' (a single post has no day-window or
publication-count scope), and drops analysis_runs.deep_analysis_skip_reason -- the
auto-chain it recorded skip reasons for no longer exists.

Revision ID: b1c2d3e4f5a6
Revises: a2b3c4d5e6f7
Create Date: 2026-08-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCOPE_CHECK_SQL = (
    "(analysis_mode IS NOT DISTINCT FROM 'post' AND duration_days IS NULL AND item_limit IS NULL)"
    " OR (analysis_mode IS DISTINCT FROM 'post' AND ("
    "(duration_days IS NOT NULL AND item_limit IS NULL AND duration_days BETWEEN 1 AND 7)"
    " OR (item_limit IS NOT NULL AND duration_days IS NULL AND item_limit BETWEEN 1 AND 50)"
    "))"
)
_OLD_SCOPE_CHECK_SQL = (
    "(duration_days IS NOT NULL AND item_limit IS NULL AND duration_days BETWEEN 1 AND 7)"
    " OR (item_limit IS NOT NULL AND duration_days IS NULL AND item_limit BETWEEN 1 AND 50)"
)
_COMMENTS_LIMIT_CHECK_SQL = "comments_limit IS NULL OR comments_limit BETWEEN 1 AND 50"


def upgrade() -> None:
    op.add_column(
        "analysis_runs", sa.Column("analysis_mode", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "analysis_runs", sa.Column("target_post_url", sa.String(length=500), nullable=True)
    )
    op.add_column("analysis_runs", sa.Column("comments_limit", sa.Integer(), nullable=True))
    op.drop_constraint("duration_or_item_limit_range", "analysis_runs", type_="check")
    op.create_check_constraint(
        "duration_or_item_limit_range", "analysis_runs", _SCOPE_CHECK_SQL
    )
    op.create_check_constraint(
        op.f("ck_analysis_runs_comments_limit_range"), "analysis_runs", _COMMENTS_LIMIT_CHECK_SQL
    )
    op.drop_column("analysis_runs", "deep_analysis_skip_reason")

    op.add_column(
        "scheduled_runs", sa.Column("analysis_mode", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "scheduled_runs", sa.Column("target_post_url", sa.String(length=500), nullable=True)
    )
    op.add_column("scheduled_runs", sa.Column("comments_limit", sa.Integer(), nullable=True))
    op.drop_constraint(
        op.f("ck_scheduled_runs_duration_or_item_limit_range"), "scheduled_runs", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_scheduled_runs_duration_or_item_limit_range"), "scheduled_runs", _SCOPE_CHECK_SQL
    )
    op.create_check_constraint(
        op.f("ck_scheduled_runs_comments_limit_range"), "scheduled_runs", _COMMENTS_LIMIT_CHECK_SQL
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_scheduled_runs_comments_limit_range"), "scheduled_runs", type_="check"
    )
    op.drop_constraint(
        op.f("ck_scheduled_runs_duration_or_item_limit_range"), "scheduled_runs", type_="check"
    )
    op.execute(
        "UPDATE scheduled_runs SET duration_days = 7 "
        "WHERE analysis_mode = 'post' AND duration_days IS NULL AND item_limit IS NULL"
    )
    op.create_check_constraint(
        op.f("ck_scheduled_runs_duration_or_item_limit_range"),
        "scheduled_runs",
        _OLD_SCOPE_CHECK_SQL,
    )
    op.drop_column("scheduled_runs", "comments_limit")
    op.drop_column("scheduled_runs", "target_post_url")
    op.drop_column("scheduled_runs", "analysis_mode")

    op.add_column(
        "analysis_runs", sa.Column("deep_analysis_skip_reason", sa.String(length=30), nullable=True)
    )
    op.drop_constraint(
        op.f("ck_analysis_runs_comments_limit_range"), "analysis_runs", type_="check"
    )
    op.drop_constraint("duration_or_item_limit_range", "analysis_runs", type_="check")
    op.execute(
        "UPDATE analysis_runs SET duration_days = 7 "
        "WHERE analysis_mode = 'post' AND duration_days IS NULL AND item_limit IS NULL"
    )
    op.create_check_constraint(
        "duration_or_item_limit_range", "analysis_runs", _OLD_SCOPE_CHECK_SQL
    )
    op.drop_column("analysis_runs", "comments_limit")
    op.drop_column("analysis_runs", "target_post_url")
    op.drop_column("analysis_runs", "analysis_mode")
