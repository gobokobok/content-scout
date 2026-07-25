import uuid
from datetime import datetime, time
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import Project, ScheduledRun, ScheduleMode
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.workspace import get_user_workspace

router = APIRouter(prefix="/projects/{project_id}/scheduled-runs", tags=["scheduled-runs"])
# Cross-project — backs the header notification panel, which has no single project in scope.
alerts_router = APIRouter(prefix="/scheduled-runs", tags=["scheduled-runs"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)
SCHEDULED_RUN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "scheduled_run_not_found", "message_ru": "Расписание не найдено."},
)


class ScheduledRunIn(BaseModel):
    # Exactly one of the two — a day window, or the last N publications per account,
    # same XOR scope as RunRequestIn (src/api/runs.py).
    duration_days: int | None = Field(default=None, ge=1, le=7)
    item_limit: int | None = Field(default=None, ge=1, le=50)
    account_ids: list[uuid.UUID] | None = None
    # once: exactly one day (its next occurrence fires, then the schedule deactivates).
    # recurring: 1-7 days, fires every selected day indefinitely (E14-S6).
    mode: Literal["once", "recurring"] = "recurring"
    days_of_week: list[int] = Field(min_length=1, max_length=7)
    time_of_day: time
    timezone: str = "Europe/Moscow"
    active: bool = True
    notify_enabled: bool = False

    @model_validator(mode="after")
    def _exactly_one_scope(self) -> "ScheduledRunIn":
        if (self.duration_days is None) == (self.item_limit is None):
            raise ValueError("Ровно одно из duration_days/item_limit должно быть задано.")
        return self

    @model_validator(mode="after")
    def _valid_timezone(self) -> "ScheduledRunIn":
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError:
            raise ValueError("Некорректный часовой пояс.") from None
        return self

    @model_validator(mode="after")
    def _valid_days_of_week(self) -> "ScheduledRunIn":
        if any(d < 0 or d > 6 for d in self.days_of_week):
            raise ValueError("Дни недели должны быть в диапазоне 0-6.")
        if len(set(self.days_of_week)) != len(self.days_of_week):
            raise ValueError("Дни недели не должны повторяться.")
        if self.mode == "once" and len(self.days_of_week) != 1:
            raise ValueError("Разовый запуск требует ровно один день.")
        return self


class ScheduledRunOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    account_ids: list[uuid.UUID] | None
    duration_days: int | None
    item_limit: int | None
    mode: str
    days_of_week: list[int]
    time_of_day: time
    timezone: str
    active: bool
    notify_enabled: bool
    last_run_id: uuid.UUID | None
    last_skip_reason: str | None
    last_skip_at: datetime | None
    created_at: datetime

    @classmethod
    def from_model(cls, scheduled_run: ScheduledRun) -> "ScheduledRunOut":
        return cls(
            id=scheduled_run.id,
            project_id=scheduled_run.project_id,
            account_ids=scheduled_run.account_ids,
            duration_days=scheduled_run.duration_days,
            item_limit=scheduled_run.item_limit,
            mode=scheduled_run.mode.value,
            days_of_week=sorted(scheduled_run.days_of_week),
            time_of_day=scheduled_run.time_of_day,
            timezone=scheduled_run.timezone,
            active=scheduled_run.active,
            notify_enabled=scheduled_run.notify_enabled,
            last_run_id=scheduled_run.last_run_id,
            last_skip_reason=scheduled_run.last_skip_reason.value
            if scheduled_run.last_skip_reason
            else None,
            last_skip_at=scheduled_run.last_skip_at,
            created_at=scheduled_run.created_at,
        )


class SkippedScheduleOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    reason: str
    skipped_at: datetime


async def _get_project(session: AsyncSession, user: CurrentUser, project_id: uuid.UUID):
    try:
        return await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None


async def _get_scheduled_run(
    session: AsyncSession, project_id: uuid.UUID, scheduled_run_id: uuid.UUID
) -> ScheduledRun:
    scheduled_run = await session.scalar(
        select(ScheduledRun).where(
            ScheduledRun.id == scheduled_run_id, ScheduledRun.project_id == project_id
        )
    )
    if scheduled_run is None:
        raise SCHEDULED_RUN_NOT_FOUND
    return scheduled_run


