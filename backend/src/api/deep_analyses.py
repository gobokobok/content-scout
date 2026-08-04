import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.db import get_session
from src.models import DeepAnalysis, DeepAnalysisItem
from src.services.deep_analysis import estimate_deep_analysis_tokens
from src.services.projects import ProjectNotFoundError, get_owned_project

router = APIRouter(tags=["deep-analyses"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)
DEEP_ANALYSIS_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "deep_analysis_not_found", "message_ru": "Анализ не найден."},
)


class DeepAnalysisEstimateIn(BaseModel):
    """D50: a pre-confirm token estimate for the standalone Analysis creation flow — no run_id
    anymore, since Analysis no longer attaches to an existing Review run (D40). Mirrors the
    scope shape of RunRequestIn's own deep_analysis fields."""

    analysis_mode: Literal["account", "post"]
    duration_days: int | None = Field(default=None, ge=1, le=7)
    item_limit: int | None = Field(default=None, ge=1, le=50)
    comments_limit: int | None = Field(default=None, ge=1, le=50)


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


@router.post(
    "/projects/{project_id}/deep-analyses/estimate", response_model=DeepAnalysisEstimateOut
)
async def estimate_deep_analysis(
    project_id: uuid.UUID, body: DeepAnalysisEstimateIn, user: CurrentUser, session: SessionDep
) -> DeepAnalysisEstimateOut:
    """Read-only token preview for the standalone Analysis creation flow (D49/D50) — a ceiling
    estimate before any scrape has happened, same spirit as the old run_id-based version this
    replaces but computed from the requested scope directly instead of an already-scraped
    ContentItem count."""
    await _get_project(session, user, project_id)
    tokens = estimate_deep_analysis_tokens(
        get_settings(),
        analysis_mode=body.analysis_mode,
        duration_days=body.duration_days,
        item_limit=body.item_limit,
        comments_limit=body.comments_limit,
    )
    return DeepAnalysisEstimateOut(tokens=tokens)


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
