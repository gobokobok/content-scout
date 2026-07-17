import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
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
