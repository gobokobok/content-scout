import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.db import get_session
from src.models import Account, AnalysisRun, ContentItem, RunStatus, ShortlistItem
from src.services.metrics import (
    bucket_virality,
    days_since_published_expr,
    engagement_rate_expr,
    likes_per_day_expr,
    views_per_day_expr,
    virality_baseline_subquery,
    virality_ratio,
    virality_ratio_expr,
)
from src.services.projects import ProjectNotFoundError, get_owned_project

router = APIRouter(tags=["items"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

RUN_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "run_not_found", "message_ru": "Запуск не найден."},
)

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
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
    "comments",
    "days_since_published",
    "views_per_day",
    "likes_per_day",
    "engagement_rate",
    "virality",
]


class ContentItemOut(BaseModel):
    id: uuid.UUID
    account_handle: str
    followers_count: int | None = None
    published_at: datetime
    type: str
    title: str | None
    url: str
    summary: str | None
    likes: int | None
    views: int | None
    comments: int | None
    days_since_published: float
    views_per_day: float | None
    likes_per_day: float | None
    engagement_rate: float | None = None
    virality: Literal["high", "medium", "low"] | None = None
    in_shortlist: bool = False


class ItemsPageOut(BaseModel):
    items: list[ContentItemOut]
    total: int
    page: int
    page_size: int


class TopViralityOut(BaseModel):
    items: list[ContentItemOut]


TOP_VIRALITY_DEFAULT_LIMIT = 5


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
    run = await _get_run(session, user, run_id)
    settings = get_settings()

    days_expr = days_since_published_expr()
    views_per_day = views_per_day_expr()
    likes_per_day = likes_per_day_expr()
    engagement_rate = engagement_rate_expr()
    virality_subq = virality_baseline_subquery(ContentItem.run_id == run_id)

    shortlist_exists = (
        select(ShortlistItem.id)
        .where(
            ShortlistItem.content_item_id == ContentItem.id,
            ShortlistItem.project_id == run.project_id,
            ShortlistItem.removed_at.is_(None),
        )
        .correlate(ContentItem)
        .exists()
    )

    sort_columns: dict[SortField, Any] = {
        "account": Account.handle,
        "published_at": ContentItem.published_at,
        "type": ContentItem.type,
        "title": ContentItem.title,
        "url": ContentItem.url,
        "summary": ContentItem.summary,
        "likes": ContentItem.likes,
        "views": ContentItem.views,
        "comments": ContentItem.comments,
        "days_since_published": days_expr,
        "views_per_day": views_per_day,
        "likes_per_day": likes_per_day,
        "engagement_rate": engagement_rate,
        "virality": virality_ratio_expr(
            virality_subq.c.median_engagement,
            virality_subq.c.median_views,
            virality_subq.c.item_count,
            settings,
        ),
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
            Account.followers_count,
            days_expr.label("days_since_published"),
            views_per_day.label("views_per_day"),
            likes_per_day.label("likes_per_day"),
            engagement_rate.label("engagement_rate"),
            virality_subq.c.median_engagement,
            virality_subq.c.median_views,
            virality_subq.c.item_count,
            shortlist_exists.label("in_shortlist"),
        )
        .join(Account, ContentItem.account_id == Account.id)
        .join(
            virality_subq,
            (virality_subq.c.account_id == ContentItem.account_id)
            & (virality_subq.c.run_id == ContentItem.run_id),
        )
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
            followers_count=followers_count,
            published_at=item.published_at,
            type=item.type.value,
            title=item.title,
            url=item.url,
            summary=item.summary,
            likes=item.likes,
            views=item.views,
            comments=item.comments,
            days_since_published=days,
            views_per_day=vpd,
            likes_per_day=lpd,
            engagement_rate=eng_rate,
            virality=bucket_virality(
                virality_ratio(
                    likes=item.likes,
                    comments=item.comments,
                    views=item.views,
                    median_engagement=median_engagement,
                    median_views=median_views,
                ),
                item_count,
                settings,
            ),
            in_shortlist=bool(in_sl),
        )
        for (
            item,
            handle,
            followers_count,
            days,
            vpd,
            lpd,
            eng_rate,
            median_engagement,
            median_views,
            item_count,
            in_sl,
        ) in rows
    ]

    return ItemsPageOut(items=items, total=total or 0, page=page, page_size=PAGE_SIZE)


