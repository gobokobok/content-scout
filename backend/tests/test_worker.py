from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AccountStatus, ContentItem, RunStatus
from src.worker import process_run
from tests.conftest import make_account, make_account_list, make_project, make_run


async def test_process_run_scrapes_mock_content_and_completes(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=3)
    await session.commit()

    await process_run(session, run)

    assert run.status == RunStatus.done
    assert run.progress_accounts == 1
    assert run.progress_items == 3
    assert run.finished_at is not None

    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert len(items) == 3
    assert all(item.raw.get("mock") is True for item in items)


async def test_process_run_only_targets_active_accounts(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    await make_account(session, account_list=account_list, status=AccountStatus.failed)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    await process_run(session, run)

    assert run.progress_accounts == 1


async def test_process_run_respects_account_subset(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account_a = await make_account(session, account_list=account_list)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1, account_ids=[account_a.id])
    await session.commit()

    await process_run(session, run)

    assert run.progress_accounts == 1
    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert all(item.account_id == account_a.id for item in items)


async def test_process_run_no_accounts_still_completes(session: AsyncSession) -> None:
    project = await make_project(session)
    await make_account_list(session, project=project)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    await process_run(session, run)

    assert run.status == RunStatus.done
    assert run.progress_accounts == 0