@router.post("", response_model=ScheduledRunOut, status_code=status.HTTP_201_CREATED)
async def create_scheduled_run(
    project_id: uuid.UUID, body: ScheduledRunIn, user: CurrentUser, session: SessionDep
) -> ScheduledRunOut:
    await _get_project(session, user, project_id)
    scheduled_run = ScheduledRun(
        project_id=project_id,
        created_by=user.id,
        account_ids=body.account_ids,
        duration_days=body.duration_days,
        item_limit=body.item_limit,
        mode=ScheduleMode(body.mode),
        days_of_week=body.days_of_week,
        time_of_day=body.time_of_day,
        timezone=body.timezone,
        active=body.active,
        notify_enabled=body.notify_enabled,
    )
    session.add(scheduled_run)
    await session.commit()
    return ScheduledRunOut.from_model(scheduled_run)


@router.get("", response_model=list[ScheduledRunOut])
async def list_scheduled_runs(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[ScheduledRunOut]:
    await _get_project(session, user, project_id)
    scheduled_runs = await session.scalars(
        select(ScheduledRun)
        .where(ScheduledRun.project_id == project_id)
        .order_by(ScheduledRun.created_at.desc())
    )
    return [ScheduledRunOut.from_model(sr) for sr in scheduled_runs]


@router.patch("/{scheduled_run_id}", response_model=ScheduledRunOut)
async def update_scheduled_run(
    project_id: uuid.UUID,
    scheduled_run_id: uuid.UUID,
    body: ScheduledRunIn,
    user: CurrentUser,
    session: SessionDep,
) -> ScheduledRunOut:
    await _get_project(session, user, project_id)
    scheduled_run = await _get_scheduled_run(session, project_id, scheduled_run_id)
    scheduled_run.account_ids = body.account_ids
    scheduled_run.duration_days = body.duration_days
    scheduled_run.item_limit = body.item_limit
    scheduled_run.mode = ScheduleMode(body.mode)
    scheduled_run.days_of_week = body.days_of_week
    scheduled_run.time_of_day = body.time_of_day
    scheduled_run.timezone = body.timezone
    scheduled_run.active = body.active
    scheduled_run.notify_enabled = body.notify_enabled
    # An edit is a fresh intent — don't keep showing a stale skip reason from before the change.
    scheduled_run.last_skip_reason = None
    scheduled_run.last_skip_at = None
    await session.commit()
    return ScheduledRunOut.from_model(scheduled_run)


@router.delete("/{scheduled_run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scheduled_run(
    project_id: uuid.UUID, scheduled_run_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    await _get_project(session, user, project_id)
    scheduled_run = await _get_scheduled_run(session, project_id, scheduled_run_id)
    await session.delete(scheduled_run)
    await session.commit()


@alerts_router.get("/skipped", response_model=list[SkippedScheduleOut])
async def list_skipped_schedules(
    user: CurrentUser, session: SessionDep
) -> list[SkippedScheduleOut]:
    """Every schedule across the user's projects whose most recent due tick was skipped (no
    active accounts / no tokens / daily quota) — backs the header notification panel, since a
    skip happens server-side on a cron tick with no browser session to push it to directly."""
    workspace = await get_user_workspace(session, user)
    rows = await session.execute(
        select(ScheduledRun, Project.name)
        .join(Project, Project.id == ScheduledRun.project_id)
        .where(
            Project.workspace_id == workspace.id,
            ScheduledRun.last_skip_reason.is_not(None),
        )
        .order_by(ScheduledRun.last_skip_at.desc())
    )
    return [
        SkippedScheduleOut(
            id=scheduled_run.id,
            project_id=scheduled_run.project_id,
            project_name=project_name,
            reason=scheduled_run.last_skip_reason.value,  # type: ignore[union-attr]
            skipped_at=scheduled_run.last_skip_at,  # type: ignore[arg-type]
        )
        for scheduled_run, project_name in rows.all()
    ]