@router.get("/runs/{run_id}/top-virality", response_model=TopViralityOut)
async def list_top_virality_items(
    run_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=20)] = TOP_VIRALITY_DEFAULT_LIMIT,
) -> TopViralityOut:
    """E15-S2: the N most viral posts of a run, for the run-summary view (E15-S3).

    Purely virality_ratio_expr sorted desc with a limit — items with insufficient sample
    size (per virality_min_items) resolve to a NULL ratio and are excluded, same guard as
    the results table's virality badge (services/metrics.py:bucket_virality).
    """
    run = await _get_run(session, user, run_id)
    settings = get_settings()

    days_expr = days_since_published_expr()
    views_per_day = views_per_day_expr()
    likes_per_day = likes_per_day_expr()
    engagement_rate = engagement_rate_expr()
    virality_subq = virality_baseline_subquery(ContentItem.run_id == run_id)
    virality_expr = virality_ratio_expr(
        virality_subq.c.median_engagement,
        virality_subq.c.median_views,
        virality_subq.c.item_count,
        settings,
    )

    shortlist_exists = (
        select(ShortlistItem.id)
        .where(
            ShortlistItem.content_item_id == ContentItem.id,
            ShortlistItem.project_id == run.project_id,
            ShortlistItem.removed_at.is_(None),
        )
        .correlate(ContentItem)
        .exists()
    )

    stmt = (
        select(
            ContentItem,
            Account.handle,
            Account.followers_count,
            days_expr.label("days_since_published"),
            views_per_day.label("views_per_day"),
            likes_per_day.label("likes_per_day"),
            engagement_rate.label("engagement_rate"),
            virality_subq.c.median_engagement,
            virality_subq.c.median_views,
            virality_subq.c.item_count,
            shortlist_exists.label("in_shortlist"),
        )
        .join(Account, ContentItem.account_id == Account.id)
        .join(
            virality_subq,
            (virality_subq.c.account_id == ContentItem.account_id)
            & (virality_subq.c.run_id == ContentItem.run_id),
        )
        .where(ContentItem.run_id == run_id, virality_expr.isnot(None))
        .order_by(virality_expr.desc())
        .limit(limit)
    )
    rows = await session.execute(stmt)

    items = [
        ContentItemOut(
            id=item.id,
            account_handle=handle,
            followers_count=followers_count,
            published_at=item.published_at,
            type=item.type.value,
            title=item.title,
            url=item.url,
            summary=item.summary,
            likes=item.likes,
            views=item.views,
            comments=item.comments,
            days_since_published=days,
            views_per_day=vpd,
            likes_per_day=lpd,
            engagement_rate=eng_rate,
            virality=bucket_virality(
                virality_ratio(
                    likes=item.likes,
                    comments=item.comments,
                    views=item.views,
                    median_engagement=median_engagement,
                    median_views=median_views,
                ),
                item_count,
                settings,
            ),
            in_shortlist=bool(in_sl),
        )
        for (
            item,
            handle,
            followers_count,
            days,
            vpd,
            lpd,
            eng_rate,
            median_engagement,
            median_views,
            item_count,
            in_sl,
        ) in rows
    ]

    return TopViralityOut(items=items)


