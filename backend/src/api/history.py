import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import Account, ContentItem, ShortlistItem
from src.services.projects import ProjectNotFoundError, get_owned_project

router = APIRouter(tags=["history"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)


async def _get_project(session: AsyncSession, user: CurrentUser, project_id: uuid.UUID):
    try:
        return await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None


class ShortlistHistoryItemOut(BaseModel):
    id: uuid.UUID
    content_item_id: uuid.UUID
    account_handle: str
    type: str
    title: str | None
    url: str
    added_at: datetime
    removed_at: datetime | None


@router.get(
    "/projects/{project_id}/history/shortlist",
    response_model=list[ShortlistHistoryItemOut],
)
async def list_shortlist_history(
    project_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
) -> list[ShortlistHistoryItemOut]:
    await _get_project(session, user, project_id)

    rows = await session.execute(
        select(ShortlistItem, ContentItem.type, ContentItem.title, ContentItem.url, Account.handle)
        .join(ContentItem, ShortlistItem.content_item_id == ContentItem.id)
        .join(Account, ContentItem.account_id == Account.id)
        .where(ShortlistItem.project_id == project_id)
        .order_by(ShortlistItem.added_at.desc())
    )

    return [
        ShortlistHistoryItemOut(
            id=sl.id,
            content_item_id=sl.content_item_id,
            account_handle=handle,
            type=ct.value,
            title=title,
            url=url,
            added_at=sl.added_at,
            removed_at=sl.removed_at,
        )
        for sl, ct, title, url, handle in rows
    ]
