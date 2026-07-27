import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.db import get_session
from src.models import AnalysisRun, DeepAnalysis, DeepAnalysisItem, Project, ScheduledRun, User
from src.services.estimator import estimate_run
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.queue import enqueue_run
from src.services.runs import resolve_target_accounts
from src.services.workspace import get_user_workspace

router = APIRouter(tags=["runs"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)
RUN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "run_not_found", "message_ru": "Запуск не найден."},
)
NO_ACCOUNTS = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail={
        "code": "no_accounts_to_analyze",
        "message_ru": ("Нет аккаунтов для анализа. Добавьте конкурентов на вкладке «Конкуренты»."),
    },
)
NO_BALANCE = HTTPException(
    status_code=status.HTTP_402_PAYMENT_REQUIRED,
    detail={
        "code": "insufficient_token_balance",
        "message_ru": "Баланс токенов исчерпан. Пополните баланс, чтобы запустить анализ.",
    },
)


class RunRequestIn(BaseModel):
    # Exactly one of the two — a day window, or the last N publications per account.
    duration_days: int | None = Field(default=None, ge=1, le=7)
    item_limit: int | None = Field(default=None, ge=1, le=50)
    account_ids: list[uuid.UUID] | None = None
    run_type: Literal["stat_collection", "deep_analysis"] = "stat_collection"

    @model_validator(mode="after")
    def _exactly_one_scope(self) -> "RunRequestIn":
        if (self.duration_days is None) == (self.item_limit is None):
            raise ValueError("Ровно одно из duration_days/item_limit должно быть задано.")
        return self


class EstimateOut(BaseModel):
    apify_units: int
    claude_input_tokens: int
    claude_output_tokens: int
    estimated_cost_usd: Decimal
    accounts_count: int


class RunOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    run_type: str
    status: str
    duration_days: int | None
    item_limit: int | None
    progress_accounts: int
    progress_items: int
    progress_summarized: int
    error_message: str | None
    estimated_cost_usd: Decimal | None
    total_cost_usd: Decimal | None
    total_input_tokens: int
    total_output_tokens: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    # Run-level AI summary (E15-S1) — surfaced for the run detail page's Summary tab (E15-S3).
    summary_status: str
    summary_text: str | None
    summary_topics: list[str] | None

    @classmethod
    def from_model(cls, run: AnalysisRun) -> "RunOut":
        return cls(
            id=run.id,
            project_id=run.project_id,
            run_type=run.run_type,
            status=run.status.value,
            duration_days=run.duration_days,
            item_limit=run.item_limit,
            progress_accounts=run.progress_accounts,
            progress_items=run.progress_items,
            progress_summarized=run.progress_summarized,
            error_message=run.error_message,
            estimated_cost_usd=run.estimated_cost_usd,
            total_cost_usd=run.total_cost_usd,
            total_input_tokens=run.total_input_tokens,
            total_output_tokens=run.total_output_tokens,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            summary_status=run.summary_status.value,
            summary_text=run.summary_text,
            summary_topics=run.summary_topics,
        )


class RunFeedItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    run_type: str
    status: str
    progress_accounts: int
    progress_items: int
    comments_count: int | None
    created_at: datetime
    finished_at: datetime | None


class ScheduledFeedItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    run_type: str
    mode: str
    days_of_week: list[int]
    active: bool
    created_at: datetime


async def _check_run_quota(session: AsyncSession, user_id: uuid.UUID) -> None:
    settings = get_settings()
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
    if (count or 0) >= settings.max_runs_per_user_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "run_quota_exceeded",
                "message_ru": (
                    f"Достигнут лимит запусков: {settings.max_runs_per_user_per_day} в день."
                ),
            },
        )


async def _get_project(session: AsyncSession, user: CurrentUser, project_id: uuid.UUID):
    try:
        return await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None


@router.post("/projects/{project_id}/runs/estimate", response_model=EstimateOut)
async def estimate_project_run(
    project_id: uuid.UUID, body: RunRequestIn, user: CurrentUser, session: SessionDep
) -> EstimateOut:
    await _get_project(session, user, project_id)
    accounts = await resolve_target_accounts(session, project_id, body.account_ids)
    est = estimate_run(
        get_settings(), len(accounts), duration_days=body.duration_days, item_limit=body.item_limit
    )
    return EstimateOut(
        apify_units=est.apify_units,
        claude_input_tokens=est.claude_input_tokens,
        claude_output_tokens=est.claude_output_tokens,
        estimated_cost_usd=est.estimated_cost_usd,
        accounts_count=len(accounts),
    )


