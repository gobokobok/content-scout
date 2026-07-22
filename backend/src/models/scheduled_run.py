import uuid
from datetime import time

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Time,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class ScheduledRun(UuidPk, CreatedAt, Base):
    __tablename__ = "scheduled_runs"
    # Same XOR scope pattern as AnalysisRun (E3-S7) — exactly one of duration_days
    # (day window) / item_limit (last N publications per account) is set.
    __table_args__ = (
        CheckConstraint(
            "(duration_days IS NOT NULL AND item_limit IS NULL"
            " AND duration_days BETWEEN 1 AND 7)"
            " OR (item_limit IS NOT NULL AND duration_days IS NULL"
            " AND item_limit BETWEEN 1 AND 50)",
            name="duration_or_item_limit_range",
        ),
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="day_of_week_range"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # NULL = every active account in the project's IG list; otherwise an explicit subset.
    account_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(Uuid()), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(nullable=True)
    item_limit: Mapped[int | None] = mapped_column(nullable=True)
    # 0=Monday .. 6=Sunday, matching datetime.weekday().
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    # IANA tz name (e.g. "Europe/Moscow") — day_of_week/time_of_day are evaluated in it.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True
    )
