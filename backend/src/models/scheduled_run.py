import enum
import uuid
from datetime import datetime, time

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class ScheduleMode(enum.StrEnum):
    # once: fires on the next occurrence of its single selected weekday, then
    # auto-deactivates (see services/scheduled_runs.py:_fire_one). recurring: fires every
    # selected weekday indefinitely, until deactivated or the user's tokens run out.
    once = "once"
    recurring = "recurring"


class ScheduledRunSkipReason(enum.StrEnum):
    # Same three silent-skip gates _fire_one has always had (E14-S2) — now recorded instead
    # of just vanishing, so the UI can tell the user why a due schedule didn't fire.
    no_accounts = "no_accounts"
    no_tokens = "no_tokens"
    quota_exceeded = "quota_exceeded"


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
        # Every element of days_of_week must be a valid weekday (0=Monday..6=Sunday) and
        # there must be at least one — array containment (`<@`) checks the values, and
        # cardinality() (unlike array_length, which is NULL for a zero-length array — a
        # Postgres CHECK treats a NULL result as passing) catches the empty-array case.
        CheckConstraint(
            "days_of_week <@ ARRAY[0,1,2,3,4,5,6] AND cardinality(days_of_week) >= 1",
            name="days_of_week_range",
        ),
    )

    # "stat_collection" = standard scrape; "deep_analysis" = scrape + auto-chained deep analysis.
    run_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="stat_collection")

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    # NULL = every active account in the project's IG list; otherwise an explicit subset.
    account_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(Uuid()), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(nullable=True)
    item_limit: Mapped[int | None] = mapped_column(nullable=True)
    # 0=Monday .. 6=Sunday, matching datetime.weekday(). One row = one schedule, regardless
    # of how many days it fires on (E14-S6 — was a single day_of_week, one row per day).
    days_of_week: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    mode: Mapped[ScheduleMode] = mapped_column(
        Enum(ScheduleMode, native_enum=False, length=20),
        default=ScheduleMode.recurring,
        nullable=False,
    )
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    # IANA tz name (e.g. "Europe/Moscow") — days_of_week/time_of_day are evaluated in it.
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Per-schedule opt-in (default off) to DM the user on Telegram when a run this schedule
    # fired completes — independent of manual runs, which always notify
    # (AnalysisRun.notify_on_complete).
    notify_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True
    )
    # Set by _fire_one when a due schedule is skipped (never on a genuine error — those are
    # still swallowed by fire_due_schedules' try/except); cleared on the next successful fire.
    last_skip_reason: Mapped[ScheduledRunSkipReason | None] = mapped_column(
        Enum(ScheduledRunSkipReason, native_enum=False, length=20), nullable=True
    )
    last_skip_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
