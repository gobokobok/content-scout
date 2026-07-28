import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import AnalysisRun, DeepAnalysis, DeepAnalysisItem, Project, UsageEvent
from src.models.workspace import WorkspaceMember

router = APIRouter(tags=["usage"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


class KindTotal(BaseModel):
    kind: str
    quantity: int
    cost_usd: Decimal


class UsageOut(BaseModel):
    from_: datetime
    to: datetime
    total_cost_usd: Decimal
    by_kind: list[KindTotal]


class RunSummaryOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    project_name: str
    kind: str
    status: str
    duration_days: int | None
    item_limit: int | None
    progress_items: int
    tokens_charged: int
    total_input_tokens: int
    total_output_tokens: int
    comments_analyzed_count: int | None = None
    created_at: datetime
    finished_at: datetime | None


@router.get("/me/usage", response_model=UsageOut)
async def get_my_usage(
    user: CurrentUser,
    session: SessionDep,
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
) -> UsageOut:
    rows = await session.execute(
        select(
            UsageEvent.kind,
            func.sum(UsageEvent.quantity).label("qty"),
            func.sum(UsageEvent.quantity * UsageEvent.unit_cost_usd).label("cost"),
        )
        .where(UsageEvent.user_id == user.id)
        .where(UsageEvent.created_at >= from_)
        .where(UsageEvent.created_at < to)
        .group_by(UsageEvent.kind)
    )
    by_kind = [
        KindTotal(kind=kind, quantity=int(qty or 0), cost_usd=cost or Decimal("0"))
        for kind, qty, cost in rows
    ]
    total_cost_usd = sum((k.cost_usd for k in by_kind), Decimal("0"))
    return UsageOut(from_=from_, to=to, total_cost_usd=total_cost_usd, by_kind=by_kind)


@router.get("/me/runs", response_model=list[RunSummaryOut])
async def get_my_runs(
    user: CurrentUser,
    session: SessionDep,
    from_: datetime = Query(alias="from"),
    to: datetime = Query(),
) -> list[RunSummaryOut]:
    run_rows = await session.execute(
        select(AnalysisRun, Project.name.label("project_name"))
        .join(Project, AnalysisRun.project_id == Project.id)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Project.workspace_id)
        .where(WorkspaceMember.user_id == user.id)
        .where(AnalysisRun.created_at >= from_)
        .where(AnalysisRun.created_at < to)
    )
    entries = [
        RunSummaryOut(
            id=run.id,
            project_id=run.project_id,
            project_name=project_name,
            kind="run",
            status=run.status,
            duration_days=run.duration_days,
            item_limit=run.item_limit,
            progress_items=run.progress_items,
            tokens_charged=run.progress_items,
            total_input_tokens=run.total_input_tokens,
            total_output_tokens=run.total_output_tokens,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
        for run, project_name in run_rows
    ]

    # E17: deep-analysis token charges must appear in the same ledger view — they're deducted
    # from the same token_balance but weren't previously surfaced anywhere in this list.
    # progress_items comes from the underlying review run: a deep analysis re-analyzes the
    # same publications it was chained from, it does not scrape its own set.
    deep_analysis_rows = (
        await session.execute(
            select(
                DeepAnalysis,
                Project.name.label("project_name"),
                AnalysisRun.progress_items.label("run_progress_items"),
            )
            .join(Project, DeepAnalysis.project_id == Project.id)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Project.workspace_id)
            .join(AnalysisRun, AnalysisRun.id == DeepAnalysis.run_id)
            .where(WorkspaceMember.user_id == user.id)
            .where(DeepAnalysis.created_at >= from_)
            .where(DeepAnalysis.created_at < to)
        )
    ).all()

    comments_by_analysis: dict[uuid.UUID, int] = {}
    analysis_ids = [analysis.id for analysis, _, _ in deep_analysis_rows]
    if analysis_ids:
        comment_rows = await session.execute(
            select(
                DeepAnalysisItem.deep_analysis_id,
                func.coalesce(func.sum(DeepAnalysisItem.comments_analyzed_count), 0),
            )
            .where(DeepAnalysisItem.deep_analysis_id.in_(analysis_ids))
            .group_by(DeepAnalysisItem.deep_analysis_id)
        )
        comments_by_analysis = {aid: int(total) for aid, total in comment_rows}

    entries.extend(
        RunSummaryOut(
            id=analysis.id,
            project_id=analysis.project_id,
            project_name=project_name,
            kind="deep_analysis",
            status=analysis.status,
            duration_days=None,
            item_limit=None,
            progress_items=run_progress_items,
            tokens_charged=analysis.tokens_charged,
            total_input_tokens=0,
            total_output_tokens=0,
            comments_analyzed_count=comments_by_analysis.get(analysis.id, 0),
            created_at=analysis.created_at,
            finished_at=analysis.completed_at,
        )
        for analysis, project_name, run_progress_items in deep_analysis_rows
    )

    entries.sort(key=lambda e: e.created_at, reverse=True)
    return entries
