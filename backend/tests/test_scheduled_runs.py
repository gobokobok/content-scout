import uuid
from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import create_access_token
from src.config import get_settings
from src.db import get_session
from src.main import app
from src.models import AnalysisRun, ScheduledRunSkipReason, ScheduleMode
from src.services.scheduled_runs import fire_due_schedules, is_due, most_recent_occurrence_utc
from src.worker import process_run
from tests.conftest import (
    make_account,
    make_account_list,
    make_project,
    make_run,
    make_scheduled_run,
    make_user,
    make_workspace,
)


class _TestClient(AsyncClient):
    async def __aexit__(self, *exc_info: object) -> None:
        app.dependency_overrides.pop(get_session, None)
        await super().__aexit__(*exc_info)


async def client(session: AsyncSession) -> _TestClient:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    return _TestClient(transport=transport, base_url="http://test")


def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def _setup_project_with_accounts(session: AsyncSession, n: int = 3):
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    for _ in range(n):
        await make_account(session, account_list=account_list)
    await session.commit()
    return owner, project


# --- pure scheduling-math tests (no DB) ---------------------------------------------------


class _FakeSchedule:
    def __init__(self, days_of_week: list[int], time_of_day: time, timezone: str) -> None:
        self.days_of_week = days_of_week
        self.time_of_day = time_of_day
        self.timezone = timezone


def test_most_recent_occurrence_same_day() -> None:
    # 2026-07-22 is a Wednesday (weekday()==2).
    schedule = _FakeSchedule(days_of_week=[2], time_of_day=time(9, 0), timezone="UTC")
    now = datetime(2026, 7, 22, 9, 3, tzinfo=UTC)
    occurrence = most_recent_occurrence_utc(schedule, now)
    assert occurrence == datetime(2026, 7, 22, 9, 0, tzinfo=UTC)


def test_most_recent_occurrence_looks_back_a_week() -> None:
    schedule = _FakeSchedule(days_of_week=[2], time_of_day=time(9, 0), timezone="UTC")
    now = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)  # Friday, after Wednesday's slot
    occurrence = most_recent_occurrence_utc(schedule, now)
    assert occurrence == datetime(2026, 7, 22, 9, 0, tzinfo=UTC)


def test_most_recent_occurrence_respects_timezone() -> None:
    # 09:00 Europe/Moscow (UTC+3, no DST) == 06:00 UTC.
    schedule = _FakeSchedule(days_of_week=[2], time_of_day=time(9, 0), timezone="Europe/Moscow")
    now = datetime(2026, 7, 22, 6, 2, tzinfo=UTC)
    occurrence = most_recent_occurrence_utc(schedule, now)
    assert occurrence == datetime(2026, 7, 22, 6, 0, tzinfo=UTC)


def test_most_recent_occurrence_multi_day_picks_closest() -> None:
    # Mon(0)/Wed(2)/Fri(4) schedule — Friday should win over the earlier-in-the-week days.
    schedule = _FakeSchedule(days_of_week=[0, 2, 4], time_of_day=time(9, 0), timezone="UTC")
    now = datetime(2026, 7, 24, 12, 0, tzinfo=UTC)  # Friday afternoon
    occurrence = most_recent_occurrence_utc(schedule, now)
    assert occurrence == datetime(2026, 7, 24, 9, 0, tzinfo=UTC)


def test_is_due_within_window() -> None:
    schedule = _FakeSchedule(days_of_week=[2], time_of_day=time(9, 0), timezone="UTC")
    now = datetime(2026, 7, 22, 9, 4, tzinfo=UTC)
    assert is_due(schedule, now, window_minutes=5) is True


def test_is_due_outside_window() -> None:
    schedule = _FakeSchedule(days_of_week=[2], time_of_day=time(9, 0), timezone="UTC")
    now = datetime(2026, 7, 22, 9, 6, tzinfo=UTC)
    assert is_due(schedule, now, window_minutes=5) is False


