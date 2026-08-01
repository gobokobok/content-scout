import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.db import get_session
from src.models import MAX_ACCOUNTS_PER_LIST, Account, AccountList, PlatformSlug
from src.services.projects import ProjectNotFoundError, get_owned_project
from src.services.queue import enqueue_profile_fetch
from src.services.url_normalizer import InvalidAccountUrlError, normalize_instagram_input

router = APIRouter(prefix="/projects/{project_id}/accounts", tags=["accounts"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

PROJECT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "project_not_found", "message_ru": "Проект не найден."},
)
ACCOUNT_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "account_not_found", "message_ru": "Аккаунт не найден."},
)


class AccountOut(BaseModel):
    id: uuid.UUID
    handle: str
    normalized_url: str
    status: str
    created_at: datetime
    display_name: str | None
    followers_count: int | None
    avatar_url: str | None
    profile_updated_at: datetime | None

    @classmethod
    def from_model(cls, account: Account) -> "AccountOut":
        return cls(
            id=account.id,
            handle=account.handle,
            normalized_url=account.normalized_url,
            status=account.status.value,
            created_at=account.created_at,
            display_name=account.display_name,
            followers_count=account.followers_count,
            avatar_url=account.avatar_url,
            profile_updated_at=account.followers_updated_at,
        )


class AddAccountsIn(BaseModel):
    entries: list[str] = Field(min_length=1, max_length=MAX_ACCOUNTS_PER_LIST)


class AddAccountError(BaseModel):
    input: str
    message_ru: str


class AddAccountsOut(BaseModel):
    added: list[AccountOut]
    errors: list[AddAccountError]
    total: int


async def _get_project(session: AsyncSession, user: CurrentUser, project_id: uuid.UUID):
    try:
        return await get_owned_project(session, user, project_id)
    except ProjectNotFoundError:
        raise PROJECT_NOT_FOUND from None


async def _get_or_create_ig_list(session: AsyncSession, project_id: uuid.UUID) -> AccountList:
    account_list = await session.scalar(
        select(AccountList).where(
            AccountList.project_id == project_id, AccountList.platform == PlatformSlug.instagram
        )
    )
    if account_list is None:
        account_list = AccountList(project_id=project_id, platform=PlatformSlug.instagram)
        session.add(account_list)
        await session.flush()
    return account_list


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[AccountOut]:
    await _get_project(session, user, project_id)
    account_list = await session.scalar(
        select(AccountList).where(
            AccountList.project_id == project_id, AccountList.platform == PlatformSlug.instagram
        )
    )
    if account_list is None:
        return []
    accounts = (
        await session.scalars(
            select(Account)
            .where(Account.account_list_id == account_list.id, Account.archived_at.is_(None))
            .order_by(Account.created_at)
        )
    ).all()
    return [AccountOut.from_model(a) for a in accounts]


@router.post("", response_model=AddAccountsOut, status_code=status.HTTP_201_CREATED)
async def add_accounts(
    project_id: uuid.UUID, body: AddAccountsIn, user: CurrentUser, session: SessionDep
) -> AddAccountsOut:
    await _get_project(session, user, project_id)
    account_list = await _get_or_create_ig_list(session, project_id)

    existing = (
        await session.scalars(select(Account).where(Account.account_list_id == account_list.id))
    ).all()
    active_existing = [a for a in existing if a.archived_at is None]
    active_urls = {a.normalized_url for a in active_existing}
    # A previously archived account (same normalized_url) is reactivated in place rather than
    # erroring on the unique constraint — preserves its scrape history instead of recreating it.
    archived_by_url = {a.normalized_url: a for a in existing if a.archived_at is not None}
    slots_left = MAX_ACCOUNTS_PER_LIST - len(active_existing)

    added: list[AccountOut] = []
    errors: list[AddAccountError] = []
    seen_in_batch: set[str] = set()

    for raw in body.entries:
        line = raw.strip()
        if not line:
            continue
        try:
            normalized = normalize_instagram_input(line)
        except InvalidAccountUrlError as exc:
            errors.append(AddAccountError(input=line, message_ru=exc.message_ru))
            continue

        if normalized.normalized_url in active_urls or normalized.normalized_url in seen_in_batch:
            continue  # duplicate — silently deduped per AC

        if slots_left <= 0:
            errors.append(
                AddAccountError(
                    input=line,
                    message_ru=f"Достигнут лимит {MAX_ACCOUNTS_PER_LIST} аккаунтов на список.",
                )
            )
            continue

        archived_match = archived_by_url.get(normalized.normalized_url)
        if archived_match is not None:
            archived_match.archived_at = None
            archived_match.input_url = line
            await session.flush()
            added.append(AccountOut.from_model(archived_match))
            seen_in_batch.add(normalized.normalized_url)
            slots_left -= 1
            continue

        account = Account(
            account_list_id=account_list.id,
            input_url=line,
            normalized_url=normalized.normalized_url,
            handle=normalized.handle,
        )
        session.add(account)
        await session.flush()
        added.append(AccountOut.from_model(account))
        seen_in_batch.add(normalized.normalized_url)
        slots_left -= 1

    await session.commit()
    for account_out in added:
        await enqueue_profile_fetch(account_out.id, user.id)
    total = len(active_existing) + len(added)
    return AddAccountsOut(added=added, errors=errors, total=total)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_account(
    project_id: uuid.UUID, account_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    await _get_project(session, user, project_id)
    account = await session.scalar(
        select(Account)
        .join(AccountList, AccountList.id == Account.account_list_id)
        .where(Account.id == account_id, AccountList.project_id == project_id)
    )
    if account is None:
        raise ACCOUNT_NOT_FOUND

    # Soft delete: content_items/shortlist_items/deep_analysis_items from past runs reference
    # this account, and removing a competitor must not erase that history. Re-adding the same
    # account later (add_accounts) un-archives this same row instead of creating a new one.
    if account.archived_at is None:
        account.archived_at = datetime.now(UTC)
    await session.commit()
