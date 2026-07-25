import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class RunStatus(enum.StrEnum):
    pending = "pending"
    scraping = "scraping"
    summarizing = "summarizing"
    done = "done"
    failed = "failed"


class RunSummaryStatus(enum.StrEnum):
    pending = "pending"
    done = "done"
    failed = "failed"


class AnalysisRun(UuidPk, CreatedAt, Base):
    __tablename__ = "analysis_runs"
    # Exactly one of duration_days (a day window) / item_limit (last N publications per
    # account) is set — mutually exclusive ways to scope a scrape, never both.
    __table_args__ = (
        CheckConstraint(
            "(duration_days IS NOT NULL AND item_limit IS NULL"
            " AND duration_days BETWEEN 1 AND 7)"
            " OR (item_limit IS NOT NULL AND duration_days IS NULL"
            " AND item_limit BETWEEN 1 AND 50)",
            name="duration_or_item_limit_range",
        ),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    duration_days: Mapped[int | None] = mapped_column(nullable=True)
    item_limit: Mapped[int | None] = mapped_column(nullable=True)
    # NULL = every active account in the project's IG list; otherwise an explicit subset.
    account_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(Uuid()), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=20),
        default=RunStatus.pending,
        nullable=False,
    )
    # Gates the Telegram completion DM (services/telegram_notify.py). True for every manual
    # run (unchanged E8-S2 behavior); scheduled runs copy their ScheduledRun.notify_enabled
    # (E14-S6 — schedules default this off, unlike manual runs).
    notify_on_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    progress_accounts: Mapped[int] = mapped_column(default=0, nullable=False)
    progress_items: Mapped[int] = mapped_column(default=0, nullable=False)
    progress_summarized: Mapped[int] = mapped_column(default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    total_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    total_input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Run-level AI summary (E15-S1) — synthesized once, after per-item summarization,
    # non-fatal to the run on failure (see services/run_summary.py).
    summary_status: Mapped[RunSummaryStatus] = mapped_column(
        Enum(RunSummaryStatus, native_enum=False, length=20),
        default=RunSummaryStatus.pending,
        nullable=False,
    )
    summary_text: Mapped[str | None] = mapped_column(Text)
    summary_topics: Mapped[list[str] | None] = mapped_column(ARRAY(String(100)))
    summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
