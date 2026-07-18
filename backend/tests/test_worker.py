from decimal import Decimal
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_APIFY_RESULT,
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    AccountStatus,
    ContentItem,
    RunStatus,
    UsageEvent,
)
from src.worker import process_run
from tests.conftest import (
    make_account,
    make_account_list,
    make_content_item,
    make_project,
    make_run,
)


async def _fake_summarize(session, items, *, user_id, run_id) -> None:
    """Stand-in for the real Claude-backed summarizer — no network calls in worker tests."""
    for item in items:
        item.summary = "тестовое описание"
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=run_id,
                kind=KIND_CLAUDE_INPUT_TOKENS,
                quantity=100,
                unit_cost_usd=Decimal("0.000001"),
            )
        )
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=run_id,
                kind=KIND_CLAUDE_OUTPUT_TOKENS,
                quantity=20,
                unit_cost_usd=Decimal("0.000005"),
            )
        )


async def test_process_run_scrapes_mock_content_and_completes(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=3)
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    assert run.status == RunStatus.done
    assert run.progress_accounts == 1
    assert run.progress_items == 3
    assert run.progress_summarized == 3
    assert run.finished_at is not None

    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert len(items) == 3
    assert all(item.raw.get("mock") is True for item in items)
    assert all(item.summary == "тестовое описание" for item in items)

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    apify_events = [u for u in usage if u.kind == KIND_APIFY_RESULT]
    assert len(apify_events) == 1
    assert apify_events[0].quantity == 3

    assert run.total_input_tokens == 300
    assert run.total_output_tokens == 60
    assert run.total_cost_usd > 0


async def test_process_run_only_targets_active_accounts(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    await make_account(session, account_list=account_list, status=AccountStatus.failed)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    assert run.progress_accounts == 1


async def test_process_run_respects_account_subset(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account_a = await make_account(session, account_list=account_list)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1, account_ids=[account_a.id])
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    assert run.progress_accounts == 1
    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert all(item.account_id == account_a.id for item in items)


async def test_process_run_account_failure_does_not_fail_run(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    bad_account = await make_account(session, account_list=account_list)
    good_account = await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    class _FlakyPlatform:
        slug = "mock"

        async def fetch_content(self, account, since):
            if account.id == bad_account.id:
                raise RuntimeError("account is private")
            from src.platforms.mock import MockPlatform

            return await MockPlatform().fetch_content(account, since)

    with (
        patch("src.worker.get_platform", return_value=_FlakyPlatform()),
        patch("src.worker.summarize_run_items", side_effect=_fake_summarize),
    ):
        await process_run(session, run)

    assert run.status == RunStatus.done
    assert run.progress_accounts == 2
    await session.refresh(bad_account)
    await session.refresh(good_account)
    assert bad_account.status == AccountStatus.failed
    assert bad_account.fail_reason == "account is private"
    assert good_account.status == AccountStatus.active

    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert all(item.account_id == good_account.id for item in items)


async def test_process_run_no_accounts_still_completes(session: AsyncSession) -> None:
    project = await make_project(session)
    await make_account_list(session, project=project)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    assert run.status == RunStatus.done
    assert run.progress_accounts == 0
    assert run.progress_summarized == 0


async def test_process_run_skips_already_summarized_items(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1)
    pre_summarized = await make_content_item(
        session, run=run, account=account, summary="уже готово"
    )
    await session.commit()

    calls: list[list] = []

    async def _tracking_summarize(session, items, *, user_id, run_id):
        calls.append(list(items))
        await _fake_summarize(session, items, user_id=user_id, run_id=run_id)

    with patch("src.worker.summarize_run_items", side_effect=_tracking_summarize):
        await process_run(session, run)

    summarized_ids = {item.id for batch in calls for item in batch}
    assert pre_summarized.id not in summarized_ids
    await session.refresh(pre_summarized)
    assert pre_summarized.summary == "уже готово"
