"""raise comments_limit ceiling from 50 to 100 (E21-S2 follow-up)

First DEV smoke test of publication-mode Analysis showed the 50-comment ceiling
was already tight for accounts with heavily-commented posts; widens the
comments_limit range on both analysis_runs and scheduled_runs to 1-100.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-04 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_CHECK_SQL = "comments_limit IS NULL OR comments_limit BETWEEN 1 AND 100"
_OLD_CHECK_SQL = "comments_limit IS NULL OR comments_limit BETWEEN 1 AND 50"


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_analysis_runs_comments_limit_range"), "analysis_runs", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_analysis_runs_comments_limit_range"), "analysis_runs", _NEW_CHECK_SQL
    )
    op.drop_constraint(
        op.f("ck_scheduled_runs_comments_limit_range"), "scheduled_runs", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_scheduled_runs_comments_limit_range"), "scheduled_runs", _NEW_CHECK_SQL
    )


def downgrade() -> None:
    op.execute("UPDATE analysis_runs SET comments_limit = 50 WHERE comments_limit > 50")
    op.execute("UPDATE scheduled_runs SET comments_limit = 50 WHERE comments_limit > 50")
    op.drop_constraint(
        op.f("ck_scheduled_runs_comments_limit_range"), "scheduled_runs", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_scheduled_runs_comments_limit_range"), "scheduled_runs", _OLD_CHECK_SQL
    )
    op.drop_constraint(
        op.f("ck_analysis_runs_comments_limit_range"), "analysis_runs", type_="check"
    )
    op.create_check_constraint(
        op.f("ck_analysis_runs_comments_limit_range"), "analysis_runs", _OLD_CHECK_SQL
    )
