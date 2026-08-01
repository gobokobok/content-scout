"""add archived_at to accounts, scope the account-list cap trigger to non-archived rows

Revision ID: a2b3c4d5e6f7
Revises: d4e5f6a7b8c9
Create Date: 2026-08-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    # Archived rows no longer count toward the 50-per-list cap this trigger backstops —
    # otherwise repeated archive/re-add cycles would eventually block adding real new accounts.
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


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION enforce_account_list_cap() RETURNS trigger AS $$
        BEGIN
            IF (SELECT count(*) FROM accounts WHERE account_list_id = NEW.account_list_id) >= 50
            THEN
                RAISE EXCEPTION 'account list % already has 50 accounts', NEW.account_list_id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.drop_column("accounts", "archived_at")
