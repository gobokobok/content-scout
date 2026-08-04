import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from anthropic import AsyncAnthropic
from arq import cron
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.db import get_sessionmaker
from src.models import (
    KIND_APIFY_RESULT,
    Account,
    AccountList,
    AccountStatus,
    AnalysisRun,
    ContentItem,
    DeepAnalysis,
    DeepAnalysisStatus,
    PlatformSlug,
    RunStatus,
    UsageEvent,
    User,
)
from src.platforms import get_platform
from src.platforms.base import Platform
from src.services.deep_analysis import create_pending_deep_analysis, fail_deep_analysis
from src.services.deep_analysis_extraction import extract_deep_analysis_items
from src.services.deep_analysis_synthesis import synthesize_report
from src.services.run_summary import generate_run_summary
from src.services.runs import resolve_target_accounts
from src.services.scheduled_runs import fire_due_schedules
from src.services.summarizer import summarize_run_items
from src.services.telegram_notify import notify_deep_analysis_complete, notify_run_complete
from src.services.url_normalizer import InvalidAccountUrlError, normalize_instagram_input
from src.services.usage import rollup_run_totals

# arq's own logging.config.dictConfig only configures the "arq" namespace (see arq/logs.py) —
# it never touches the root logger, so every `logging.getLogger(__name__)` call anywhere in
# src/ was silently going nowhere in the worker process (found 2026-08-03 debugging a
# deep-analysis failure with zero log trace anywhere despite an explicit logger.exception call
# on the failure path). Mirrors the same fix in main.py for the api process.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)

_SUMMARIZER_HTTP_TIMEOUT = 10.0
_TOKEN_BALANCE_EXHAUSTED_MSG = (
    "Баланс токенов исчерпан. Показаны результаты, полученные до остановки."
)


async def _resolve_or_create_account(
    session: AsyncSession, project_id: uuid.UUID, owner_username: str
) -> Account:
    """Post-mode Analysis (D49/D50): the pasted post's author isn't necessarily an existing
    competitor — reuse the account if it already is one, otherwise auto-add it (mirrors
    api/accounts.py:add_accounts' normalize-and-reuse-or-create, minus the 50-per-list cap,
    which shouldn't block an Analysis run the user explicitly asked for)."""
    normalized = normalize_instagram_input(owner_username)
    account_list = await session.scalar(
        select(AccountList).where(
            AccountList.project_id == project_id, AccountList.platform == PlatformSlug.instagram
        )
    )
    if account_list is None:
        account_list = AccountList(project_id=project_id, platform=PlatformSlug.instagram)
        session.add(account_list)
        await session.flush()

    existing = await session.scalar(
        select(Account).where(
            Account.account_list_id == account_list.id,
            Account.normalized_url == normalized.normalized_url,
        )
    )
    if existing is not None:
        if existing.archived_at is not None:
            existing.archived_at = None
        return existing

    account = Account(
        account_list_id=account_list.id,
        input_url=normalized.normalized_url,
        normalized_url=normalized.normalized_url,
        handle=normalized.handle,
    )
    session.add(account)
    await session.flush()
    return account


async def _scrape_single_post(
    session: AsyncSession, run: AnalysisRun, platform: Platform, settings: Settings
) -> None:
    """Post-mode Analysis (D49/D50): fetches exactly one publication by URL instead of an
    account's post history, resolving/creating its author as a real Account so
    ContentItem.account_id stays non-nullable and every existing account-joined query (virality,
    exports, Telegram notify) keeps working unmodified."""
    assert run.target_post_url is not None
    try:
        raw_item = await platform.fetch_post(run.target_post_url)
        owner_username = raw_item.raw.get("ownerUsername")
        if not owner_username:
            raise InvalidAccountUrlError("Не удалось определить автора публикации.")
        account = await _resolve_or_create_account(session, run.project_id, owner_username)
    except Exception as exc:  # noqa: BLE001 — mirrors the per-account failure handling below
        run.error_message = str(exc)[:1000]
        logger.warning("run_id=%s post fetch failed: %s", run.id, exc)
        run.progress_accounts = 0
        run.progress_items = 0
        await session.commit()
        return

    await session.execute(
        pg_insert(ContentItem)
        .values(
            id=uuid.uuid4(),
            run_id=run.id,
            account_id=account.id,
            external_id=raw_item.external_id,
            type=raw_item.type,
            published_at=raw_item.published_at,
            title=raw_item.title,
            url=raw_item.url,
            cover_url=raw_item.cover_url,
            caption=raw_item.caption,
            likes=raw_item.likes,
            views=raw_item.views,
            comments=raw_item.comments,
            raw=raw_item.raw,
        )
        .on_conflict_do_nothing(index_elements=["run_id", "external_id"])
    )
    session.add(
        UsageEvent(
            user_id=run.requested_by,
            run_id=run.id,
            kind=KIND_APIFY_RESULT,
            quantity=1,
            unit_cost_usd=Decimal(str(settings.apify_unit_cost_usd)),
        )
    )
    run.progress_accounts = 1
    run.progress_items = 1
    await session.commit()


