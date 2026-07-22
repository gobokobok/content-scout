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
from src.models import AnalysisRun, Project, UsageEvent
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
    status: str
    duration_days: int | None
    item_limit: int | None
    progress_items: int
    total_input_tokens: int
    total_output_tokens: int
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
    rows = await session.execute(
        select(AnalysisRun, Project.name.label("project_name"))
        .join(Project, AnalysisRun.project_id == Project.id)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Project.workspace_id)
        .where(WorkspaceMember.user_id == user.id)
        .where(AnalysisRun.created_at >= from_)
        .where(AnalysisRun.created_at < to)
        .order_by(AnalysisRun.created_at.desc())
    )
    return [
        RunSummaryOut(
            id=run.id,
            project_id=run.project_id,
            project_name=project_name,
            status=run.status,
            duration_days=run.duration_days,
            item_limit=run.item_limit,
            progress_items=run.progress_items,
            total_input_tokens=run.total_input_tokens,
            total_output_tokens=run.total_output_tokens,
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
        for run, project_name in rows
    ]
