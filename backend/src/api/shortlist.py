import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import Account, AnalysisRun, ContentItem, ShortlistItem
from src.services.projects import ProjectNotFoundError, get_owned_project

router = APIRouter(tags=["shortlist"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)
SHORTLIST_ITEM_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "code": "shortlist_item_not_found",
        "message_ru": "Публикация не найдена в шорт-листе.",
    },  # noqa: E501
)


async def _get_project(session: AsyncSession, user: CurrentUser, project_id: uuid.UUID):
    try:
        return await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None


class ShortlistAddIn(BaseModel):
    item_ids: list[uuid.UUID]


class ShortlistItemOut(BaseModel):
    id: uuid.UUID
    content_item_id: uuid.UUID
    account_handle: str
    published_at: datetime
    type: str
    title: str | None
    url: str
    summary: str | None
    likes: int | None
    views: int | None
    added_at: datetime


@router.post(
    "/projects/{project_id}/shortlist/items",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def add_to_shortlist(
    project_id: uuid.UUID,
    body: ShortlistAddIn,
    user: CurrentUser,
    session: SessionDep,
) -> None:
    await _get_project(session, user, project_id)

    for item_id in body.item_ids:
        # Already active — skip (idempotent)
        already_active = await session.scalar(
            select(ShortlistItem).where(
                ShortlistItem.project_id == project_id,
                ShortlistItem.content_item_id == item_id,
                ShortlistItem.removed_at.is_(None),
            )
        )
        if already_active:
            continue

        # Restore a previously removed entry
        removed = await session.scalar(
            select(ShortlistItem)
            .where(
                ShortlistItem.project_id == project_id,
                ShortlistItem.content_item_id == item_id,
                ShortlistItem.removed_at.isnot(None),
            )
            .order_by(ShortlistItem.added_at.desc())
        )
        if removed:
            removed.removed_at = None
            removed.added_by = user.id
            removed.added_at = datetime.now(UTC)
            continue

        # Verify the content item belongs to a run in this project
        item = await session.scalar(
            select(ContentItem)
            .join(AnalysisRun, ContentItem.run_id == AnalysisRun.id)
            .where(ContentItem.id == item_id, AnalysisRun.project_id == project_id)
        )
        if not item:
            continue

        session.add(
            ShortlistItem(
                project_id=project_id,
                content_item_id=item_id,
                added_by=user.id,
            )
        )

    await session.commit()


@router.delete(
    "/projects/{project_id}/shortlist/items/{content_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_from_shortlist(
    project_id: uuid.UUID,
    content_item_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
) -> None:
    await _get_project(session, user, project_id)

    sl_item = await session.scalar(
        select(ShortlistItem).where(
            ShortlistItem.project_id == project_id,
            ShortlistItem.content_item_id == content_item_id,
            ShortlistItem.removed_at.is_(None),
        )
    )
    if not sl_item:
        raise SHORTLIST_ITEM_NOT_FOUND

    sl_item.removed_at = datetime.now(UTC)
    await session.commit()


@router.get("/projects/{project_id}/shortlist/items", response_model=list[ShortlistItemOut])
async def list_shortlist(
    project_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
) -> list[ShortlistItemOut]:
    await _get_project(session, user, project_id)

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

    return [
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
