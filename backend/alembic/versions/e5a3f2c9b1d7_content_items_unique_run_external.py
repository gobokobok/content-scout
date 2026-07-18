"""content_items unique (run_id, external_id)

Revision ID: e5a3f2c9b1d7
Revises: c7e2f8a1b6d4
Create Date: 2026-07-18 10:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = "e5a3f2c9b1d7"
down_revision: str | None = "c7e2f8a1b6d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_content_items_run_id_external_id",
        "content_items",
        ["run_id", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_content_items_run_id_external_id", "content_items", type_="unique")
