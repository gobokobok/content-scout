import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_APIFY_RESULT,
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    AccountStatus,
    ContentItem,
    DeepAnalysis,
    DeepAnalysisStatus,
    RunStatus,
    UsageEvent,
)
from src.worker import maybe_start_deep_analysis, process_deep_analysis, process_run
from tests.conftest import (
    make_account,
    make_account_list,
    make_content_item,
    make_deep_analysis,
    make_project,
    make_run,
    make_user,
)


async def _fake_summarize(session, items, *, user_id, run_id, **_kwargs) -> None:
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
    account = await make_account(session, account_list=account_list)
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
    # One event for the profile fetch (quantity=1) + one for the content fetch (quantity=3).
    assert len(apify_events) == 2
    assert sorted(e.quantity for e in apify_events) == [1, 3]

    await session.refresh(account)
    assert account.followers_count == 12_400
    assert account.display_name == f"Тестовый аккаунт @{account.handle}"
    assert account.followers_updated_at is not None

    assert run.total_input_tokens == 300
    assert run.total_output_tokens == 60
    assert run.total_cost_usd > 0


async def test_process_run_item_limit_mode_fetches_last_n_publications(
    session: AsyncSession,
) -> None:
    """When item_limit is set instead of duration_days, the worker must pass since=None (no
    date cutoff) and limit=item_limit through to the platform."""
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=None, item_limit=5)
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    assert run.status == RunStatus.done
    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert len(items) == 5


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

        async def fetch_content(self, account, since=None, limit=None):
            if account.id == bad_account.id:
                raise RuntimeError("account is private")
            from src.platforms.mock import MockPlatform

            return await MockPlatform().fetch_content(account, since=since, limit=limit)

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


async def test_process_run_profile_fetch_failure_falls_back_to_last_known(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list, followers_count=999)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    class _ProfileFlakyPlatform:
        slug = "mock"

        async def fetch_content(self, account, since=None, limit=None):
            from src.platforms.mock import MockPlatform

            return await MockPlatform().fetch_content(account, since=since, limit=limit)

        async def fetch_profile(self, account):
            raise RuntimeError("apify profile boom")

    with (
        patch("src.worker.get_platform", return_value=_ProfileFlakyPlatform()),
        patch("src.worker.summarize_run_items", side_effect=_fake_summarize),
    ):
        await process_run(session, run)

    assert run.status == RunStatus.done
    await session.refresh(account)
    assert account.followers_count == 999  # unchanged — falls back to the last known value
    assert account.status == AccountStatus.active  # content scrape still succeeded

    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert len(items) == 3

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    apify_events = [u for u in usage if u.kind == KIND_APIFY_RESULT]
    # Only the content fetch — no usage event for the failed profile fetch.
    assert len(apify_events) == 1
    assert apify_events[0].quantity == 3


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

    async def _tracking_summarize(session, items, *, user_id, run_id, **_kwargs):
        calls.append(list(items))
        await _fake_summarize(session, items, user_id=user_id, run_id=run_id)

    with patch("src.worker.summarize_run_items", side_effect=_tracking_summarize):
        await process_run(session, run)

    summarized_ids = {item.id for batch in calls for item in batch}
    assert pre_summarized.id not in summarized_ids
    await session.refresh(pre_summarized)
    assert pre_summarized.summary == "уже готово"


