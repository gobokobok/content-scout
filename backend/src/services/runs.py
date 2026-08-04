import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Account, AccountList, AccountStatus, PlatformSlug


async def resolve_target_accounts(
    session: AsyncSession, project_id: uuid.UUID, account_ids: list[uuid.UUID] | None
) -> list[Account]:
    """Active accounts for the project's IG list, or the given subset (still IG-scoped)."""
    account_list = await session.scalar(
        select(AccountList).where(
            AccountList.project_id == project_id, AccountList.platform == PlatformSlug.instagram
        )
    )
    if account_list is None:
        return []

    stmt = select(Account).where(
        Account.account_list_id == account_list.id,
        Account.status == AccountStatus.active,
        # Direct bug fix (chat-reported): hidden accounts (post-mode Analysis's auto-created
        # single-post authors) are not real competitors — never eligible scrape targets, even
        # for a "whole list" run (account_ids=None).
        Account.hidden.is_(False),
    )
    if account_ids is not None:
        stmt = stmt.where(Account.id.in_(account_ids))
    return list(await session.scalars(stmt))