async def _finish_run(session: AsyncSession, run: AnalysisRun, settings: Settings) -> None:
    """Shared tail for both scrape paths (multi-account and single-post): summarizing (skipped
    entirely for deep_analysis runs — Analysis's own extraction/synthesis is the "summary", no
    product surface shows Review's per-item Claude captions for it, D50) -> done -> rollup ->
    notify."""
    run.status = RunStatus.summarizing
    await session.commit()

    requesting_user = await session.get(User, run.requested_by)
    token_balance_exhausted = False

    if run.run_type != "deep_analysis":
        pending_items = list(
            await session.scalars(
                select(ContentItem).where(
                    ContentItem.run_id == run.id, ContentItem.summary.is_(None)
                )
            )
        )
        batch_size = max(1, settings.summary_concurrency)
        anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        http_client = httpx.AsyncClient(timeout=_SUMMARIZER_HTTP_TIMEOUT)

        for start in range(0, len(pending_items), batch_size):
            if requesting_user is not None and requesting_user.token_balance <= 0:
                token_balance_exhausted = True
                break

            batch = pending_items[start : start + batch_size]

            if requesting_user is not None and requesting_user.token_balance < len(batch):
                batch = batch[: requesting_user.token_balance]
                token_balance_exhausted = True

            await summarize_run_items(
                session,
                batch,
                user_id=run.requested_by,
                run_id=run.id,
                project_id=run.project_id,
                client=anthropic_client,
                http_client=http_client,
            )
            run.progress_summarized += len(batch)

            if requesting_user is not None:
                requesting_user.token_balance = max(0, requesting_user.token_balance - len(batch))

            await session.commit()

            if token_balance_exhausted:
                break

        try:
            # Run-level AI overview (E15-S1) — one extra call after per-item summaries
            # are ready, using the same client. Never fails the run: the service itself
            # never raises, but this call site mirrors notify_run_complete's
            # defensive try/except pattern for good measure.
            await generate_run_summary(
                session, run, user_id=run.requested_by, client=anthropic_client
            )
        except Exception:  # noqa: BLE001
            pass

        await anthropic_client.close()
        await http_client.aclose()

    await rollup_run_totals(session, run)
    run.status = RunStatus.done
    run.finished_at = datetime.now(UTC)
    if token_balance_exhausted:
        run.error_message = _TOKEN_BALANCE_EXHAUSTED_MSG
    await session.commit()
    requesting_user = requesting_user or await session.get(User, run.requested_by)
    # deep_analysis runs defer their completion notification until run_deep_analysis_pipeline
    # actually finishes — notifying here would tell the user the run is "done" while only the
    # scrape has finished, before the real Analysis result exists.
    if requesting_user and run.notify_on_complete and run.run_type != "deep_analysis":
        await notify_run_complete(run, requesting_user, session)


