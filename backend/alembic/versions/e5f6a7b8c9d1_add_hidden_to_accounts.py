"""add hidden to accounts, scope the account-list cap trigger to non-hidden rows too

Revision ID: e5f6a7b8c9d1
Revises: c2d3e4f5a6b7
Create Date: 2026-08-04 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f6a7b8c9d1"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Direct bug fix (chat-reported): post-mode Analysis auto-creates the resolved author as a
    # real Account (ContentItem.account_id is non-nullable) but that must not silently count
    # against the user's 50-per-list competitor cap either — same "non-archived rows only"
    # rescoping a2b3c4d5e6f7 already did for archived_at, extended to hidden.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_account_list_cap() RETURNS trigger AS $$
        BEGIN
            IF (
                SELECT count(*) FROM accounts
                WHERE account_list_id = NEW.account_list_id
                  AND archived_at IS NULL
                  AND hidden IS FALSE
            ) >= 50
            THEN
                RAISE EXCEPTION 'account list % already has 50 accounts', NEW.account_list_id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_account_list_cap() RETURNS trigger AS $$
        BEGIN
            IF (
                SELECT count(*) FROM accounts
                WHERE account_list_id = NEW.account_list_id AND archived_at IS NULL
            ) >= 50
            THEN
                RAISE EXCEPTION 'account list % already has 50 accounts', NEW.account_list_id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.drop_column("accounts", "hidden")
