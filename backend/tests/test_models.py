from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_APIFY_RESULT,
    Account,
    ContentType,
    PlatformSlug,
    ShortlistItem,
    UsageEvent,
)
from tests.conftest import (
    make_account,
    make_account_list,
    make_content_item,
    make_project,
    make_run,
    make_scheduled_run,
    make_user,
    make_workspace,
)


async def test_full_graph_roundtrip(session: AsyncSession) -> None:
    user = await make_user(session)
    workspace = await make_workspace(session, owner=user)
    project = await make_project(session, workspace=workspace)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, requested_by=user, duration_days=3)
    item = await make_content_item(session, run=run, account=account, views=1000, likes=50)

    session.add(ShortlistItem(project_id=project.id, content_item_id=item.id, added_by=user.id))
    session.add(
        UsageEvent(
            user_id=user.id,
            run_id=run.id,
            kind=KIND_APIFY_RESULT,
            quantity=1,
            unit_cost_usd=Decimal("0.00230000"),
        )
    )
    await session.flush()

    count = await session.scalar(
        select(func.count()).select_from(UsageEvent).where(UsageEvent.run_id == run.id)
    )
    assert count == 1
    fetched = await session.get(type(item), item.id)
    assert fetched is not None
    assert fetched.views == 1000


async def test_run_duration_check_rejected(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="duration_or_item_limit_range"):
        await make_run(session, duration_days=8)


async def test_run_item_limit_out_of_range_rejected(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="duration_or_item_limit_range"):
        await make_run(session, duration_days=None, item_limit=51)


async def test_run_neither_duration_nor_item_limit_rejected(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="duration_or_item_limit_range"):
        await make_run(session, duration_days=None, item_limit=None)


async def test_run_both_duration_and_item_limit_rejected(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="duration_or_item_limit_range"):
        await make_run(session, duration_days=3, item_limit=10)


async def test_scheduled_run_roundtrip(session: AsyncSession) -> None:
    scheduled = await make_scheduled_run(session, day_of_week=2, active=True)
    fetched = await session.get(type(scheduled), scheduled.id)
    assert fetched is not None
    assert fetched.duration_days == 7
    assert fetched.item_limit is None
    assert fetched.active is True
    assert fetched.timezone == "Europe/Moscow"


async def test_scheduled_run_duration_check_rejected(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="duration_or_item_limit_range"):
        await make_scheduled_run(session, duration_days=8)


async def test_scheduled_run_both_duration_and_item_limit_rejected(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="duration_or_item_limit_range"):
        await make_scheduled_run(session, duration_days=3, item_limit=10)


async def test_scheduled_run_day_of_week_out_of_range_rejected(session: AsyncSession) -> None:
    with pytest.raises(IntegrityError, match="day_of_week_range"):
        await make_scheduled_run(session, day_of_week=7)


async def test_duplicate_normalized_url_in_list_rejected(session: AsyncSession) -> None:
    account_list = await make_account_list(session)
    await make_account(
        session, account_list=account_list, normalized_url="https://instagram.com/dup"
    )
    with pytest.raises(IntegrityError, match="uq_accounts"):
        await make_account(
            session, account_list=account_list, normalized_url="https://instagram.com/dup"
        )


async def test_one_list_per_platform_rejected(session: AsyncSession) -> None:
    project = await make_project(session)
    await make_account_list(session, project=project, platform=PlatformSlug.instagram)
    with pytest.raises(IntegrityError, match="uq_account_lists"):
        await make_account_list(session, project=project, platform=PlatformSlug.instagram)


async def test_account_cap_trigger_blocks_51st(session: AsyncSession) -> None:
    account_list = await make_account_list(session)
    session.add_all(
        Account(
            account_list_id=account_list.id,
            input_url=f"https://instagram.com/bulk{i}",
            normalized_url=f"https://instagram.com/bulk{i}",
            handle=f"bulk{i}",
        )
        for i in range(50)
    )
    await session.flush()

    with pytest.raises(DBAPIError, match="already has 50 accounts"):
        await make_account(session, account_list=account_list)


async def test_shortlist_active_uniqueness_and_readd(session: AsyncSession) -> None:
    user = await make_user(session)
    project = await make_project(session)
    item = await make_content_item(session)

    first = ShortlistItem(project_id=project.id, content_item_id=item.id, added_by=user.id)
    session.add(first)
    await session.flush()

    with pytest.raises(IntegrityError, match="uq_shortlist_items_active"):
        async with session.begin_nested():
            session.add(
                ShortlistItem(project_id=project.id, content_item_id=item.id, added_by=user.id)
            )
            await session.flush()

    # after soft-removal the same item can be shortlisted again
    first.removed_at = datetime.now(UTC)
    await session.flush()
    session.add(ShortlistItem(project_id=project.id, content_item_id=item.id, added_by=user.id))
    await session.flush()


async def test_timestamps_are_timezone_aware(session: AsyncSession) -> None:
    account = await make_account(session)
    await session.refresh(account)
    assert account.created_at.tzinfo is not None


async def test_views_nullable_for_posts(session: AsyncSession) -> None:
    item = await make_content_item(session, type=ContentType.post, views=None, likes=10)
    assert item.views is None


async def test_schema_has_exactly_expected_tables(session: AsyncSession) -> None:
    expected = {
        "users",
        "workspaces",
        "workspace_members",
        "projects",
        "account_lists",
        "accounts",
        "analysis_runs",
        "content_items",
        "shortlist_items",
        "usage_events",
        "alembic_version",
    }
    tables = {
        row[0]
        for row in await session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
    }
    assert tables == expected
