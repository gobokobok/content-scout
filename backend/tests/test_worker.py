import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models import (
    KIND_APIFY_RESULT,
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    Account,
    AccountStatus,
    ContentItem,
    ContentType,
    DeepAnalysis,
    DeepAnalysisItem,
    DeepAnalysisStatus,
    RunStatus,
    UsageEvent,
)
from src.platforms.base import RawContentItem
from src.worker import (
    WorkerSettings,
    process_run,
    process_run_and_maybe_analyze,
    run_deep_analysis_pipeline,
)
from tests.conftest import (
    make_account,
    make_account_list,
    make_content_item,
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


def test_worker_max_jobs_stays_within_apify_concurrency_ceiling() -> None:
    """E20-S2/D44: worst case is every concurrent worker job being a run_analysis job, each
    firing up to scrape_concurrency Apify calls at once — that product must not exceed the
    confirmed 25-concurrent-Apify-run ceiling (the previous unset arq default of 10 allowed up
    to 50, already 2x over)."""
    settings = get_settings()
    assert WorkerSettings.max_jobs == settings.worker_max_jobs
    assert settings.worker_max_jobs * settings.scrape_concurrency <= 25


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


async def test_process_run_deep_analysis_type_does_not_notify_immediately(
    session: AsyncSession,
) -> None:
    """A deep_analysis run's completion notification is deferred to process_deep_analysis
    (see worker.py) — notifying here would announce "done" before comments/synthesis even
    start. stat_collection runs are unaffected (see the sibling test below)."""
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=1000)
    run = await make_run(
        session,
        project=project,
        requested_by=user,
        duration_days=3,
        run_type="deep_analysis",
    )
    await session.commit()

    with (
        patch("src.worker.summarize_run_items", side_effect=_fake_summarize),
        patch("src.worker.notify_run_complete", new_callable=AsyncMock) as mock_notify,
    ):
        await process_run(session, run)

    assert run.status == RunStatus.done
    mock_notify.assert_not_awaited()


async def test_process_run_stat_collection_type_still_notifies_immediately(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=1000)
    run = await make_run(
        session,
        project=project,
        requested_by=user,
        duration_days=3,
        run_type="stat_collection",
    )
    await session.commit()

    with (
        patch("src.worker.summarize_run_items", side_effect=_fake_summarize),
        patch("src.worker.notify_run_complete", new_callable=AsyncMock) as mock_notify,
    ):
        await process_run(session, run)

    assert run.status == RunStatus.done
    mock_notify.assert_awaited_once()


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
# E17-S4/D50: deep analysis lifecycle — run_deep_analysis_pipeline is now the standalone
# pipeline, called inline from run_analysis (no more separate arq job/auto-chain), and
# incremental charging (D50) means it always starts a fresh DeepAnalysis at tokens_charged=0.
# ---------------------------------------------------------------------------


async def test_run_deep_analysis_pipeline_transitions_extracting_synthesizing_done(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=1000)
    run = await make_run(session, project=project, requested_by=user, duration_days=1)
    await make_content_item(session, run=run, account=account)
    await session.commit()

    seen_statuses: list[DeepAnalysisStatus] = []

    async def _fake_extract(session, analysis, items, *, user, **_kwargs) -> bool:
        seen_statuses.append(analysis.status)
        return False

    async def _fake_synthesize(session, analysis_arg, *, user_id, **_kwargs) -> None:
        seen_statuses.append(analysis_arg.status)
        analysis_arg.status = DeepAnalysisStatus.done

    with (
        patch("src.worker.extract_deep_analysis_items", side_effect=_fake_extract),
        patch("src.worker.synthesize_report", side_effect=_fake_synthesize),
    ):
        await run_deep_analysis_pipeline(session, run, user)

    assert seen_statuses == [DeepAnalysisStatus.extracting, DeepAnalysisStatus.synthesizing]
    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert analysis.status == DeepAnalysisStatus.done


async def test_run_deep_analysis_pipeline_notifies_on_success(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=1000)
    run = await make_run(session, project=project, requested_by=user, duration_days=1)
    await make_content_item(session, run=run, account=account)
    await session.commit()

    async def _fake_extract(session, analysis, items, *, user, **_kwargs) -> bool:
        return False

    async def _fake_synthesize(session, analysis_arg, *, user_id, **_kwargs) -> None:
        analysis_arg.status = DeepAnalysisStatus.done

    with (
        patch("src.worker.extract_deep_analysis_items", side_effect=_fake_extract),
        patch("src.worker.synthesize_report", side_effect=_fake_synthesize),
        patch("src.worker.notify_deep_analysis_complete", new_callable=AsyncMock) as mock_notify,
    ):
        await run_deep_analysis_pipeline(session, run, user)

    mock_notify.assert_awaited_once()
    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert mock_notify.call_args[0][0] is analysis


