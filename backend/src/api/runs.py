import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import String, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.scheduled_runs import SCHEDULE_LIST_VISIBLE, ScheduledRunOut
from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.db import get_session
from src.middleware.rate_limit import check_rate_limit
from src.models import (
    Account,
    AccountList,
    AnalysisRun,
    ContentItem,
    DeepAnalysis,
    DeepAnalysisItem,
    PlatformSlug,
    Project,
    ScheduledRun,
    User,
)
from src.services.estimator import estimate_run
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.queue import enqueue_run
from src.services.runs import resolve_target_accounts
from src.services.url_normalizer import InvalidAccountUrlError, normalize_post_url
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
    # Exactly one of duration_days/item_limit — a day window, or the last N publications per
    # account. Both left unset only for a post-mode Analysis run (D49/D50), which has no such
    # scope (its "top N comments" field is comments_limit instead).
    duration_days: int | None = Field(default=None, ge=1, le=7)
    item_limit: int | None = Field(default=None, ge=1, le=50)
    account_ids: list[uuid.UUID] | None = None
    run_type: Literal["stat_collection", "deep_analysis"] = "stat_collection"
    # D49/D50: only meaningful for run_type="deep_analysis" — 'account' (single competitor +
    # day/count scope) or 'post' (single publication URL, comments-only, no scope step).
    analysis_mode: Literal["account", "post"] | None = None
    target_post_url: str | None = None
    comments_limit: int | None = Field(default=None, ge=1, le=100)
    # Was schedule-only (ScheduledRunIn.notify_enabled) — now overarching, so "run now" gets
    # the same choice a schedule always had instead of being unconditionally notified with no
    # opt-out. Defaults True to preserve "run now"'s pre-existing unconditional-notify behavior
    # for any caller that omits this field.
    notify_on_complete: bool = True

    @model_validator(mode="after")
    def _validate_scope(self) -> "RunRequestIn":
        if self.run_type != "deep_analysis":
            if self.analysis_mode is not None or self.target_post_url is not None:
                raise ValueError(
                    "analysis_mode/target_post_url применимы только к run_type=deep_analysis."
                )
        elif self.analysis_mode is None:
            raise ValueError("analysis_mode обязателен для run_type=deep_analysis.")
        elif self.analysis_mode == "post":
            if self.duration_days is not None or self.item_limit is not None:
                raise ValueError("Для анализа публикации duration_days/item_limit не задаются.")
            if not self.target_post_url:
                raise ValueError("target_post_url обязателен для analysis_mode=post.")
            return self
        elif self.account_ids is None or len(self.account_ids) != 1:
            raise ValueError("Для анализа аккаунта нужно выбрать ровно один аккаунт.")

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
    # D49/D50: only set for run_type="deep_analysis" — which of the two Analysis entry modes
    # this run used, and post mode's own fields.
    analysis_mode: str | None
    target_post_url: str | None
    comments_limit: int | None

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
            analysis_mode=run.analysis_mode,
            target_post_url=run.target_post_url,
            comments_limit=run.comments_limit,
        )


class RunAccountOut(BaseModel):
    """E15-S5: the settings drill-down sheet's account list — derived entirely from existing
    data (Account rows + this run's ContentItem rows), no new columns needed. `succeeded` is
    True iff this run actually produced at least one ContentItem for the account; `fail_reason`
    mirrors Account.fail_reason (the account's own last-fetch-attempt reason, the only place
    this project tracks a failure reason today) and is only surfaced when the run didn't
    succeed for that account."""

    id: uuid.UUID
    handle: str
    display_name: str | None
    avatar_url: str | None
    succeeded: bool
    fail_reason: str | None