def test_is_due_wrong_day() -> None:
    schedule = _FakeSchedule(days_of_week=[2], time_of_day=time(9, 0), timezone="UTC")
    now = datetime(2026, 7, 23, 9, 2, tzinfo=UTC)
    assert is_due(schedule, now, window_minutes=5) is False


# --- CRUD API tests ------------------------------------------------------------------------


async def test_create_scheduled_run(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/scheduled-runs",
            json={"duration_days": 3, "days_of_week": [1], "time_of_day": "09:00:00"},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["duration_days"] == 3
        assert body["mode"] == "recurring"
        assert body["days_of_week"] == [1]
        assert body["time_of_day"] == "09:00:00"
        assert body["timezone"] == "Europe/Moscow"
        assert body["active"] is True
        assert body["notify_enabled"] is False
        assert body["last_run_id"] is None


async def test_create_scheduled_run_multi_day_recurring(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/scheduled-runs",
            json={
                "duration_days": 3,
                "mode": "recurring",
                "days_of_week": [0, 2, 4],
                "time_of_day": "09:00:00",
                "notify_enabled": True,
            },
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["days_of_week"] == [0, 2, 4]
        assert body["notify_enabled"] is True


async def test_create_scheduled_run_once_rejects_multiple_days(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/scheduled-runs",
            json={
                "duration_days": 3,
                "mode": "once",
                "days_of_week": [0, 2],
                "time_of_day": "09:00:00",
            },
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 422


async def test_create_scheduled_run_rejects_both_scopes(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/scheduled-runs",
            json={
                "duration_days": 3,
                "item_limit": 10,
                "days_of_week": [1],
                "time_of_day": "09:00:00",
            },
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 422


async def test_create_scheduled_run_rejects_invalid_timezone(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)

    async with await client(session) as c:
        resp = await c.post(
            f"/projects/{project.id}/scheduled-runs",
            json={
                "duration_days": 3,
                "days_of_week": [1],
                "time_of_day": "09:00:00",
                "timezone": "Not/AZone",
            },
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 422


async def test_list_scheduled_runs_scoped_to_project(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    other_owner, other_project = await _setup_project_with_accounts(session, n=1)
    await make_scheduled_run(session, project=project, created_by=owner)
    await make_scheduled_run(session, project=other_project, created_by=other_owner)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/scheduled-runs", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert len(resp.json()) == 1


async def test_scheduled_run_feed_exposes_full_record_and_project_name(
    session: AsyncSession,
) -> None:
    """The home feed's Расписание list opens a schedule's edit dialog directly on tap
    (nav-overhaul follow-up), which needs the same fields the per-project CRUD endpoints
    return — not just the summary the feed previously exposed."""
    owner, project = await _setup_project_with_accounts(session, n=2)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        duration_days=5,
        days_of_week=[1, 3],
        time_of_day=time(18, 30),
        notify_enabled=True,
    )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get("/me/scheduled-run-feed", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        [item] = resp.json()
        assert item["id"] == str(scheduled.id)
        assert item["project_name"] == project.name
        assert item["duration_days"] == 5
        assert item["days_of_week"] == [1, 3]
        assert item["time_of_day"] == "18:30:00"
        assert item["notify_enabled"] is True
        assert item["active"] is True


async def test_update_scheduled_run(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    scheduled = await make_scheduled_run(session, project=project, created_by=owner)
    await session.commit()

    async with await client(session) as c:
        resp = await c.patch(
            f"/projects/{project.id}/scheduled-runs/{scheduled.id}",
            json={
                "duration_days": 5,
                "days_of_week": [4],
                "time_of_day": "18:30:00",
                "active": False,
            },
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["duration_days"] == 5
        assert body["days_of_week"] == [4]
        assert body["active"] is False


async def test_update_scheduled_run_not_found(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)

    async with await client(session) as c:
        resp = await c.patch(
            f"/projects/{project.id}/scheduled-runs/{uuid.uuid4()}",
            json={"duration_days": 5, "days_of_week": [4], "time_of_day": "18:30:00"},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 404


async def test_delete_scheduled_run(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    scheduled = await make_scheduled_run(session, project=project, created_by=owner)
    await session.commit()

    async with await client(session) as c:
        resp = await c.delete(
            f"/projects/{project.id}/scheduled-runs/{scheduled.id}",
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 204

        resp = await c.get(f"/projects/{project.id}/scheduled-runs", headers=auth_headers(owner.id))
        assert resp.json() == []


async def test_scheduled_run_out_includes_skip_fields(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        last_skip_reason=ScheduledRunSkipReason.no_tokens,
        last_skip_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
    )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get(f"/projects/{project.id}/scheduled-runs", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        body = resp.json()[0]
        assert body["last_skip_reason"] == "no_tokens"
        assert body["last_skip_at"] is not None


async def test_update_scheduled_run_clears_skip_reason(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        last_skip_reason=ScheduledRunSkipReason.no_accounts,
        last_skip_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
    )
    await session.commit()

    async with await client(session) as c:
        resp = await c.patch(
            f"/projects/{project.id}/scheduled-runs/{scheduled.id}",
            json={"duration_days": 5, "days_of_week": [4], "time_of_day": "18:30:00"},
            headers=auth_headers(owner.id),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["last_skip_reason"] is None
        assert body["last_skip_at"] is None


async def test_list_skipped_schedules_scoped_to_workspace(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    other_owner, other_project = await _setup_project_with_accounts(session, n=1)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        last_skip_reason=ScheduledRunSkipReason.no_tokens,
        last_skip_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
    )
    await make_scheduled_run(session, project=project, created_by=owner)  # never skipped
    await make_scheduled_run(
        session,
        project=other_project,
        created_by=other_owner,
        last_skip_reason=ScheduledRunSkipReason.no_accounts,
        last_skip_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
    )
    await session.commit()

    async with await client(session) as c:
        resp = await c.get("/scheduled-runs/skipped", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["project_id"] == str(project.id)
        assert body[0]["reason"] == "no_tokens"
        assert body[0]["project_name"] == project.name


async def test_list_skipped_schedules_empty_when_none(session: AsyncSession) -> None:
    owner, project = await _setup_project_with_accounts(session, n=1)
    await make_scheduled_run(session, project=project, created_by=owner)
    await session.commit()

    async with await client(session) as c:
        resp = await c.get("/scheduled-runs/skipped", headers=auth_headers(owner.id))
        assert resp.status_code == 200
        assert resp.json() == []


# --- cron dispatcher tests -------------------------------------------------------------


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_fires_due_schedule(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert len(fired) == 1
    mock_enqueue.assert_awaited_once()
    await session.refresh(scheduled)
    assert scheduled.last_run_id == fired[0].id


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_once_mode_deactivates_after_firing(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        mode=ScheduleMode.once,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert len(fired) == 1
    await session.refresh(scheduled)
    assert scheduled.active is False


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_recurring_mode_stays_active(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        mode=ScheduleMode.recurring,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert len(fired) == 1
    await session.refresh(scheduled)
    assert scheduled.active is True


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_copies_notify_enabled_onto_run(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        notify_enabled=True,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert len(fired) == 1
    assert fired[0].notify_on_complete is True


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_defaults_notify_disabled(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert len(fired) == 1
    assert fired[0].notify_on_complete is False


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_skips_not_due(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 14, 0, tzinfo=UTC))

    assert fired == []
    mock_enqueue.assert_not_awaited()


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_skips_inactive(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
        active=False,
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert fired == []
    mock_enqueue.assert_not_awaited()


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_skips_exhausted_token_balance(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    owner.token_balance = 0
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert fired == []
    mock_enqueue.assert_not_awaited()
    await session.refresh(scheduled)
    assert scheduled.last_skip_reason == ScheduledRunSkipReason.no_tokens
    assert scheduled.last_skip_at is not None


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_skips_no_accounts(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=0)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert fired == []
    mock_enqueue.assert_not_awaited()
    await session.refresh(scheduled)
    assert scheduled.last_skip_reason == ScheduledRunSkipReason.no_accounts


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_skips_daily_quota_exceeded(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    for _ in range(get_settings().max_runs_per_user_per_day):
        await make_run(session, project=project, requested_by=owner)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert fired == []
    mock_enqueue.assert_not_awaited()
    await session.refresh(scheduled)
    assert scheduled.last_skip_reason == ScheduledRunSkipReason.quota_exceeded


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_once_mode_deactivates_on_skip(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=0)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        mode=ScheduleMode.once,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert fired == []
    await session.refresh(scheduled)
    assert scheduled.active is False
    assert scheduled.last_skip_reason == ScheduledRunSkipReason.no_accounts


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_clears_stale_skip_reason_on_success(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    scheduled = await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
        last_skip_reason=ScheduledRunSkipReason.no_tokens,
        last_skip_at=datetime(2026, 7, 15, 9, 0, tzinfo=UTC),
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert len(fired) == 1
    await session.refresh(scheduled)
    assert scheduled.last_skip_reason is None
    assert scheduled.last_skip_at is None


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
async def test_fire_due_schedules_creates_run_with_schedule_scope(
    mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    owner, project = await _setup_project_with_accounts(session, n=2)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        duration_days=None,
        item_limit=20,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))

    assert len(fired) == 1
    run = await session.get(AnalysisRun, fired[0].id)
    assert run is not None
    assert run.item_limit == 20
    assert run.duration_days is None
    assert run.project_id == project.id


# --- E14-S5: a scheduled run's completion notifies Telegram like a manual run ---------------


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
@patch("src.worker.notify_run_complete", new_callable=AsyncMock)
async def test_scheduled_run_completion_notifies_telegram(
    mock_notify: AsyncMock, mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    """A schedule fires straight into the same enqueue_run -> process_run path a manual run
    takes (src/api/runs.py:create_run), so notify_run_complete needs no schedule-specific
    call site — this proves that end to end rather than by inspection alone. notify_enabled
    must be explicit here (E14-S6 changed the default to off)."""
    owner, project = await _setup_project_with_accounts(session, n=1)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        notify_enabled=True,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))
    assert len(fired) == 1
    run = fired[0]

    with patch("src.worker.summarize_run_items", new_callable=AsyncMock):
        await process_run(session, run)

    mock_notify.assert_awaited_once()
    notified_run, notified_user, _notified_session = mock_notify.await_args.args
    assert notified_run.id == run.id
    assert notified_user.id == owner.id


@patch("src.services.scheduled_runs.enqueue_run", new_callable=AsyncMock)
@patch("src.worker.notify_run_complete", new_callable=AsyncMock)
async def test_scheduled_run_completion_skips_notify_when_disabled(
    mock_notify: AsyncMock, mock_enqueue: AsyncMock, session: AsyncSession
) -> None:
    """Default notify_enabled=False (E14-S6) must mean no Telegram DM at all, even though
    notify_run_complete's own gate (user.telegram_id set) would otherwise allow it."""
    owner, project = await _setup_project_with_accounts(session, n=1)
    await make_scheduled_run(
        session,
        project=project,
        created_by=owner,
        day_of_week=2,
        time_of_day=time(9, 0),
        timezone="UTC",
    )
    await session.commit()

    fired = await fire_due_schedules(session, now=datetime(2026, 7, 22, 9, 2, tzinfo=UTC))
    assert len(fired) == 1
    run = fired[0]

    with patch("src.worker.summarize_run_items", new_callable=AsyncMock):
        await process_run(session, run)

    mock_notify.assert_not_awaited()
