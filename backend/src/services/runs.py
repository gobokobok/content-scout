import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Account, AccountList, PlatformSlug


async def resolve_target_accounts(
    session: AsyncSession, project_id: uuid.UUID, account_ids: list[uuid.UUID] | None
) -> list[Account]:
    """Accounts for the project's IG list, or the given subset (still IG-scoped).

    Direct bug fix (chat-reported, 2026-08-08): this used to also filter on
    `Account.status == AccountStatus.active`, permanently excluding any account that had ever
    hit a single scrape failure — status only ever flipped to `failed` in worker.py, never back
    (that half is now fixed too, see worker.py's `_fetch_one` result handling), but even with
    that fix an account stuck at `failed` could never be selected again to get the retry that
    would clear it. `status`/`fail_reason` stay informational only — every non-hidden,
    non-archived account is always a valid, retryable scrape target.
    """
    account_list = await session.scalar(
        select(AccountList).where(
            AccountList.project_id == project_id, AccountList.platform == PlatformSlug.instagram
        )
    )
    if account_list is None:
        return []

    stmt = select(Account).where(
        Account.account_list_id == account_list.id,
        # Direct bug fix (chat-reported): hidden accounts (post-mode Analysis's auto-created
        # single-post authors) are not real competitors — never eligible scrape targets, even
        # for a "whole list" run (account_ids=None).
        Account.hidden.is_(False),
    )
    if account_ids is not None:
        stmt = stmt.where(Account.id.in_(account_ids))
    return list(await session.scalars(stmt))
