"""deep_analysis_items table

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-25 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: str | None = "c1d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deep_analysis_items",
        sa.Column("deep_analysis_id", sa.Uuid(), nullable=False),
        sa.Column("content_item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "done",
                "failed",
                name="deepanalysisitemstatus",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("topic", sa.String(length=200), nullable=True),
        sa.Column("content_format", sa.String(length=100), nullable=True),
        sa.Column("hook_type", sa.String(length=100), nullable=True),
        sa.Column("has_cta", sa.Boolean(), nullable=True),
        sa.Column("sentiment", sa.String(length=20), nullable=True),
        sa.Column("complaints", sa.ARRAY(sa.String(length=300)), nullable=True),
        sa.Column("praises", sa.ARRAY(sa.String(length=300)), nullable=True),
        sa.Column("questions", sa.ARRAY(sa.String(length=300)), nullable=True),
        sa.Column("notable_phrases", sa.ARRAY(sa.String(length=300)), nullable=True),
        sa.Column("comments_analyzed_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["deep_analysis_id"],
            ["deep_analyses.id"],
            name=op.f("fk_deep_analysis_items_deep_analysis_id_deep_analyses"),
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name=op.f("fk_deep_analysis_items_content_item_id_content_items"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deep_analysis_items")),
        sa.UniqueConstraint(
            "deep_analysis_id",
            "content_item_id",
            name=op.f("uq_deep_analysis_items_analysis_item"),
        ),
    )
    op.create_index(
        op.f("ix_deep_analysis_items_deep_analysis_id"),
        "deep_analysis_items",
        ["deep_analysis_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_deep_analysis_items_content_item_id"),
        "deep_analysis_items",
        ["content_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_deep_analysis_items_content_item_id"), table_name="deep_analysis_items")
    op.drop_index(op.f("ix_deep_analysis_items_deep_analysis_id"), table_name="deep_analysis_items")
    op.drop_table("deep_analysis_items")
