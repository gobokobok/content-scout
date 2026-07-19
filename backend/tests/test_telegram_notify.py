"""Unit tests for Telegram run-complete notification (E8-S2)."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import AnalysisRun, RunStatus, User
from src.services.telegram_notify import notify_run_complete


def _make_run(status: RunStatus, items: int = 5, error: str | None = None) -> AnalysisRun:
    run = MagicMock(spec=AnalysisRun)
    run.id = uuid.uuid4()
    run.project_id = uuid.uuid4()
    run.status = status
    run.progress_items = items
    run.error_message = error
    return run


def _make_user(telegram_id: int | None) -> User:
    user = MagicMock(spec=User)
    user.telegram_id = telegram_id
    return user


@pytest.mark.asyncio
async def test_notify_skipped_when_no_telegram_id():
    """No HTTP call when user has no linked telegram_id."""
    run = _make_run(RunStatus.done)
    user = _make_user(telegram_id=None)
    with patch("src.services.telegram_notify.httpx.AsyncClient") as mock_client:
        await notify_run_complete(run, user)
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_notify_skipped_when_no_bot_token():
    """No HTTP call when TELEGRAM_BOT_TOKEN is empty."""
    run = _make_run(RunStatus.done)
    user = _make_user(telegram_id=12345)
    with (
        patch("src.services.telegram_notify.get_settings") as mock_settings,
        patch("src.services.telegram_notify.httpx.AsyncClient") as mock_client,
    ):
        mock_settings.return_value.telegram_bot_token = ""
        await notify_run_complete(run, user)
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_notify_done_sends_message_with_link():
    """On done: sends a message containing item count and web link."""
    run = _make_run(RunStatus.done, items=42)
    user = _make_user(telegram_id=99999)

    mock_post = AsyncMock()
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = mock_post

    with (
        patch("src.services.telegram_notify.get_settings") as mock_settings,
        patch("src.services.telegram_notify.httpx.AsyncClient", return_value=mock_http),
    ):
        mock_settings.return_value.telegram_bot_token = "token123"
        mock_settings.return_value.web_url = "https://example.com"
        await notify_run_complete(run, user)

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    payload = call_kwargs["json"]
    assert payload["chat_id"] == 99999
    assert "42" in payload["text"]
    assert "example.com" in payload["text"]


@pytest.mark.asyncio
async def test_notify_failed_sends_error_message():
    """On failed: sends a message with the error."""
    run = _make_run(RunStatus.failed, error="Тестовая ошибка")
    user = _make_user(telegram_id=88888)

    mock_post = AsyncMock()
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = mock_post

    with (
        patch("src.services.telegram_notify.get_settings") as mock_settings,
        patch("src.services.telegram_notify.httpx.AsyncClient", return_value=mock_http),
    ):
        mock_settings.return_value.telegram_bot_token = "token123"
        mock_settings.return_value.web_url = "https://example.com"
        await notify_run_complete(run, user)

    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert "Тестовая ошибка" in payload["text"]


@pytest.mark.asyncio
async def test_notify_http_failure_is_swallowed():
    """Network errors never propagate — notify_run_complete always returns normally."""
    run = _make_run(RunStatus.done)
    user = _make_user(telegram_id=77777)

    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = AsyncMock(side_effect=Exception("network error"))

    with (
        patch("src.services.telegram_notify.get_settings") as mock_settings,
        patch("src.services.telegram_notify.httpx.AsyncClient", return_value=mock_http),
    ):
        mock_settings.return_value.telegram_bot_token = "token123"
        mock_settings.return_value.web_url = "https://example.com"
        # Must not raise
        await notify_run_complete(run, user)