class RunFeedItem(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    run_type: str
    status: str
    progress_accounts: int
    progress_items: int
    comments_count: int | None
    # The auto-chained DeepAnalysis for this run, once it exists — lets the home feed link a
    # done deep_analysis run straight to its report instead of the plain run-detail page, and
    # show the *analysis*'s own status (extracting/synthesizing/failed) rather than just the
    # base run's — a run can finish scraping cleanly while its deep analysis still fails.
    deep_analysis_id: uuid.UUID | None
    deep_analysis_status: str | None
    created_at: datetime
    finished_at: datetime | None


class ScheduledFeedItem(ScheduledRunOut):
    # Full ScheduledRunOut shape (not just a summary) plus project_name — the home feed's
    # Расписание list opens this schedule's edit dialog directly on tap, which needs the
    # complete record, not a trimmed-down feed row.
    project_name: str


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
    project_id: uuid.UUID,
    body: RunRequestIn,
    user: CurrentUser,
    session: SessionDep,
    request: Request,
) -> RunOut:
    await _get_project(session, user, project_id)
    await check_rate_limit(
        request, limit=get_settings().write_endpoint_rate_limit_per_minute, key=str(user.id)
    )
    await _check_run_quota(session, user.id)
    db_user = await session.get(User, user.id)
    if db_user is not None and db_user.token_balance <= 0:
        raise NO_BALANCE

    target_post_url: str | None = None
    accounts: list = []
    if body.analysis_mode == "post":
        try:
            target_post_url = normalize_post_url(body.target_post_url or "").url
        except InvalidAccountUrlError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "invalid_post_url", "message_ru": exc.message_ru},
            ) from None
    else:
        accounts = await resolve_target_accounts(session, project_id, body.account_ids)
        if not accounts:
            raise NO_ACCOUNTS

    est = estimate_run(
        get_settings(),
        len(accounts) or 1,
        duration_days=body.duration_days,
        item_limit=body.item_limit,
    )
    run = AnalysisRun(
        project_id=project_id,
        requested_by=user.id,
        duration_days=body.duration_days,
        item_limit=body.item_limit,
        account_ids=body.account_ids,
        estimated_cost_usd=est.estimated_cost_usd,
        run_type=body.run_type,
        analysis_mode=body.analysis_mode,
        target_post_url=target_post_url,
        comments_limit=body.comments_limit,
        notify_on_complete=body.notify_on_complete,
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


@router.get("/runs/{run_id}/accounts", response_model=list[RunAccountOut])
async def get_run_accounts(
    run_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[RunAccountOut]:
    """E15-S5: the settings sheet's account list, for both Review run-detail pages and (via
    DeepAnalysisOut.run_id) the Analysis report page. Post-mode Analysis runs (analysis_mode=
    "post") have no account scope — their one resolved author isn't a competitor-list entry."""
    run = await session.get(AnalysisRun, run_id)
    if run is None:
        raise RUN_NOT_FOUND
    try:
        await get_owned_project(session, user, run.project_id)
    except ProjectNotFoundError:
        raise RUN_NOT_FOUND from None

    if run.analysis_mode == "post":
        return []

    if run.account_ids is not None:
        accounts_stmt = select(Account).where(Account.id.in_(run.account_ids))
    else:
        account_list = await session.scalar(
            select(AccountList).where(
                AccountList.project_id == run.project_id,
                AccountList.platform == PlatformSlug.instagram,
            )
        )
        if account_list is None:
            return []
        accounts_stmt = select(Account).where(
            Account.account_list_id == account_list.id,
            Account.archived_at.is_(None),
            Account.hidden.is_(False),
        )
    accounts = list(await session.scalars(accounts_stmt))
    if not accounts:
        return []

    succeeded_ids = set(
        await session.scalars(
            select(ContentItem.account_id)
            .where(
                ContentItem.run_id == run.id, ContentItem.account_id.in_([a.id for a in accounts])
            )
            .distinct()
        )
    )
    return [
        RunAccountOut(
            id=account.id,
            handle=account.handle,
            display_name=account.display_name,
            avatar_url=account.avatar_url,
            succeeded=account.id in succeeded_ids,
            fail_reason=None if account.id in succeeded_ids else account.fail_reason,
        )
        for account in accounts
    ]


# Cross-project feed — backs the unified home screen run feed.
feed_router = APIRouter(tags=["runs"])


@feed_router.get("/me/run-feed", response_model=list[RunFeedItem])
async def get_run_feed(user: CurrentUser, session: SessionDep) -> list[RunFeedItem]:
    """All AnalysisRuns across the user's projects, newest-first."""
    workspace = await get_user_workspace(session, user)
    # Deep-analysis runs auto-chain a DeepAnalysis (E17/nav-overhaul) whose comment coverage
    # lives on its items — aggregate it per run_id so the feed can show a "Comments: N" figure
    # without an N+1 query per row. The auto-chain creates at most one DeepAnalysis per run, so
    # MAX(id) here is just "the one that exists", not an arbitrary tie-break — cast to text
    # since Postgres has no MAX aggregate for uuid.
    comments_subq = (
        select(
            DeepAnalysis.run_id.label("run_id"),
            func.coalesce(func.sum(DeepAnalysisItem.comments_analyzed_count), 0).label(
                "comments_count"
            ),
            func.max(cast(DeepAnalysis.id, String)).label("deep_analysis_id"),
            func.max(cast(DeepAnalysis.status, String)).label("deep_analysis_status"),
        )
        .outerjoin(DeepAnalysisItem, DeepAnalysisItem.deep_analysis_id == DeepAnalysis.id)
        .group_by(DeepAnalysis.run_id)
        .subquery()
    )
    rows = await session.execute(
        select(
            AnalysisRun,
            Project.name,
            comments_subq.c.comments_count,
            comments_subq.c.deep_analysis_id,
            comments_subq.c.deep_analysis_status,
        )
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
            deep_analysis_id=deep_analysis_id,
            deep_analysis_status=deep_analysis_status,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
        for run, project_name, comments_count, deep_analysis_id, deep_analysis_status in rows.all()
    ]


@feed_router.get("/me/scheduled-run-feed", response_model=list[ScheduledFeedItem])
async def get_scheduled_run_feed(user: CurrentUser, session: SessionDep) -> list[ScheduledFeedItem]:
    """All ScheduledRuns across the user's projects, newest-first."""
    workspace = await get_user_workspace(session, user)
    rows = await session.execute(
        select(ScheduledRun, Project.name)
        .join(Project, Project.id == ScheduledRun.project_id)
        .where(Project.workspace_id == workspace.id, SCHEDULE_LIST_VISIBLE)
        .order_by(ScheduledRun.created_at.desc())
        .limit(200)
    )
    return [
        ScheduledFeedItem(**ScheduledRunOut.from_model(sr).model_dump(), project_name=project_name)
        for sr, project_name in rows.all()
    ]
