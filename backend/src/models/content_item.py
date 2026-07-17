import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class ContentType(enum.StrEnum):
    reel = "reel"
    post = "post"
    carousel = "carousel"
    # future platforms (D1)
    video = "video"
    short = "short"


class ContentItem(UuidPk, CreatedAt, Base):
    __tablename__ = "content_items"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=False, index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[ContentType] = mapped_column(
        Enum(ContentType, native_enum=False, length=20), nullable=False
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str | None] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(1000))
    caption: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    likes: Mapped[int | None] = mapped_column(BigInteger)
    # NULL for post/carousel — IG exposes no view counts there (D14); never 0.
    views: Mapped[int | None] = mapped_column(BigInteger)
    comments: Mapped[int | None] = mapped_column(BigInteger)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
