"""Telegram bot notification on run completion (E8-S2, D27).

Sends a message to the requesting user's linked Telegram account when a run
finishes (done or failed). Failure is always non-fatal — it is logged and
swallowed so the run result is never affected.
"""

import html
import logging

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.models import (
    Account,
    AnalysisRun,
    ContentItem,
    DeepAnalysis,
    DeepAnalysisItem,
    DeepAnalysisStatus,
    RunStatus,
    User,
)
from src.services.metrics import virality_baseline_subquery, virality_ratio_expr

logger = logging.getLogger(__name__)

_BOT_API = "https://api.telegram.org/bot{token}/sendMessage"
_TOP_ITEMS_LIMIT = 3


def _esc(text: str) -> str:
    return html.escape(text, quote=False)


async def _top_items_lines(session: AsyncSession, run: AnalysisRun) -> list[str]:
    """Plain-text (no KPIs) rundown of the run's top posts by virality, for the bot
    message — same ranking as the run detail page's Summary tab (api/items.py's
    top-virality endpoint), just formatted as readable lines instead of a JSON payload."""
    settings = get_settings()
    virality_subq = virality_baseline_subquery(ContentItem.run_id == run.id)
    virality_expr = virality_ratio_expr(
        virality_subq.c.median_engagement,
        virality_subq.c.median_views,
        virality_subq.c.item_count,
        settings,
    )
    stmt = (
        select(ContentItem.summary, ContentItem.url, Account.handle)
        .join(Account, ContentItem.account_id == Account.id)
        .join(
            virality_subq,
            (virality_subq.c.account_id == ContentItem.account_id)
            & (virality_subq.c.run_id == ContentItem.run_id),
        )
        .where(ContentItem.run_id == run.id, virality_expr.isnot(None))
        .order_by(virality_expr.desc())
        .limit(_TOP_ITEMS_LIMIT)
    )
    rows = (await session.execute(stmt)).all()

    lines = []
    for summary, url, handle in rows:
        caption = _esc(summary) if summary else "—"
        # No leading bullet (E22-S1, user-confirmed) — each line already opens with @handle,
        # visually distinct enough on its own.
        line = f"<b>@{_esc(handle)}</b>: {caption}"
        if url:
            line += f' (<a href="{html.escape(url, quote=True)}">пост</a>)'
        lines.append(line)
    return lines


async def notify_run_complete(run: AnalysisRun, user: User, session: AsyncSession) -> None:
    """Send a Telegram DM if the user has a linked telegram_id. Never raises."""
    settings = get_settings()
    if not settings.telegram_bot_token or user.telegram_id is None:
        return

    balance_line = f"Баланс токенов: <b>{user.token_balance}</b>"

    if run.status == RunStatus.done:
        accounts = run.progress_accounts or 0
        items = run.progress_items or 0
        # progress_items is the total scraped count, not what actually got charged — a
        # token-balance exhaustion mid-run can summarize (and charge) fewer items than were
        # scraped, and progress_items is never adjusted down to reflect that. progress_summarized
        # is the real per-batch-debited count (worker.py's _finish_run), the correct field here.
        tokens_spent = run.progress_summarized or 0
        link = f"{settings.web_url.rstrip('/')}/projects/{run.project_id}/runs/{run.id}"

        parts = [
            "✅ Задача «Ревью» завершена!",
            f"- Аккаунтов проверено: <b>{accounts}</b>\n- Публикаций найдено: <b>{items}</b>",
        ]
        if run.summary_text:
            parts.append(f"<b>Резюме</b>\n{_esc(run.summary_text)}")

        top_lines = await _top_items_lines(session, run)
        if top_lines:
            parts.append("<b>Топ публикации по виральности</b>\n" + "\n".join(top_lines))

        parts.append(f'<a href="{link}">Открыть результаты →</a>')
        parts.append(f"Потрачено токенов: <b>{tokens_spent}</b>\n{balance_line}")
        text = "\n\n".join(parts)
    else:
        error = _esc((run.error_message or "—")[:200])
        text = f"❌ Задача «Ревью» завершилась с ошибкой.\n\n{error}\n\n{balance_line}"

    await _send(settings, user, text)


async def notify_deep_analysis_complete(
    analysis: DeepAnalysis, run: AnalysisRun, user: User, session: AsyncSession
) -> None:
    """Sent when a deep_analysis run's full pipeline (scrape -> comments -> synthesis)
    finishes, not just its base scrape. `notify_run_complete` above fires immediately after
    the base scrape for `stat_collection` runs; for `deep_analysis` runs that notification is
    deliberately skipped (see worker.py's `process_run`) and this one fires instead, once the
    Разбор itself is actually done — otherwise the user got a "done" DM for a Review-shaped
    summary of a run they asked to Analyze, minutes before the real result was ready."""
    settings = get_settings()
    if not settings.telegram_bot_token or user.telegram_id is None:
        return

    balance_line = f"Баланс токенов: <b>{user.token_balance}</b>"

    if analysis.status == DeepAnalysisStatus.done:
        comments_count = await session.scalar(
            select(func.coalesce(func.sum(DeepAnalysisItem.comments_analyzed_count), 0)).where(
                DeepAnalysisItem.deep_analysis_id == analysis.id
            )
        )
        link = (
            f"{settings.web_url.rstrip('/')}/projects/{run.project_id}/deep-analyses/{analysis.id}"
        )
        parts = [
            "✅ Разбор завершён!",
            (
                f"Аккаунтов проверено: <b>{run.progress_accounts or 0}</b> · "
                f"публикаций: <b>{run.progress_items or 0}</b> · "
                f"комментариев: <b>{comments_count or 0}</b>"
            ),
            f"Токенов потрачено: <b>{analysis.tokens_charged}</b>",
            f'<a href="{link}">Открыть разбор →</a>',
            balance_line,
        ]
        text = "\n\n".join(parts)
    else:
        error = _esc((analysis.error_message or "—")[:200])
        text = f"❌ Разбор завершился с ошибкой.\n\n{error}\n\n{balance_line}"

    await _send(settings, user, text)


async def _send(settings: Settings, user: User, text: str) -> None:
    try:
        url = _BOT_API.format(token=settings.telegram_bot_token)
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                url,
                json={
                    "chat_id": user.telegram_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Telegram notification failed (non-fatal): %s", exc)
