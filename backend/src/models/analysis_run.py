import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
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


class AnalysisRun(UuidPk, CreatedAt, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (CheckConstraint("duration_days BETWEEN 1 AND 7", name="duration_days_range"),)

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    duration_days: Mapped[int] = mapped_column(nullable=False)
    # NULL = every active account in the project's IG list; otherwise an explicit subset.
    account_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(Uuid()), nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False, length=20),
        default=RunStatus.pending,
        nullable=False,
    )
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
