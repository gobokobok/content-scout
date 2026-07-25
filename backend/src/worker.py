import asyncio
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
    PlatformSlug,
    RunStatus,
    UsageEvent,
    User,
)
from src.platforms import get_platform
from src.services.run_summary import generate_run_summary
from src.services.runs import resolve_target_accounts
from src.services.scheduled_runs import fire_due_schedules
from src.services.summarizer import summarize_run_items
from src.services.telegram_notify import notify_run_complete
from src.services.usage import rollup_run_totals

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
            else:
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
            await notify_run_complete(run, requesting_user)

    except asyncio.CancelledError:
        run.status = RunStatus.failed
        run.error_message = "Превышено время выполнения"
        run.finished_at = datetime.now(UTC)
        await asyncio.shield(session.commit())
        try:
            requesting_user = await session.get(User, run.requested_by)
            if requesting_user and run.notify_on_complete:
                await notify_run_complete(run, requesting_user)
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
                await notify_run_complete(run, requesting_user)
        except Exception:  # noqa: BLE001
            pass


async def run_analysis(ctx: dict, run_id: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        run = await session.get(AnalysisRun, uuid.UUID(run_id))
        if run is None:
            return
        await process_run(session, run)


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