@router.get("/projects/{project_id}/items", response_model=ItemsPageOut)
async def list_project_items(
    project_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    run_id: uuid.UUID | None = None,
    starred_only: bool = False,
    sort: SortField = "likes_per_day",
    order: Literal["asc", "desc"] = "desc",
    page: Annotated[int, Query(ge=1)] = 1,
) -> ItemsPageOut:
    """Powers the mobile results view's run filter: run_id omitted (or null) means "all runs" —
    items pooled across every completed run in the project, each still scored against its own
    run's virality baseline (see virality_baseline_subquery)."""
    try:
        await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None
    settings = get_settings()

    days_expr = days_since_published_expr()
    views_per_day = views_per_day_expr()
    likes_per_day = likes_per_day_expr()
    engagement_rate = engagement_rate_expr()

    runs_in_project = select(AnalysisRun.id).where(AnalysisRun.project_id == project_id)
    done_runs_in_project = runs_in_project.where(AnalysisRun.status == RunStatus.done)

    if run_id is not None:
        # E15-S4/D43: viewing one specific run's own Publications tab shows whatever it
        # already committed regardless of status (partial results on a failed/exhausted run)
        # — still scoped to this project's own runs (ownership already gated by
        # get_owned_project above), just without the "all runs" aggregate view's done-only
        # requirement below.
        item_scope: Any = and_(
            ContentItem.run_id == run_id, ContentItem.run_id.in_(runs_in_project)
        )
    else:
        item_scope = ContentItem.run_id.in_(done_runs_in_project)

    where_clauses: list[Any] = [item_scope]
    virality_subq = virality_baseline_subquery(item_scope)

    shortlist_exists = (
        select(ShortlistItem.id)
        .where(
            ShortlistItem.content_item_id == ContentItem.id,
            ShortlistItem.project_id == project_id,
            ShortlistItem.removed_at.is_(None),
        )
        .correlate(ContentItem)
        .exists()
    )
    if starred_only:
        where_clauses.append(shortlist_exists)

    sort_columns: dict[SortField, Any] = {
        "account": Account.handle,
        "published_at": ContentItem.published_at,
        "type": ContentItem.type,
        "title": ContentItem.title,
        "url": ContentItem.url,
        "summary": ContentItem.summary,
        "likes": ContentItem.likes,
        "views": ContentItem.views,
        "comments": ContentItem.comments,
        "days_since_published": days_expr,
        "views_per_day": views_per_day,
        "likes_per_day": likes_per_day,
        "engagement_rate": engagement_rate,
        "virality": virality_ratio_expr(
            virality_subq.c.median_engagement,
            virality_subq.c.median_views,
            virality_subq.c.item_count,
            settings,
        ),
    }
    sort_col = sort_columns[sort]
    order_by = sort_col.asc().nulls_last() if order == "asc" else sort_col.desc().nulls_last()

    total = await session.scalar(
        select(func.count()).select_from(ContentItem).where(*where_clauses)
    )

    stmt = (
        select(
            ContentItem,
            Account.handle,
            Account.followers_count,
            days_expr.label("days_since_published"),
            views_per_day.label("views_per_day"),
            likes_per_day.label("likes_per_day"),
            engagement_rate.label("engagement_rate"),
            virality_subq.c.median_engagement,
            virality_subq.c.median_views,
            virality_subq.c.item_count,
            shortlist_exists.label("in_shortlist"),
        )
        .join(Account, ContentItem.account_id == Account.id)
        .join(
            virality_subq,
            (virality_subq.c.account_id == ContentItem.account_id)
            & (virality_subq.c.run_id == ContentItem.run_id),
        )
        .where(*where_clauses)
        .order_by(order_by)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )
    rows = await session.execute(stmt)

    items = [
        ContentItemOut(
            id=item.id,
            account_handle=handle,
            followers_count=followers_count,
            published_at=item.published_at,
            type=item.type.value,
            title=item.title,
            url=item.url,
            summary=item.summary,
            likes=item.likes,
            views=item.views,
            comments=item.comments,
            days_since_published=days,
            views_per_day=vpd,
            likes_per_day=lpd,
            engagement_rate=eng_rate,
            virality=bucket_virality(
                virality_ratio(
                    likes=item.likes,
                    comments=item.comments,
                    views=item.views,
                    median_engagement=median_engagement,
                    median_views=median_views,
                ),
                item_count,
                settings,
            ),
            in_shortlist=bool(in_sl),
        )
        for (
            item,
            handle,
            followers_count,
            days,
            vpd,
            lpd,
            eng_rate,
            median_engagement,
            median_views,
            item_count,
            in_sl,
        ) in rows
    ]

    return ItemsPageOut(items=items, total=total or 0, page=page, page_size=PAGE_SIZE)
