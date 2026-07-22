import io
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.items import ContentItemOut, SortField, _get_run
from src.api.shortlist import ShortlistItemOut
from src.auth.dependency import UNAUTHORIZED, CurrentUser, OptionalUser
from src.auth.tokens import create_download_token, decode_download_token
from src.config import get_settings
from src.db import get_session
from src.models import Account, AnalysisRun, ContentItem, Project, RunStatus, ShortlistItem, User
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
from src.services.xlsx_export import build_shortlist_xlsx, build_xlsx, safe_filename_part

router = APIRouter(tags=["export"])

_PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _run_export_resource(run_id: uuid.UUID) -> str:
    return f"run_export:{run_id}"


def _shortlist_export_resource(project_id: uuid.UUID) -> str:
    return f"shortlist_export:{project_id}"


def _project_items_export_resource(project_id: uuid.UUID) -> str:
    return f"project_items_export:{project_id}"


async def _resolve_export_user(
    session: AsyncSession, user: User | None, dl_token: str | None, resource: str
) -> User:
    """Authenticated via the normal Authorization header, or (when absent) a short-lived
    download token scoped to this exact resource — see auth/tokens.py:create_download_token.
    Telegram's native `downloadFile` fetches the URL itself with no custom headers, so the
    header path alone can't cover it."""
    if user is not None:
        return user
    if dl_token:
        token_user_id = decode_download_token(dl_token, resource=resource)
        if token_user_id is not None:
            token_user = await session.get(User, token_user_id)
            if token_user is not None:
                return token_user
    raise UNAUTHORIZED


@router.post("/runs/{run_id}/export-token")
async def create_run_export_token(
    run_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> dict[str, str]:
    await _get_run(session, user, run_id)  # ownership check
    token = create_download_token(user.id, resource=_run_export_resource(run_id))
    return {"token": token}


@router.get("/runs/{run_id}/export.xlsx")
async def export_run_xlsx(
    run_id: uuid.UUID,
    user: OptionalUser,
    session: SessionDep,
    dl_token: str | None = None,
    sort: SortField = "views_per_day",
    order: Literal["asc", "desc"] = "desc",
) -> StreamingResponse:
    resolved_user = await _resolve_export_user(
        session, user, dl_token, _run_export_resource(run_id)
    )
    run = await _get_run(session, resolved_user, run_id)
    settings = get_settings()

    project = await session.get(Project, run.project_id)
    project_slug = safe_filename_part(project.name if project else "project")

    days_expr = days_since_published_expr()
    views_per_day = views_per_day_expr()
    likes_per_day = likes_per_day_expr()
    engagement_rate = engagement_rate_expr()
    virality_subq = virality_baseline_subquery(ContentItem.run_id == run_id)

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
        )
        .join(Account, ContentItem.account_id == Account.id)
        .join(
            virality_subq,
            (virality_subq.c.account_id == ContentItem.account_id)
            & (virality_subq.c.run_id == ContentItem.run_id),
        )
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


@router.post("/projects/{project_id}/shortlist/export-token")
async def create_shortlist_export_token(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> dict[str, str]:
    try:
        await get_owned_project(session, user, project_id)  # ownership check
    except ProjectNotFoundError:
        raise _PROJECT_NOT_FOUND from None
    token = create_download_token(user.id, resource=_shortlist_export_resource(project_id))
    return {"token": token}


@router.get("/projects/{project_id}/shortlist/export.xlsx")
async def export_shortlist_xlsx(
    project_id: uuid.UUID,
    user: OptionalUser,
    session: SessionDep,
    dl_token: str | None = None,
) -> StreamingResponse:
    resolved_user = await _resolve_export_user(
        session, user, dl_token, _shortlist_export_resource(project_id)
    )
    try:
        project = await get_owned_project(session, resolved_user, project_id)
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


@router.post("/projects/{project_id}/items/export-token")
async def create_project_items_export_token(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> dict[str, str]:
    try:
        await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise _PROJECT_NOT_FOUND from None
    token = create_download_token(user.id, resource=_project_items_export_resource(project_id))
    return {"token": token}


@router.get("/projects/{project_id}/items/export.xlsx")
async def export_project_items_xlsx(
    project_id: uuid.UUID,
    user: OptionalUser,
    session: SessionDep,
    dl_token: str | None = None,
    run_id: uuid.UUID | None = None,
    starred_only: bool = False,
    sort: SortField = "likes_per_day",
    order: Literal["asc", "desc"] = "desc",
) -> StreamingResponse:
    """Mirrors GET /projects/{project_id}/items (mobile results view) but returns every
    matching item as .xlsx rather than one paginated page — the export always reflects exactly
    what's currently filtered/shown on screen (run filter + starred-only), never the full
    unfiltered project."""
    resolved_user = await _resolve_export_user(
        session, user, dl_token, _project_items_export_resource(project_id)
    )
    try:
        project = await get_owned_project(session, resolved_user, project_id)
    except ProjectNotFoundError:
        raise _PROJECT_NOT_FOUND from None
    settings = get_settings()
    project_slug = safe_filename_part(project.name)

    days_expr = days_since_published_expr()
    views_per_day = views_per_day_expr()
    likes_per_day = likes_per_day_expr()
    engagement_rate = engagement_rate_expr()

    done_runs_in_project = select(AnalysisRun.id).where(
        AnalysisRun.project_id == project_id, AnalysisRun.status == RunStatus.done
    )
    item_scope: Any = ContentItem.run_id.in_(done_runs_in_project)
    if run_id is not None:
        item_scope = and_(item_scope, ContentItem.run_id == run_id)

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
        )
        .join(Account, ContentItem.account_id == Account.id)
        .join(
            virality_subq,
            (virality_subq.c.account_id == ContentItem.account_id)
            & (virality_subq.c.run_id == ContentItem.run_id),
        )
        .where(*where_clauses)
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
        ) in rows
    ]

    xlsx_bytes = build_xlsx(items, project_slug, datetime.now(UTC))
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"content-scout_{project_slug}_{today}.xlsx"
    encoded_filename = quote(filename)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
