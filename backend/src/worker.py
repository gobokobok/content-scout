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

from src.config import get_settings
from src.db import get_sessionmaker
from src.models import (
    KIND_APIFY_RESULT,
    Account,
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
from src.services.deep_analysis import (
    InsufficientTokenBalanceError,
    fail_deep_analysis,
    start_deep_analysis,
)
from src.services.deep_analysis_extraction import extract_deep_analysis_items
from src.services.deep_analysis_synthesis import synthesize_report
from src.services.queue import enqueue_deep_analysis
from src.services.run_summary import generate_run_summary
from src.services.runs import resolve_target_accounts
from src.services.scheduled_runs import fire_due_schedules
from src.services.summarizer import summarize_run_items
from src.services.telegram_notify import notify_run_complete
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


async def process_run(session: AsyncSession, run: AnalysisRun) -> None:
    """Core run lifecycle logic, isolated from session/queue plumbing for testability."""
    try:
        run.status = RunStatus.scraping
        run.started_at = datetime.now(UTC)
        await session.commit()

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
        platform = get_platform(PlatformSlug.instagram)
        settings = get_settings()
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

        run.status = RunStatus.summarizing
        await session.commit()

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

        requesting_user = await session.get(User, run.requested_by)
        token_balance_exhausted = False

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
        if requesting_user and run.notify_on_complete:
            await notify_run_complete(run, requesting_user, session)

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


async def maybe_start_deep_analysis(session: AsyncSession, run: AnalysisRun) -> None:
    """Auto-chain (nav overhaul, E17 follow-up): a "deep_analysis"-type run immediately starts
    and enqueues a DeepAnalysis once its base scrape finishes cleanly — no separate user step.
    Never raises: a soft-fail here (insufficient tokens, a DB/queue hiccup, a misconfigured
    comment vendor) leaves the scrape result intact and analyzable manually later. Always
    logged, and — unlike the original version of this function — always recorded on the run
    itself via deep_analysis_skip_reason: a bare `except: pass` here previously made a skipped
    chain indistinguishable from a run that was never meant to have one, with zero trace once
    the log line scrolled out of Railway's retention window.
    """
    if run.run_type != "deep_analysis" or run.status != RunStatus.done:
        return
    try:
        user = await session.get(User, run.requested_by)
        if user is None:
            return
        settings = get_settings()
        analysis = await start_deep_analysis(session, run, user, settings)
        run.deep_analysis_skip_reason = None
        await session.commit()
        await enqueue_deep_analysis(analysis.id)
    except InsufficientTokenBalanceError:
        logger.info("Skipping auto deep-analysis for run_id=%s: insufficient token balance", run.id)
        run.deep_analysis_skip_reason = "insufficient_tokens"
        await session.commit()
    except Exception:  # noqa: BLE001 — logged, never lets chaining fail the base run
        logger.exception("Auto deep-analysis chaining failed for run_id=%s", run.id)
        run.deep_analysis_skip_reason = "error"
        await session.commit()


async def run_analysis(ctx: dict, run_id: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        run = await session.get(AnalysisRun, uuid.UUID(run_id))
        if run is None:
            return
        await process_run(session, run)
        await maybe_start_deep_analysis(session, run)


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


async def process_deep_analysis(session: AsyncSession, analysis: DeepAnalysis) -> None:
    """Core deep-analysis lifecycle logic, isolated from session/queue plumbing for
    testability (mirrors `process_run`): extracting (E17-S3) -> synthesizing (E17-S4) ->
    done/failed. Tokens are already deducted up front by `services/deep_analysis.py:
    start_deep_analysis` before this job is even enqueued."""
    try:
        analysis.status = DeepAnalysisStatus.extracting
        await session.commit()

        items = list(
            await session.scalars(select(ContentItem).where(ContentItem.run_id == analysis.run_id))
        )
        await extract_deep_analysis_items(
            session, analysis.id, items, user_id=analysis.requested_by
        )
        await session.commit()

        analysis.status = DeepAnalysisStatus.synthesizing
        await session.commit()

        await synthesize_report(session, analysis, user_id=analysis.requested_by)
        await session.commit()
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
        raise
    except Exception as exc:  # noqa: BLE001 — worker boundary: never let a deep analysis hang
        await fail_deep_analysis(session, analysis, str(exc), user_id=analysis.requested_by)
        await session.commit()


async def run_deep_analysis(ctx: dict, deep_analysis_id: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        analysis = await session.get(DeepAnalysis, uuid.UUID(deep_analysis_id))
        if analysis is None:
            return
        await process_deep_analysis(session, analysis)


class WorkerSettings:
    functions = [run_analysis, fetch_account_profile, run_deep_analysis]
    cron_jobs = [cron(check_scheduled_runs, minute=set(range(0, 60, 5)), second=0)]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = get_settings().worker_job_timeout_secs
    # D44/E20-S2: sized against the confirmed 25-concurrent-Apify-run ceiling — see
    # Settings.worker_max_jobs for the worst-case math (previously arq's unset default of 10
    # allowed up to 50 simultaneous Apify calls, already 2x the real ceiling).
    max_jobs = get_settings().worker_max_jobs
