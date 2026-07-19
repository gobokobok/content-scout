import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.db import get_session
from src.models import AnalysisRun
from src.services.estimator import estimate_run
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.queue import enqueue_run
from src.services.runs import resolve_target_accounts

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
        "message_ru": (
            "Нет аккаунтов для анализа. Добавьте конкурентов на вкладке «Конкуренты»."
        ),
    },
)


class RunRequestIn(BaseModel):
    duration_days: int = Field(ge=1, le=7)
    account_ids: list[uuid.UUID] | None = None


class EstimateOut(BaseModel):
    apify_units: int
    claude_input_tokens: int
    claude_output_tokens: int
    estimated_cost_usd: Decimal
    accounts_count: int


class RunOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    duration_days: int
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

    @classmethod
    def from_model(cls, run: AnalysisRun) -> "RunOut":
        return cls(
            id=run.id,
            project_id=run.project_id,
            status=run.status.value,
            duration_days=run.duration_days,
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
        )


async def _check_run_quota(session: AsyncSession, user_id: uuid.UUID) -> None:
    settings = get_settings()
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    count = await session.scalar(
        select(func.count()).select_from(AnalysisRun).where(
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
    est = estimate_run(get_settings(), len(accounts), body.duration_days)
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
    accounts = await resolve_target_accounts(session, project_id, body.account_ids)
    if not accounts:
        raise NO_ACCOUNTS

    est = estimate_run(get_settings(), len(accounts), body.duration_days)
    run = AnalysisRun(
        project_id=project_id,
        requested_by=user.id,
        duration_days=body.duration_days,
        account_ids=body.account_ids,
        estimated_cost_usd=est.estimated_cost_usd,
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
