import enum
import uuid

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class PlatformSlug(enum.StrEnum):
    instagram = "instagram"
    youtube = "youtube"
    tiktok = "tiktok"
    threads = "threads"


class AccountList(UuidPk, CreatedAt, Base):
    __tablename__ = "account_lists"
    __table_args__ = (UniqueConstraint("project_id", "platform"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    platform: Mapped[PlatformSlug] = mapped_column(
        Enum(PlatformSlug, native_enum=False, length=20), nullable=False
    )
