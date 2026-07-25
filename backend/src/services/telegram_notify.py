"""Telegram bot notification on run completion (E8-S2, D27).

Sends a message to the requesting user's linked Telegram account when a run
finishes (done or failed). Failure is always non-fatal — it is logged and
swallowed so the run result is never affected.
"""

import html
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models import Account, AnalysisRun, ContentItem, RunStatus, User
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
        line = f"• <b>@{_esc(handle)}</b>: {caption}"
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
        link = f"{settings.web_url.rstrip('/')}/projects/{run.project_id}/runs/{run.id}"

        parts = [
            "✅ Анализ завершён!",
            f"Аккаунтов проверено: <b>{accounts}</b> · публикаций найдено: <b>{items}</b>",
        ]
        if run.summary_text:
            parts.append(_esc(run.summary_text))

        top_lines = await _top_items_lines(session, run)
        if top_lines:
            parts.append("Топ публикации:\n" + "\n".join(top_lines))

        parts.append(f'<a href="{link}">Открыть результаты →</a>')
        parts.append(balance_line)
        text = "\n\n".join(parts)
    else:
        error = _esc((run.error_message or "—")[:200])
        text = f"❌ Анализ завершился с ошибкой.\n\n{error}\n\n{balance_line}"

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