async def test_run_deep_analysis_pipeline_token_exhausted_sets_disclaimer(
    session: AsyncSession,
) -> None:
    """D43/D50: extraction stopping early on balance exhaustion doesn't hard-fail the
    analysis — whatever was extracted still gets synthesized, with a disclaimer message."""
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=5)
    run = await make_run(session, project=project, requested_by=user, duration_days=1)
    await make_content_item(session, run=run, account=account)
    await session.commit()

    async def _fake_extract(session, analysis, items, *, user, **_kwargs) -> bool:
        return True  # simulates the balance running out mid-extraction

    async def _fake_synthesize(session, analysis_arg, *, user_id, **_kwargs) -> None:
        # Mirrors synthesize_report's real success path: never touches error_message.
        analysis_arg.status = DeepAnalysisStatus.done

    with (
        patch("src.worker.extract_deep_analysis_items", side_effect=_fake_extract),
        patch("src.worker.synthesize_report", side_effect=_fake_synthesize),
    ):
        await run_deep_analysis_pipeline(session, run, user)

    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert analysis.status == DeepAnalysisStatus.done
    assert analysis.error_message == (
        "Баланс токенов исчерпан. Показаны результаты, полученные до остановки."
    )


async def test_run_deep_analysis_pipeline_exception_marks_failed_without_refund(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=100)
    run = await make_run(session, project=project, requested_by=user, duration_days=1)
    await make_content_item(session, run=run, account=account)
    await session.commit()

    async def _boom(session, analysis, items, *, user, **_kwargs):
        # Simulates a real partial charge having already happened before the crash.
        analysis.tokens_charged += 4
        user.token_balance -= 4
        raise RuntimeError("extraction exploded")

    with (
        patch("src.worker.extract_deep_analysis_items", side_effect=_boom),
        patch("src.worker.notify_deep_analysis_complete", new_callable=AsyncMock) as mock_notify,
    ):
        await run_deep_analysis_pipeline(session, run, user)

    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert analysis.status == DeepAnalysisStatus.failed
    assert analysis.error_message == "extraction exploded"
    assert analysis.completed_at is not None
    # D50: incremental charging means tokens_charged already reflects real work done — no
    # refund on failure, unlike the old up-front lump-sum model.
    assert analysis.tokens_charged == 4
    assert user.token_balance == 96
    mock_notify.assert_awaited_once()


async def test_run_deep_analysis_pipeline_cancellation_marks_failed_without_refund(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    account = await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=100)
    run = await make_run(session, project=project, requested_by=user, duration_days=1)
    await make_content_item(session, run=run, account=account)
    await session.commit()

    inside = asyncio.Event()

    async def _blocking_extract(*args, **kwargs):
        inside.set()
        await asyncio.sleep(60)

    with patch("src.worker.extract_deep_analysis_items", side_effect=_blocking_extract):
        task = asyncio.create_task(run_deep_analysis_pipeline(session, run, user))
        await inside.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert analysis.status == DeepAnalysisStatus.failed
    assert analysis.error_message == "Превышено время выполнения"
    assert analysis.completed_at is not None
    # Regression test for the bug where arq's job_timeout cancellation (CancelledError, a
    # BaseException) bypassed `except Exception` entirely and left rows stuck forever — no
    # refund expected either, since nothing was charged before the cancellation.
    assert analysis.tokens_charged == 0
    assert user.token_balance == 100


# ---------------------------------------------------------------------------
# run_analysis (D50): scrape then, inline in the same job, the standalone Analysis pipeline
# for deep_analysis-type runs — no more separate auto-chain/enqueue.
# ---------------------------------------------------------------------------


async def test_run_analysis_chains_into_deep_analysis_pipeline_when_run_done(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=1000)
    run = await make_run(
        session, project=project, requested_by=user, duration_days=1, run_type="deep_analysis"
    )
    await session.commit()

    async def _fake_extract(session, analysis, items, *, user, **_kwargs) -> bool:
        return False

    async def _fake_synthesize(session, analysis_arg, *, user_id, **_kwargs) -> None:
        analysis_arg.status = DeepAnalysisStatus.done

    with (
        patch("src.worker.extract_deep_analysis_items", side_effect=_fake_extract),
        patch("src.worker.synthesize_report", side_effect=_fake_synthesize),
    ):
        await process_run_and_maybe_analyze(session, run)

    assert run.status == RunStatus.done
    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert analysis.status == DeepAnalysisStatus.done


