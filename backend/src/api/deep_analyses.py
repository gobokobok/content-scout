import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.db import get_session
from src.models import AnalysisRun, ContentItem, DeepAnalysis, DeepAnalysisItem, User
from src.services.deep_analysis import (
    InsufficientTokenBalanceError,
    RunNotDoneError,
    compute_tokens_charged,
    start_deep_analysis,
)
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.queue import enqueue_deep_analysis

router = APIRouter(tags=["deep-analyses"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)
RUN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "run_not_found", "message_ru": "Запуск не найден."},
)
DEEP_ANALYSIS_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "deep_analysis_not_found", "message_ru": "Анализ не найден."},
)
RUN_NOT_DONE = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail={
        "code": "run_not_done",
        "message_ru": "Разбор доступен только для завершённых запусков.",
    },
)
NO_BALANCE = HTTPException(
    status_code=status.HTTP_402_PAYMENT_REQUIRED,
    detail={
        "code": "insufficient_token_balance",
        "message_ru": "Баланс токенов исчерпан. Пополните баланс, чтобы запустить анализ.",
    },
)


class DeepAnalysisEstimateOut(BaseModel):
    tokens: int


class DeepAnalysisOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    project_id: uuid.UUID
    status: str
    tokens_charged: int
    error_message: str | None
    report_stats: dict[str, Any] | None
    report_recommendations: dict[str, Any] | None
    # Total comments actually fetched across this analysis's items — only populated by
    # get_deep_analysis (the report page's summary card), not list/create, which have no need
    # for it and would otherwise pay for the aggregate query on every row.
    comments_analyzed_count: int | None = None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_model(cls, analysis: DeepAnalysis) -> "DeepAnalysisOut":
        return cls(
            id=analysis.id,
            run_id=analysis.run_id,
            project_id=analysis.project_id,
            status=analysis.status.value,
            tokens_charged=analysis.tokens_charged,
            error_message=analysis.error_message,
            report_stats=analysis.report_stats,
            report_recommendations=analysis.report_recommendations,
            created_at=analysis.created_at,
            completed_at=analysis.completed_at,
        )


async def _get_project(session: AsyncSession, user: CurrentUser, project_id: uuid.UUID):
    try:
        return await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None


@router.get(
    "/projects/{project_id}/runs/{run_id}/deep-analyses/estimate",
    response_model=DeepAnalysisEstimateOut,
)
async def estimate_deep_analysis(
    project_id: uuid.UUID, run_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> DeepAnalysisEstimateOut:
    """Read-only token preview for E17-S6's new-analysis sheet — mirrors `compute_tokens_charged`
    exactly, just without deducting. Added alongside S6 rather than S5 because only the
    frontend picker needs a pre-charge number; `create_deep_analysis` already returns the real
    `tokens_charged` once the charge has happened."""
    await _get_project(session, user, project_id)
    run = await session.get(AnalysisRun, run_id)
    if run is None or run.project_id != project_id:
        raise RUN_NOT_FOUND

    items_count = await session.scalar(
        select(func.count()).select_from(ContentItem).where(ContentItem.run_id == run_id)
    )
    tokens = compute_tokens_charged(items_count or 0, get_settings())
    return DeepAnalysisEstimateOut(tokens=tokens)


@router.post(
    "/projects/{project_id}/runs/{run_id}/deep-analyses",
    response_model=DeepAnalysisOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_deep_analysis(
    project_id: uuid.UUID, run_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> DeepAnalysisOut:
    await _get_project(session, user, project_id)
    run = await session.get(AnalysisRun, run_id)
    if run is None or run.project_id != project_id:
        raise RUN_NOT_FOUND

    db_user = await session.get(User, user.id)
    if db_user is None:
        raise RUN_NOT_FOUND
    settings = get_settings()
    try:
        analysis = await start_deep_analysis(session, run, db_user, settings)
    except RunNotDoneError:
        raise RUN_NOT_DONE from None
    except InsufficientTokenBalanceError:
        raise NO_BALANCE from None
    await session.commit()

    await enqueue_deep_analysis(analysis.id)
    return DeepAnalysisOut.from_model(analysis)


@router.get("/projects/{project_id}/deep-analyses", response_model=list[DeepAnalysisOut])
async def list_deep_analyses(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[DeepAnalysisOut]:
    await _get_project(session, user, project_id)
    rows = await session.scalars(
        select(DeepAnalysis)
        .where(DeepAnalysis.project_id == project_id)
        .order_by(DeepAnalysis.created_at.desc())
    )
    return [DeepAnalysisOut.from_model(row) for row in rows]


@router.get("/deep-analyses/{analysis_id}", response_model=DeepAnalysisOut)
async def get_deep_analysis(
    analysis_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> DeepAnalysisOut:
    analysis = await session.get(DeepAnalysis, analysis_id)
    if analysis is None:
        raise DEEP_ANALYSIS_NOT_FOUND
    try:
        await get_owned_project(session, user, analysis.project_id)
    except ProjectNotFoundError:
        raise DEEP_ANALYSIS_NOT_FOUND from None
    comments_analyzed_count = await session.scalar(
        select(func.coalesce(func.sum(DeepAnalysisItem.comments_analyzed_count), 0)).where(
            DeepAnalysisItem.deep_analysis_id == analysis.id
        )
    )
    result = DeepAnalysisOut.from_model(analysis)
    result.comments_analyzed_count = comments_analyzed_count
    return result
