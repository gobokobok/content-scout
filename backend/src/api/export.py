import io
import uuid
from typing import Annotated, Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.items import ContentItemOut, SortField, _get_run
from src.api.shortlist import ShortlistItemOut
from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.db import get_session
from src.models import Account, ContentItem, Project, ShortlistItem
from src.services.metrics import (
    account_item_count_expr,
    bucket_virality,
    days_since_published_expr,
    engagement_rate_expr,
    likes_per_day_expr,
    views_per_day_expr,
    virality_ratio_expr,
)
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.xlsx_export import build_shortlist_xlsx, build_xlsx, safe_filename_part

router = APIRouter(tags=["export"])

_PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/runs/{run_id}/export.xlsx")
async def export_run_xlsx(
    run_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    sort: SortField = "views_per_day",
    order: Literal["asc", "desc"] = "desc",
) -> StreamingResponse:
    run = await _get_run(session, user, run_id)
    settings = get_settings()

    project = await session.get(Project, run.project_id)
    project_slug = safe_filename_part(project.name if project else "project")

    days_expr = days_since_published_expr()
    views_per_day = views_per_day_expr()
    likes_per_day = likes_per_day_expr()
    engagement_rate = engagement_rate_expr()
    virality_ratio = virality_ratio_expr()
    account_item_count = account_item_count_expr()

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
    }
    sort_col = sort_columns[sort]
    order_by = sort_col.asc().nulls_last() if order == "asc" else sort_col.desc().nulls_last()

    stmt = (
        select(
            ContentItem,
            Account.handle,
            Account.followers_count,
            days_expr.label("days_since_published"),
            views_per_day.label("views_per_day"),
            likes_per_day.label("likes_per_day"),
            engagement_rate.label("engagement_rate"),
            virality_ratio.label("virality_ratio"),
            account_item_count.label("account_item_count"),
        )
        .join(Account, ContentItem.account_id == Account.id)
        .where(ContentItem.run_id == run_id)
        .order_by(order_by)
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
            virality=bucket_virality(ratio, item_count, settings),
        )
        for (
            item,
            handle,
            followers_count,
            days,
            vpd,
            lpd,
            eng_rate,
            ratio,
            item_count,
        ) in rows
    ]

    xlsx_bytes = build_xlsx(items, project_slug, run.created_at)
    run_date = run.created_at.strftime("%Y-%m-%d")
    filename = f"content-scout_{project_slug}_{run_date}.xlsx"

    encoded_filename = quote(filename)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@router.get("/projects/{project_id}/shortlist/export.xlsx")
async def export_shortlist_xlsx(
    project_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
) -> StreamingResponse:
    try:
        project = await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise _PROJECT_NOT_FOUND from None
    project_slug = safe_filename_part(project.name)

    rows = await session.execute(
        select(ShortlistItem, ContentItem, Account.handle)
        .join(ContentItem, ShortlistItem.content_item_id == ContentItem.id)
        .join(Account, ContentItem.account_id == Account.id)
        .where(
            ShortlistItem.project_id == project_id,
            ShortlistItem.removed_at.is_(None),
        )
        .order_by(ShortlistItem.added_at.desc())
    )

    items = [
        ShortlistItemOut(
            id=sl.id,
            content_item_id=sl.content_item_id,
            account_handle=handle,
            published_at=item.published_at,
            type=item.type.value,
            title=item.title,
            url=item.url,
            summary=item.summary,
            likes=item.likes,
            views=item.views,
            added_at=sl.added_at,
        )
        for sl, item, handle in rows
    ]

    xlsx_bytes = build_shortlist_xlsx(items, project_slug)
    filename = f"content-scout_{project_slug}_shortlist.xlsx"
    encoded_filename = quote(filename)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