async def test_run_analysis_does_not_chain_for_stat_collection(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    run = await make_run(session, project=project, duration_days=1, run_type="stat_collection")
    await session.commit()

    with patch("src.worker.summarize_run_items", side_effect=_fake_summarize):
        await process_run_and_maybe_analyze(session, run)

    assert run.status == RunStatus.done
    count = await session.scalar(
        select(func.count()).select_from(DeepAnalysis).where(DeepAnalysis.run_id == run.id)
    )
    assert count == 0


async def test_run_analysis_zero_balance_ends_in_no_data_failure(session: AsyncSession) -> None:
    """D50: there's no more up-front insufficient-balance skip gate — the pipeline always
    starts, extraction immediately exhausts (zero items attempted), and synthesis's own
    existing no-done-items guard fails the analysis cleanly instead."""
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    await make_account(session, account_list=account_list)
    user = await make_user(session, token_balance=0)
    run = await make_run(
        session, project=project, requested_by=user, duration_days=1, run_type="deep_analysis"
    )
    await session.commit()

    await process_run_and_maybe_analyze(session, run)

    assert run.status == RunStatus.done  # the base scrape itself still succeeds
    analysis = (
        await session.scalars(select(DeepAnalysis).where(DeepAnalysis.run_id == run.id))
    ).one()
    assert analysis.status == DeepAnalysisStatus.failed
    assert analysis.tokens_charged == 0
    assert user.token_balance == 0
    items = (await session.scalars(select(DeepAnalysisItem))).all()
    assert items == []


# ---------------------------------------------------------------------------
# D49/D50: post-mode Analysis — a single publication URL instead of an account's post history.
# ---------------------------------------------------------------------------


async def test_process_run_post_mode_creates_one_item_and_resolves_new_account(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    user = await make_user(session)
    run = await make_run(
        session,
        project=project,
        requested_by=user,
        run_type="deep_analysis",
        analysis_mode="post",
        duration_days=None,
        target_post_url="https://www.instagram.com/p/ABC123/",
    )
    await session.commit()

    raw_item = RawContentItem(
        external_id="abc123",
        type=ContentType.post,
        published_at=run.created_at,
        url="https://www.instagram.com/p/ABC123/",
        caption="Тестовая подпись",
        raw={"ownerUsername": "brand_new_author"},
    )

    class _PostPlatform:
        async def fetch_post(self, post_url: str) -> RawContentItem:
            return raw_item

    with patch("src.worker.get_platform", return_value=_PostPlatform()):
        await process_run(session, run)

    assert run.status == RunStatus.done
    assert run.progress_accounts == 1
    assert run.progress_items == 1
    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert len(items) == 1
    assert items[0].external_id == "abc123"

    account = await session.get(Account, items[0].account_id)
    assert account.handle == "brand_new_author"


async def test_process_run_post_mode_reuses_existing_account(session: AsyncSession) -> None:
    project = await make_project(session)
    account_list = await make_account_list(session, project=project)
    existing = await make_account(session, account_list=account_list, handle="existing_author")
    user = await make_user(session)
    run = await make_run(
        session,
        project=project,
        requested_by=user,
        run_type="deep_analysis",
        analysis_mode="post",
        duration_days=None,
        target_post_url="https://www.instagram.com/p/XYZ789/",
    )
    await session.commit()

    raw_item = RawContentItem(
        external_id="xyz789",
        type=ContentType.post,
        published_at=run.created_at,
        url="https://www.instagram.com/p/XYZ789/",
        raw={"ownerUsername": "existing_author"},
    )

    class _PostPlatform:
        async def fetch_post(self, post_url: str) -> RawContentItem:
            return raw_item

    with patch("src.worker.get_platform", return_value=_PostPlatform()):
        await process_run(session, run)

    items = (await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id))).all()
    assert len(items) == 1
    assert items[0].account_id == existing.id


async def test_process_run_post_mode_fetch_failure_marks_run_failed_gracefully(
    session: AsyncSession,
) -> None:
    project = await make_project(session)
    user = await make_user(session)
    run = await make_run(
        session,
        project=project,
        requested_by=user,
        run_type="deep_analysis",
        analysis_mode="post",
        duration_days=None,
        target_post_url="https://www.instagram.com/p/GONE/",
    )
    await session.commit()

    class _FailingPlatform:
        async def fetch_post(self, post_url: str):
            raise RuntimeError("post not found")

    with patch("src.worker.get_platform", return_value=_FailingPlatform()):
        await process_run(session, run)

    # Mirrors a failed-account scrape: the run still completes (done), not hard-failed, with
    # zero items and an explanatory message — same "never leave the user with nothing to see"
    # shape process_run already uses for a single bad account among many.
    assert run.status == RunStatus.done
    assert run.progress_items == 0
    assert run.error_message is not None