async def process_run(session: AsyncSession, run: AnalysisRun) -> None:
    """Core run lifecycle logic, isolated from session/queue plumbing for testability."""
    try:
        run.status = RunStatus.scraping
        run.started_at = datetime.now(UTC)
        await session.commit()

        platform = get_platform(PlatformSlug.instagram)
        settings = get_settings()

        if run.analysis_mode == "post":
            logger.info(
                "run_id=%s scope: post_url=%s run_type=%s",
                run.id,
                run.target_post_url,
                run.run_type,
            )
            await _scrape_single_post(session, run, platform, settings)
            await _finish_run(session, run, settings)
            return

        accounts = await resolve_target_accounts(session, run.project_id, run.account_ids)
        # Exactly one of duration_days/item_limit is set on the run (see AnalysisRun) — a day
        # window (since, no limit override) or the last N publications (no date cutoff, limit=N).
        since = run.started_at - timedelta(days=run.duration_days) if run.duration_days else None
        logger.info(
            "run_id=%s scope: accounts=%d duration_days=%s item_limit=%s run_type=%s",
            run.id,
            len(accounts),
            run.duration_days,
            run.item_limit,
            run.run_type,
        )
        semaphore = asyncio.Semaphore(settings.scrape_concurrency)

        async def _fetch_one(account):
            async with semaphore:
                try:
                    profile_info = await platform.fetch_profile(account)
                except Exception:  # noqa: BLE001 — profile fetch never fails the account's scrape
                    profile_info = None
                try:
                    content = await platform.fetch_content(
                        account, since=since, limit=run.item_limit
                    )
                    return account, content, profile_info, None
                except Exception as exc:  # noqa: BLE001
                    return account, None, profile_info, exc

        fetch_results = await asyncio.gather(*(_fetch_one(a) for a in accounts))

        items_found = 0
        for account, raw_items, profile_info, exc in fetch_results:
            if profile_info is not None:
                account.followers_count = profile_info.followers_count
                account.display_name = profile_info.display_name
                account.avatar_url = profile_info.avatar_url
                account.followers_updated_at = datetime.now(UTC)
                session.add(
                    UsageEvent(
                        user_id=run.requested_by,
                        run_id=run.id,
                        kind=KIND_APIFY_RESULT,
                        quantity=1,
                        unit_cost_usd=Decimal(str(settings.apify_unit_cost_usd)),
                    )
                )
            if exc is not None:
                account.status = AccountStatus.failed
                account.fail_reason = str(exc)[:500]
                logger.warning(
                    "run_id=%s account_id=%s content fetch failed: %s", run.id, account.id, exc
                )
            else:
                if len(raw_items) >= 50:
                    # 50 is InstagramPlatform's hardcoded resultsLimit fallback when item_limit
                    # is unset (duration_days mode) — landing exactly there is a signal the
                    # account may have posted more than 50 times in the window and got silently
                    # truncated, not that it genuinely posted exactly 50.
                    logger.info(
                        "run_id=%s account_id=%s hit the 50-item scrape ceiling — actual post "
                        "count in the requested window may be higher",
                        run.id,
                        account.id,
                    )
                for raw in raw_items:
                    await session.execute(
                        pg_insert(ContentItem)
                        .values(
                            id=uuid.uuid4(),
                            run_id=run.id,
                            account_id=account.id,
                            external_id=raw.external_id,
                            type=raw.type,
                            published_at=raw.published_at,
                            title=raw.title,
                            url=raw.url,
                            cover_url=raw.cover_url,
                            caption=raw.caption,
                            likes=raw.likes,
                            views=raw.views,
                            comments=raw.comments,
                            raw=raw.raw,
                        )
                        .on_conflict_do_nothing(index_elements=["run_id", "external_id"])
                    )
                    items_found += 1
                if raw_items:
                    session.add(
                        UsageEvent(
                            user_id=run.requested_by,
                            run_id=run.id,
                            kind=KIND_APIFY_RESULT,
                            quantity=len(raw_items),
                            unit_cost_usd=Decimal(str(settings.apify_unit_cost_usd)),
                        )
                    )
            run.progress_accounts += 1
            run.progress_items = items_found
            await session.commit()

        await _finish_run(session, run, settings)

    except asyncio.CancelledError:
        run.status = RunStatus.failed
        run.error_message = "Превышено время выполнения"
        run.finished_at = datetime.now(UTC)
        await asyncio.shield(session.commit())
        try:
            requesting_user = await session.get(User, run.requested_by)
            if requesting_user and run.notify_on_complete:
                await notify_run_complete(run, requesting_user, session)
        except Exception:  # noqa: BLE001
            pass
        raise

    except Exception as exc:  # noqa: BLE001 — worker boundary: never let a run hang
        run.status = RunStatus.failed
        run.error_message = str(exc)[:1000]
        run.finished_at = datetime.now(UTC)
        await session.commit()
        try:
            requesting_user = await session.get(User, run.requested_by)
            if requesting_user and run.notify_on_complete:
                await notify_run_complete(run, requesting_user, session)
        except Exception:  # noqa: BLE001
            pass


