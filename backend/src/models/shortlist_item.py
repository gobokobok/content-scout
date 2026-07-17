import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func, text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UuidPk


class ShortlistItem(UuidPk, Base):
    __tablename__ = "shortlist_items"
    __table_args__ = (
        # One *active* shortlist entry per item; removed rows stay for history (E6-S2).
        Index(
            "uq_shortlist_items_active",
            "project_id",
            "content_item_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id"), nullable=False
    )
    added_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
