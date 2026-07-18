import io
import uuid
from typing import Annotated, Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.items import ContentItemOut, SortField, _get_run
from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import Account, ContentItem, Project
from src.services.metrics import days_since_published_expr, likes_per_day_expr, views_per_day_expr
from src.services.xlsx_export import build_xlsx, safe_filename_part

router = APIRouter(tags=["export"])

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

    project = await session.get(Project, run.project_id)
    project_slug = safe_filename_part(project.name if project else "project")

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

    xlsx_bytes = build_xlsx(items, project_slug, run.created_at)
    run_date = run.created_at.strftime("%Y-%m-%d")
    filename = f"content-scout_{project_slug}_{run_date}.xlsx"

    encoded_filename = quote(filename)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
