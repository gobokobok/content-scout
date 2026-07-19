"""Telegram bot notification on run completion (E8-S2, D27).

Sends a message to the requesting user's linked Telegram account when a run
finishes (done or failed). Failure is always non-fatal — it is logged and
swallowed so the run result is never affected.
"""
import logging

import httpx

from src.config import get_settings
from src.models import AnalysisRun, RunStatus, User

logger = logging.getLogger(__name__)

_BOT_API = "https://api.telegram.org/bot{token}/sendMessage"


async def notify_run_complete(run: AnalysisRun, user: User) -> None:
    """Send a Telegram DM if the user has a linked telegram_id. Never raises."""
    settings = get_settings()
    if not settings.telegram_bot_token or user.telegram_id is None:
        return

    if run.status == RunStatus.done:
        items = run.progress_items or 0
        link = f"{settings.web_url.rstrip('/')}/projects/{run.project_id}/results?run={run.id}"
        text = (
            f"✅ Анализ завершён!\n\n"
            f"Найдено публикаций: <b>{items}</b>\n\n"
            f'<a href="{link}">Открыть результаты</a>'
        )
    else:
        error = (run.error_message or "—")[:200]
        text = f"❌ Анализ завершился с ошибкой.\n\n{error}"

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
