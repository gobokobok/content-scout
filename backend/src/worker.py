import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
from anthropic import AsyncAnthropic
from arq.connections import RedisSettings
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import get_sessionmaker
from src.models import (
    KIND_APIFY_RESULT,
    AccountStatus,
    AnalysisRun,
    ContentItem,
    PlatformSlug,
    RunStatus,
    UsageEvent,
    User,
)
from src.platforms import get_platform
from src.services.runs import resolve_target_accounts
from src.services.summarizer import summarize_run_items
from src.services.telegram_notify import notify_run_complete
from src.services.usage import rollup_run_totals

_SUMMARIZER_HTTP_TIMEOUT = 10.0


async def process_run(session: AsyncSession, run: AnalysisRun) -> None:
    """Core run lifecycle logic, isolated from session/queue plumbing for testability."""
    try:
        run.status = RunStatus.scraping
        run.started_at = datetime.now(UTC)
        await session.commit()

        accounts = await resolve_target_accounts(session, run.project_id, run.account_ids)
        since = run.started_at - timedelta(days=run.duration_days)
        platform = get_platform(PlatformSlug.instagram)
        settings = get_settings()
        semaphore = asyncio.Semaphore(settings.scrape_concurrency)

        async def _fetch_one(account):
            async with semaphore:
                try:
                    return account, await platform.fetch_content(account, since), None
                except Exception as exc:  # noqa: BLE001
                    return account, None, exc

        fetch_results = await asyncio.gather(*(_fetch_one(a) for a in accounts))

        items_found = 0
        for account, raw_items, exc in fetch_results:
            if exc is not None:
                account.status = AccountStatus.failed
                account.fail_reason = str(exc)[:500]
            else:
                for raw in raw_items:
                    await session.execute(
                        pg_insert(ContentItem).values(
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
                        ).on_conflict_do_nothing(index_elements=["run_id", "external_id"])
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

        for start in range(0, len(pending_items), batch_size):
            batch = pending_items[start : start + batch_size]
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
            await session.commit()

        await anthropic_client.close()
        await http_client.aclose()

        await rollup_run_totals(session, run)
        run.status = RunStatus.done
        run.finished_at = datetime.now(UTC)
        await session.commit()
        requesting_user = await session.get(User, run.requested_by)
        if requesting_user:
            await notify_run_complete(run, requesting_user)

    except asyncio.CancelledError:
        run.status = RunStatus.failed
        run.error_message = "Превышено время выполнения"
        run.finished_at = datetime.now(UTC)
        await asyncio.shield(session.commit())
        try:
            requesting_user = await session.get(User, run.requested_by)
            if requesting_user:
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
            if requesting_user:
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


class WorkerSettings:
    functions = [run_analysis]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    job_timeout = get_settings().worker_job_timeout_secs
