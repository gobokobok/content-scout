import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk

# Hard product cap (D13); enforced app-side on add and by a DB trigger as safeguard.
MAX_ACCOUNTS_PER_LIST = 50


class AccountStatus(enum.StrEnum):
    active = "active"
    failed = "failed"


class Account(UuidPk, CreatedAt, Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("account_list_id", "normalized_url"),)

    account_list_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("account_lists.id"), nullable=False, index=True
    )
    input_url: Mapped[str] = mapped_column(String(500), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(500), nullable=False)
    handle: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False, length=20),
        default=AccountStatus.active,
        nullable=False,
    )
    fail_reason: Mapped[str | None] = mapped_column(String(500))
    followers_count: Mapped[int | None] = mapped_column()
    # Shared "last profile fetch" timestamp for followers_count/display_name/avatar_url — all
    # three come from the same Platform.fetch_profile() call, so one column covers all of them.
    followers_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    display_name: Mapped[str | None] = mapped_column(String(200))
    avatar_url: Mapped[str | None] = mapped_column(String(1000))
    # Soft-delete (mirrors Project.archived_at): removing a competitor must not destroy the
    # content_items/shortlist_items/deep_analysis_items history tied to past runs. Re-adding
    # the same normalized_url un-archives the row instead of erroring on the unique constraint.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # True only for accounts auto-created by post-mode Analysis's single-post author resolution
    # (worker.py:_resolve_or_create_account) — the row is real (ContentItem.account_id needs a
    # non-nullable FK) but must not silently pollute the user's actual competitor list: hidden
    # from GET /accounts (the picker), excluded from resolve_target_accounts' "whole list" scope
    # and the 50-per-list cap. Explicitly re-adding the same handle via "Добавить конкурентов"
    # clears this flag (api/accounts.py:add_accounts), surfacing it as a real competitor.
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