async def run_deep_analysis_pipeline(session: AsyncSession, run: AnalysisRun, user: User) -> None:
    """D50: the standalone Analysis pipeline, run inline as the continuation of a deep_analysis
    run_type's own worker job (no more separate auto-chain/enqueue, no more
    deep_analysis_skip_reason — every deep_analysis run either produces a DeepAnalysis here or
    process_run above already failed/was cancelled, in which case its own except blocks already
    notified). extracting (E17-S3) -> synthesizing (E17-S4) -> done/failed, exactly one
    notification either way."""
    analysis = await create_pending_deep_analysis(session, run, user)
    await session.commit()
    try:
        analysis.status = DeepAnalysisStatus.extracting
        await session.commit()

        items = list(await session.scalars(select(ContentItem).where(ContentItem.run_id == run.id)))
        token_exhausted = await extract_deep_analysis_items(
            session, analysis, items, user=user, comments_limit=run.comments_limit
        )
        if token_exhausted:
            # D43: still synthesize whatever was extracted before the balance ran out, rather
            # than discarding it — the disclaimer persists through synthesize_report's success
            # path since it never touches error_message on a `done` result.
            analysis.error_message = _TOKEN_BALANCE_EXHAUSTED_MSG
        await session.commit()

        analysis.status = DeepAnalysisStatus.synthesizing
        await session.commit()

        await synthesize_report(session, analysis, user_id=analysis.requested_by)
        await session.commit()
        await _notify_deep_analysis(session, analysis)
    except asyncio.CancelledError:
        # CancelledError is a BaseException, not Exception — arq's job_timeout cancels the
        # task via asyncio.wait_for, which would otherwise bypass the except Exception below
        # and leave the row stuck in extracting/synthesizing forever (mirrors process_run's
        # same handling above).
        await asyncio.shield(
            fail_deep_analysis(
                session, analysis, "Превышено время выполнения", user_id=analysis.requested_by
            )
        )
        await asyncio.shield(session.commit())
        await asyncio.shield(_notify_deep_analysis(session, analysis))
        raise
    except Exception as exc:  # noqa: BLE001 — worker boundary: never let a deep analysis hang
        await fail_deep_analysis(session, analysis, str(exc), user_id=analysis.requested_by)
        await session.commit()
        await _notify_deep_analysis(session, analysis)


async def _notify_deep_analysis(session: AsyncSession, analysis: DeepAnalysis) -> None:
    """Fires once the full deep_analysis pipeline (scrape -> comments -> synthesis) is
    actually done — process_run's own except blocks cover the case where the base scrape
    itself fails or is cancelled before ever reaching this pipeline."""
    try:
        run = await session.get(AnalysisRun, analysis.run_id)
        user = await session.get(User, analysis.requested_by)
        if run and user and run.notify_on_complete:
            await notify_deep_analysis_complete(analysis, run, user, session)
    except Exception:  # noqa: BLE001
        pass


async def process_run_and_maybe_analyze(session: AsyncSession, run: AnalysisRun) -> None:
    """Core glue logic, isolated from session/queue plumbing for testability (mirrors
    process_run/run_deep_analysis_pipeline): scrape, then continue inline into the standalone
    Analysis pipeline (D50) when this is a deep_analysis run that finished cleanly — no more
    separate auto-chain/enqueue."""
    await process_run(session, run)
    if run.run_type == "deep_analysis" and run.status == RunStatus.done:
        user = await session.get(User, run.requested_by)
        if user is not None:
            await run_deep_analysis_pipeline(session, run, user)


async def run_analysis(ctx: dict, run_id: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        run = await session.get(AnalysisRun, uuid.UUID(run_id))
        if run is None:
            return
        await process_run_and_maybe_analyze(session, run)


async def apply_profile_update(session: AsyncSession, account: Account, user_id: uuid.UUID) -> None:
    """Core enrichment logic, isolated from session/queue plumbing for testability (mirrors
    `process_run`). Fetch failure leaves the row usable (handle only) and never raises —
    the caller's `add_accounts` request must never block on this."""
    settings = get_settings()
    platform = get_platform(PlatformSlug.instagram)
    try:
        profile = await platform.fetch_profile(account)
    except Exception:  # noqa: BLE001
        return

    account.followers_count = profile.followers_count
    account.display_name = profile.display_name
    account.avatar_url = profile.avatar_url
    account.followers_updated_at = datetime.now(UTC)
    session.add(
        UsageEvent(
            user_id=user_id,
            kind=KIND_APIFY_RESULT,
            quantity=1,
            unit_cost_usd=Decimal(str(settings.apify_unit_cost_usd)),
        )
    )
    await session.commit()


async def fetch_account_profile(ctx: dict, account_id: str, user_id: str) -> None:
    """Background enrichment on account add (E2-S3) — separate from the analysis run
    lifecycle, so a competitor list fills in name/avatar/followers without waiting for a run."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        account = await session.get(Account, uuid.UUID(account_id))
        if account is None:
            return
        await apply_profile_update(session, account, uuid.UUID(user_id))


async def check_scheduled_runs(ctx: dict) -> None:
    """arq cron tick (E14-S2) — fires any ScheduledRun due in the current 5-minute window."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await fire_due_schedules(session)


class WorkerSettings:
    functions = [run_analysis, fetch_account_profile]
    cron_jobs = [cron(check_scheduled_runs, minute=set(range(0, 60, 5)), second=0)]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = get_settings().worker_job_timeout_secs
    # D44/E20-S2: sized against the confirmed 25-concurrent-Apify-run ceiling — see
    # Settings.worker_max_jobs for the worst-case math (previously arq's unset default of 10
    # allowed up to 50 simultaneous Apify calls, already 2x the real ceiling).
    max_jobs = get_settings().worker_max_jobs
