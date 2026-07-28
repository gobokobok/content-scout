"""add token_purchases (E8-S3/D37 pay-as-you-go Telegram Stars top-ups)

Revision ID: d4e5f6a7b8c9
Revises: f7a8b9c0d1e2
Create Date: 2026-07-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "token_purchases",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False),
        sa.Column("amount_stars", sa.Integer(), nullable=False),
        sa.Column("telegram_charge_id", sa.String(length=200), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_token_purchases_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_token_purchases")),
        sa.UniqueConstraint(
            "telegram_charge_id", name=op.f("uq_token_purchases_telegram_charge_id")
        ),
    )
    op.create_index(
        op.f("ix_token_purchases_user_id"), "token_purchases", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_token_purchases_user_id"), table_name="token_purchases")
    op.drop_table("token_purchases")