@router.post(
    "/projects/{project_id}/runs", response_model=RunOut, status_code=status.HTTP_201_CREATED
)
async def create_run(
    project_id: uuid.UUID, body: RunRequestIn, user: CurrentUser, session: SessionDep
) -> RunOut:
    await _get_project(session, user, project_id)
    await _check_run_quota(session, user.id)
    db_user = await session.get(User, user.id)
    if db_user is not None and db_user.token_balance <= 0:
        raise NO_BALANCE
    accounts = await resolve_target_accounts(session, project_id, body.account_ids)
    if not accounts:
        raise NO_ACCOUNTS

    est = estimate_run(
        get_settings(), len(accounts), duration_days=body.duration_days, item_limit=body.item_limit
    )
    run = AnalysisRun(
        project_id=project_id,
        requested_by=user.id,
        duration_days=body.duration_days,
        item_limit=body.item_limit,
        account_ids=body.account_ids,
        estimated_cost_usd=est.estimated_cost_usd,
        run_type=body.run_type,
    )
    session.add(run)
    await session.commit()

    await enqueue_run(run.id)
    return RunOut.from_model(run)


@router.get("/projects/{project_id}/runs", response_model=list[RunOut])
async def list_runs(project_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> list[RunOut]:
    await _get_project(session, user, project_id)
    runs = await session.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.project_id == project_id)
        .order_by(AnalysisRun.created_at.desc())
    )
    return [RunOut.from_model(run) for run in runs]


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> RunOut:
    run = await session.get(AnalysisRun, run_id)
    if run is None:
        raise RUN_NOT_FOUND
    try:
        await get_owned_project(session, user, run.project_id)
    except ProjectNotFoundError:
        raise RUN_NOT_FOUND from None
    return RunOut.from_model(run)


# Cross-project feed — backs the unified home screen run feed.
feed_router = APIRouter(tags=["runs"])


@feed_router.get("/me/run-feed", response_model=list[RunFeedItem])
async def get_run_feed(user: CurrentUser, session: SessionDep) -> list[RunFeedItem]:
    """All AnalysisRuns across the user's projects, newest-first."""
    workspace = await get_user_workspace(session, user)
    # Deep-analysis runs auto-chain a DeepAnalysis (E17/nav-overhaul) whose comment
    # coverage lives on its items — aggregate it per run_id so the feed can show a
    # "Comments: N" figure without an N+1 query per row.
    comments_subq = (
        select(
            DeepAnalysis.run_id.label("run_id"),
            func.coalesce(func.sum(DeepAnalysisItem.comments_analyzed_count), 0).label(
                "comments_count"
            ),
        )
        .outerjoin(DeepAnalysisItem, DeepAnalysisItem.deep_analysis_id == DeepAnalysis.id)
        .group_by(DeepAnalysis.run_id)
        .subquery()
    )
    rows = await session.execute(
        select(AnalysisRun, Project.name, comments_subq.c.comments_count)
        .join(Project, Project.id == AnalysisRun.project_id)
        .outerjoin(comments_subq, comments_subq.c.run_id == AnalysisRun.id)
        .where(Project.workspace_id == workspace.id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(200)
    )
    return [
        RunFeedItem(
            id=run.id,
            project_id=run.project_id,
            project_name=project_name,
            run_type=run.run_type,
            status=run.status.value,
            progress_accounts=run.progress_accounts,
            progress_items=run.progress_items,
            comments_count=comments_count,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
        for run, project_name, comments_count in rows.all()
    ]


@feed_router.get("/me/scheduled-run-feed", response_model=list[ScheduledFeedItem])
async def get_scheduled_run_feed(user: CurrentUser, session: SessionDep) -> list[ScheduledFeedItem]:
    """All ScheduledRuns across the user's projects, newest-first."""
    workspace = await get_user_workspace(session, user)
    rows = await session.execute(
        select(ScheduledRun, Project.name)
        .join(Project, Project.id == ScheduledRun.project_id)
        .where(Project.workspace_id == workspace.id)
        .order_by(ScheduledRun.created_at.desc())
        .limit(200)
    )
    return [
        ScheduledFeedItem(
            id=sr.id,
            project_id=sr.project_id,
            project_name=project_name,
            run_type=sr.run_type,
            mode=sr.mode.value,
            days_of_week=sorted(sr.days_of_week),
            active=sr.active,
            created_at=sr.created_at,
        )
        for sr, project_name in rows.all()
    ]