async def test_process_run_cancellation_marks_failed(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    # Use an event to confirm the task is inside the blocking sleep before we cancel.
    inside = asyncio.Event()

    async def _blocking_fetch(account, since=None, limit=None):
        inside.set()
        await asyncio.sleep(60)
        return []

    class _BlockingPlatform:
        async def fetch_content(self, account, since=None, limit=None):
            return await _blocking_fetch(account, since=since, limit=limit)

    with patch("src.worker.get_platform", return_value=_BlockingPlatform()):
        task = asyncio.create_task(process_run(session, run))
        await inside.wait()  # guaranteed to be at asyncio.sleep(60) now
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert run.status == RunStatus.failed
    assert run.error_message == "Превышено время выполнения"
    assert run.finished_at is not None


async def test_process_run_parallel_scrape_same_rows_as_sequential(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    await make_account(session, account_list=account_list)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    assert run.status == RunStatus.done
    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    # Mock platform returns 3 items per account; 3 accounts = 9 items total
    assert len(items) == 9


async def test_process_run_duplicate_insert_is_noop(session: AsyncSession) -> None:
    """ON CONFLICT DO NOTHING: re-delivering the arq job must not duplicate content_items."""
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1)
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    first_count = len(
        (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    )
    assert first_count == 3  # Mock returns 3 items per account

    # Reset to scraping so process_run will re-enter the scraping phase
    run.status = RunStatus.pending
    run.started_at = None
    run.progress_accounts = 0
    run.progress_items = 0
    run.progress_summarized = 0
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run(session, run)

    second_count = len(
        (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    )
    assert second_count == first_count  # No duplicates


# ---------------------------------------------------------------------------
# E17-S4: deep analysis lifecycle
# ---------------------------------------------------------------------------


async def test_process_deep_analysis_transitions_extracting_synthesizing_done(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1)
    await make_content_item(session, run=run, account=account)
    analysis = await make_deep_analysis(session, run=run)
    await session.commit()

    seen_statuses: list[DeepAnalysisStatus] = []

    async def _fake_extract(session, deep_analysis_id, items, *, user_id, **_kwargs) -> None:
        seen_statuses.append(analysis.status)

    async def _fake_synthesize(session, analysis_arg, *, user_id, **_kwargs) -> None:
        seen_statuses.append(analysis_arg.status)
        analysis_arg.status = DeepAnalysisStatus.done

    with (
        patch("src.worker.extract_deep_analysis_items", side_effect=_fake_extract),
        patch("src.worker.synthesize_report", side_effect=_fake_synthesize),
    ):
        await process_deep_analysis(session, analysis)

    assert seen_statuses == [DeepAnalysisStatus.extracting, DeepAnalysisStatus.synthesizing]
    assert analysis.status == DeepAnalysisStatus.done


async def test_process_deep_analysis_exception_marks_failed(session: AsyncSession) -> None:
    project = await make_project(session)
    run = await make_run(session, project=project, duration_days=1)
    user = await make_user(session, token_balance=100)
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=60)
    await session.commit()

    async def _boom(*args, **kwargs):
        raise RuntimeError("extraction exploded")

    with patch("src.worker.extract_deep_analysis_items", side_effect=_boom):
        await process_deep_analysis(session, analysis)

    assert analysis.status == DeepAnalysisStatus.failed
    assert analysis.error_message == "extraction exploded"
    assert analysis.completed_at is not None
    # A hard failure delivers zero report — the up-front charge is refunded in full.
    assert analysis.tokens_charged == 0
    assert user.token_balance == 160


# ---------------------------------------------------------------------------
# run_analysis auto-chain (nav overhaul): a done "deep_analysis" run starts + enqueues a
# DeepAnalysis with no separate user step. Previously untested — the only coverage was of
# process_run/process_deep_analysis individually, never the glue between them.
# ---------------------------------------------------------------------------


async def test_maybe_start_deep_analysis_creates_and_enqueues_when_run_done(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=1000)
    run = await make_run(
        session,
        project=project,
        requested_by=user,
        run_type="deep_analysis",
        status=RunStatus.done,
    )
    await make_content_item(session, run=run, account=account)
    await session.commit()

    with patch("src.worker.enqueue_deep_analysis", new=AsyncMock()) as mock_enqueue:
        await maybe_start_deep_analysis(session, run)

    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert analysis.status == DeepAnalysisStatus.pending
    assert analysis.tokens_charged > 0
    mock_enqueue.assert_awaited_once_with(analysis.id)


async def test_maybe_start_deep_analysis_skips_for_stat_collection_run(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    run = await make_run(
        session, project=project, run_type="stat_collection", status=RunStatus.done
    )
    await session.commit()

    with patch("src.worker.enqueue_deep_analysis", new=AsyncMock()) as mock_enqueue:
        await maybe_start_deep_analysis(session, run)

    mock_enqueue.assert_not_awaited()
    count = await session.scalar(
        select(func.count()).select_from(DeepAnalysis).where(DeepAnalysis.run_id == run.id)
    )
    assert count == 0


async def test_maybe_start_deep_analysis_skips_when_run_not_done(session: AsyncSession) -> None:
    project = await make_project(session)
    run = await make_run(
        session, project=project, run_type="deep_analysis", status=RunStatus.failed
    )
    await session.commit()

    with patch("src.worker.enqueue_deep_analysis", new=AsyncMock()) as mock_enqueue:
        await maybe_start_deep_analysis(session, run)

    mock_enqueue.assert_not_awaited()


async def test_maybe_start_deep_analysis_skips_silently_on_insufficient_balance(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=0)
    run = await make_run(
        session,
        project=project,
        requested_by=user,
        run_type="deep_analysis",
        status=RunStatus.done,
    )
    await make_content_item(session, run=run, account=account)
    await session.commit()

    with patch("src.worker.enqueue_deep_analysis", new=AsyncMock()) as mock_enqueue:
        await maybe_start_deep_analysis(session, run)  # must not raise

    mock_enqueue.assert_not_awaited()
    count = await session.scalar(
        select(func.count()).select_from(DeepAnalysis).where(DeepAnalysis.run_id == run.id)
    )
    assert count == 0
    assert user.token_balance == 0
