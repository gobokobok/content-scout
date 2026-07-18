import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import Account, AnalysisRun, ContentItem
from src.services.metrics import (
    days_since_published_expr,
    likes_per_day_expr,
    views_per_day_expr,
)
from src.services.projects import ProjectNotFoundError, get_owned_project

router = APIRouter(tags=["items"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

RUN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "run_not_found", "message_ru": "Запуск не найден."},
)

PAGE_SIZE = 50

SortField = Literal[
    "account",
    "published_at",
    "type",
    "title",
    "url",
    "summary",
    "likes",
    "views",
    "days_since_published",
    "views_per_day",
    "likes_per_day",
]


class ContentItemOut(BaseModel):
    id: uuid.UUID
    account_handle: str
    published_at: datetime
    type: str
    title: str | None
    url: str
    summary: str | None
    likes: int | None
    views: int | None
    days_since_published: float
    views_per_day: float | None
    likes_per_day: float | None


class ItemsPageOut(BaseModel):
    items: list[ContentItemOut]
    total: int
    page: int
    page_size: int


async def _get_run(session: AsyncSession, user: CurrentUser, run_id: uuid.UUID) -> AnalysisRun:
    run = await session.get(AnalysisRun, run_id)
    if run is None:
        raise RUN_NOT_FOUND
    try:
        await get_owned_project(session, user, run.project_id)
    except ProjectNotFoundError:
        raise RUN_NOT_FOUND from None
    return run


@router.get("/runs/{run_id}/items", response_model=ItemsPageOut)
async def list_run_items(
    run_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    sort: SortField = "views_per_day",
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
) -> ItemsPageOut:
    await _get_run(session, user, run_id)

    days_expr = days_since_published_expr()
    views_per_day = views_per_day_expr()
    likes_per_day = likes_per_day_expr()

    sort_columns: dict[SortField, Any] = {
        "account": Account.handle,
        "published_at": ContentItem.published_at,
        "type": ContentItem.type,
        "title": ContentItem.title,
        "url": ContentItem.url,
        "summary": ContentItem.summary,
        "likes": ContentItem.likes,
        "views": ContentItem.views,
        "days_since_published": days_expr,
        "views_per_day": views_per_day,
        "likes_per_day": likes_per_day,
    }
    sort_col = sort_columns[sort]
    order_by = sort_col.asc().nulls_last() if order == "asc" else sort_col.desc().nulls_last()

    total = await session.scalar(
        select(func.count()).select_from(ContentItem).where(ContentItem.run_id == run_id)
    )

    stmt = (
        select(
            ContentItem,
            Account.handle,
            days_expr.label("days_since_published"),
            views_per_day.label("views_per_day"),
            likes_per_day.label("likes_per_day"),
        )
        .join(Account, ContentItem.account_id == Account.id)
        .where(ContentItem.run_id == run_id)
        .order_by(order_by)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )
    rows = await session.execute(stmt)

    items = [
        ContentItemOut(
            id=item.id,
            account_handle=handle,
            published_at=item.published_at,
            type=item.type.value,
            title=item.title,
            url=item.url,
            summary=item.summary,
            likes=item.likes,
            views=item.views,
            days_since_published=days,
            views_per_day=vpd,
            likes_per_day=lpd,
        )
        for item, handle, days, vpd, lpd in rows
    ]

    return ItemsPageOut(items=items, total=total or 0, page=page, page_size=PAGE_SIZE)
