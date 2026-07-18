import uuid
from datetime import UTC, datetime, timedelta

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import get_sessionmaker
from src.models import AnalysisRun, ContentItem, PlatformSlug, RunStatus
from src.platforms import get_platform
from src.services.runs import resolve_target_accounts


async def process_run(session: AsyncSession, run: AnalysisRun) -> None:
    """Core run lifecycle logic, isolated from session/queue plumbing for testability."""
    try:
        run.status = RunStatus.scraping
        run.started_at = datetime.now(UTC)
        await session.commit()

        accounts = await resolve_target_accounts(session, run.project_id, run.account_ids)
        since = run.started_at - timedelta(days=run.duration_days)
        platform = get_platform(PlatformSlug.instagram)

        items_found = 0
        for account in accounts:
            raw_items = await platform.fetch_content(account, since)
            for raw in raw_items:
                session.add(
                    ContentItem(
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
                )
                items_found += 1
            run.progress_accounts += 1
            run.progress_items = items_found
            await session.commit()

        # Real summarization lands in E4-S1/E4-S2; this phase is a pass-through for now.
        run.status = RunStatus.summarizing
        await session.commit()

        run.status = RunStatus.done
        run.finished_at = datetime.now(UTC)
        await session.commit()
    except Exception as exc:  # noqa: BLE001 — worker boundary: never let a run hang
        run.status = RunStatus.failed
        run.error_message = str(exc)[:1000]
        run.finished_at = datetime.now(UTC)
        await session.commit()


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
