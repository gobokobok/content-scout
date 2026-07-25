import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class DeepAnalysisStatus(enum.StrEnum):
    pending = "pending"
    extracting = "extracting"
    synthesizing = "synthesizing"
    done = "done"
    failed = "failed"


class DeepAnalysisItemStatus(enum.StrEnum):
    done = "done"
    failed = "failed"


class DeepAnalysis(UuidPk, CreatedAt, Base):
    __tablename__ = "deep_analyses"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[DeepAnalysisStatus] = mapped_column(
        Enum(DeepAnalysisStatus, native_enum=False, length=20),
        default=DeepAnalysisStatus.pending,
        nullable=False,
    )
    # Deducted up front (D26 layer-2), before extraction starts — see services/deep_analysis.py.
    tokens_charged: Mapped[int] = mapped_column(Integer, nullable=False)
    report_stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    report_recommendations: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeepAnalysisItem(UuidPk, CreatedAt, Base):
    """E17-S3: one row per (deep_analysis, content_item) — the Haiku extraction pass's output,
    stored so E17-S4's synthesis pass never has to re-fetch comments or re-call Claude."""

    __tablename__ = "deep_analysis_items"
    __table_args__ = (
        UniqueConstraint(
            "deep_analysis_id", "content_item_id", name="uq_deep_analysis_items_analysis_item"
        ),
    )

    deep_analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deep_analyses.id"), nullable=False, index=True
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id"), nullable=False, index=True
    )
    status: Mapped[DeepAnalysisItemStatus] = mapped_column(
        Enum(DeepAnalysisItemStatus, native_enum=False, length=20),
        default=DeepAnalysisItemStatus.failed,
        nullable=False,
    )
    # Content-signal tags — from caption/cover, independent of comments.
    topic: Mapped[str | None] = mapped_column(String(200))
    content_format: Mapped[str | None] = mapped_column(String(100))
    hook_type: Mapped[str | None] = mapped_column(String(100))
    has_cta: Mapped[bool | None] = mapped_column(Boolean)
    # Comment-derived signals — null/empty when the post has no fetched comments (E17-S9).
    sentiment: Mapped[str | None] = mapped_column(String(20))
    complaints: Mapped[list[str] | None] = mapped_column(ARRAY(String(300)))
    praises: Mapped[list[str] | None] = mapped_column(ARRAY(String(300)))
    questions: Mapped[list[str] | None] = mapped_column(ARRAY(String(300)))
    notable_phrases: Mapped[list[str] | None] = mapped_column(ARRAY(String(300)))
    # Coverage signal for E17-S9's thin-data threshold — how many comments this item's
    # extraction actually had to work with (0 when both comment vendors failed/returned none).
    comments_analyzed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
