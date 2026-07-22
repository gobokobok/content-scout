import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.models import AnalysisRun, ScheduledRun, User
from src.services.estimator import estimate_run
from src.services.queue import enqueue_run
from src.services.runs import resolve_target_accounts

# arq's cron tick runs every TICK_WINDOW_MINUTES; a schedule fires the first tick whose
# window covers its most recent (day_of_week, time_of_day) occurrence in its own timezone.
# Ticks are aligned to :00/:05/:10.../:55, so consecutive windows exactly tile the timeline
# with no gaps or overlaps.
TICK_WINDOW_MINUTES = 5


def most_recent_occurrence_utc(schedule: ScheduledRun, before: datetime) -> datetime:
    """The most recent UTC instant at or before `before` when schedule's day_of_week +
    time_of_day occurred in the schedule's own timezone. Pure — no DB, safe to unit test."""
    tz = ZoneInfo(schedule.timezone)
    local_before = before.astimezone(tz)
    for days_back in range(7):
        candidate_date = local_before.date() - timedelta(days=days_back)
        if candidate_date.weekday() != schedule.day_of_week:
            continue
        candidate_local = datetime.combine(candidate_date, schedule.time_of_day, tzinfo=tz)
        if candidate_local <= local_before:
            return candidate_local.astimezone(UTC)
    raise AssertionError("unreachable: every weekday occurs within a 7-day lookback")


def is_due(schedule: ScheduledRun, now_utc: datetime, window_minutes: int) -> bool:
    occurrence = most_recent_occurrence_utc(schedule, now_utc)
    return now_utc - occurrence < timedelta(minutes=window_minutes)


async def _over_daily_quota(session: AsyncSession, user_id: uuid.UUID, settings: Settings) -> bool:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    count = await session.scalar(
        select(func.count())
        .select_from(AnalysisRun)
        .where(
            AnalysisRun.requested_by == user_id,
            AnalysisRun.created_at >= today_start,
            AnalysisRun.created_at < today_start + timedelta(days=1),
        )
    )
    return (count or 0) >= settings.max_runs_per_user_per_day


async def _fire_one(session: AsyncSession, schedule: ScheduledRun) -> AnalysisRun | None:
    """Creates+enqueues an AnalysisRun the same way POST /projects/{id}/runs does, minus the
    HTTP-facing error responses: a cron tick has no user to show an error to, so every gate
    that would 400/402/429 a manual run instead just skips this fire silently."""
    accounts = await resolve_target_accounts(session, schedule.project_id, schedule.account_ids)
    if not accounts:
        return None

    user = await session.get(User, schedule.created_by)
    if user is None or user.token_balance <= 0:
        return None

    settings = get_settings()
    if await _over_daily_quota(session, schedule.created_by, settings):
        return None

    est = estimate_run(
        settings,
        len(accounts),
        duration_days=schedule.duration_days,
        item_limit=schedule.item_limit,
    )
    run = AnalysisRun(
        project_id=schedule.project_id,
        requested_by=schedule.created_by,
        duration_days=schedule.duration_days,
        item_limit=schedule.item_limit,
        account_ids=schedule.account_ids,
        estimated_cost_usd=est.estimated_cost_usd,
    )
    session.add(run)
    await session.flush()
    schedule.last_run_id = run.id
    await session.commit()

    await enqueue_run(run.id)
    return run


async def fire_due_schedules(
    session: AsyncSession, now: datetime | None = None
) -> list[AnalysisRun]:
    """The cron tick's core logic: find active schedules due in the current window and fire
    them. Never raises — one bad/exhausted schedule must not block the others or crash the
    tick (mirrors process_run's worker-boundary exception handling)."""
    now = now or datetime.now(UTC)
    schedules = list(
        await session.scalars(select(ScheduledRun).where(ScheduledRun.active.is_(True)))
    )
    fired: list[AnalysisRun] = []
    for schedule in schedules:
        if not is_due(schedule, now, TICK_WINDOW_MINUTES):
            continue
        try:
            run = await _fire_one(session, schedule)
        except Exception:  # noqa: BLE001 — one schedule's failure must not block the rest
            await session.rollback()
            continue
        if run is not None:
            fired.append(run)
    return fired
