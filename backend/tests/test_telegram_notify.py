"""Unit tests for Telegram run-complete notification (E8-S2)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AnalysisRun, ContentType, RunStatus, User
from src.services.telegram_notify import _top_items_lines, notify_run_complete
from tests.conftest import (
    make_account,
    make_account_list,
    make_content_item,
    make_project,
    make_run,
    make_user,
    make_workspace,
)


def _make_run(status: RunStatus, items: int = 5, error: str | None = None) -> AnalysisRun:
    run = MagicMock(spec=AnalysisRun)
    run.id = uuid.uuid4()
    run.project_id = uuid.uuid4()
    run.status = status
    run.progress_accounts = 2
    run.progress_items = items
    run.error_message = error
    run.summary_text = None
    return run


def _make_user(telegram_id: int | None, token_balance: int = 100) -> User:
    user = MagicMock(spec=User)
    user.telegram_id = telegram_id
    user.token_balance = token_balance
    return user


@pytest.mark.asyncio
async def test_notify_skipped_when_no_telegram_id():
    """No HTTP call when user has no linked telegram_id."""
    run = _make_run(RunStatus.done)
    user = _make_user(telegram_id=None)
    with patch("src.services.telegram_notify.httpx.AsyncClient") as mock_client:
        await notify_run_complete(run, user, MagicMock())
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
        await notify_run_complete(run, user, MagicMock())
    mock_client.assert_not_called()


@pytest.mark.asyncio
async def test_notify_done_sends_message_with_link():
    """On done: sends a message containing account/item counts, balance, and web link."""
    run = _make_run(RunStatus.done, items=42)
    run.summary_text = "Конкуренты делают ставку на короткие видео."
    user = _make_user(telegram_id=99999, token_balance=358)

    mock_post = AsyncMock()
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    mock_http.post = mock_post

    with (
        patch("src.services.telegram_notify.get_settings") as mock_settings,
        patch("src.services.telegram_notify.httpx.AsyncClient", return_value=mock_http),
        patch("src.services.telegram_notify._top_items_lines", new_callable=AsyncMock) as mock_top,
    ):
        mock_settings.return_value.telegram_bot_token = "token123"
        mock_settings.return_value.web_url = "https://example.com"
        mock_top.return_value = ["• <b>@natgeo</b>: Отличный ролик про океан"]
        await notify_run_complete(run, user, MagicMock())

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    payload = call_kwargs["json"]
    assert payload["chat_id"] == 99999
    assert "42" in payload["text"]
    assert "2" in payload["text"]  # progress_accounts
    assert run.summary_text in payload["text"]
    assert "natgeo" in payload["text"]
    # E15-S3: links to the run detail page, not the old /results?run=... query param
    assert f"https://example.com/projects/{run.project_id}/runs/{run.id}" in payload["text"]
    assert "358" in payload["text"]


@pytest.mark.asyncio
async def test_notify_failed_sends_error_message():
    """On failed: sends a message with the error and balance, no top-items lookup."""
    run = _make_run(RunStatus.failed, error="Тестовая ошибка")
    user = _make_user(telegram_id=88888, token_balance=12)

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
        await notify_run_complete(run, user, MagicMock())

    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert "Тестовая ошибка" in payload["text"]
    assert "12" in payload["text"]


@pytest.mark.asyncio
async def test_notify_html_special_chars_are_escaped():
    """A caption/error containing HTML metacharacters must not break Telegram's HTML parser."""
    run = _make_run(RunStatus.failed, error="<script>alert(1)</script> & друзья")
    user = _make_user(telegram_id=55555)

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
        await notify_run_complete(run, user, MagicMock())

    payload = mock_post.call_args[1]["json"]
    assert "<script>" not in payload["text"]
    assert "&lt;script&gt;" in payload["text"]
    assert "&amp; друзья" in payload["text"]


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
        patch("src.services.telegram_notify._top_items_lines", new_callable=AsyncMock) as mock_top,
    ):
        mock_settings.return_value.telegram_bot_token = "token123"
        mock_settings.return_value.web_url = "https://example.com"
        mock_top.return_value = []
        # Must not raise
        await notify_run_complete(run, user, MagicMock())


# --- _top_items_lines against a real DB (virality ranking + formatting) --------------------


async def test_top_items_lines_orders_by_virality_and_formats_plain_text(
    session: AsyncSession,
) -> None:
    owner = await make_user(session)
    ws = await make_workspace(session, owner=owner)
    project = await make_project(session, workspace=ws)
    account_list = await make_account_list(session, project=project)
    viral_account = await make_account(session, account_list=account_list, handle="viral_star")
    quiet_account = await make_account(session, account_list=account_list, handle="quiet_one")
    run = await make_run(session, project=project, requested_by=owner)

    now = datetime.now(UTC)
    for i in range(3):
        await make_content_item(
            session,
            run=run,
            account=viral_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=100,
            comments=0,
            views=None,
            summary=f"Baseline {i}",
        )
    await make_content_item(
        session,
        run=run,
        account=viral_account,
        type=ContentType.post,
        published_at=now - timedelta(days=1),
        likes=900,
        comments=0,
        views=None,
        summary="Прорывной ролик недели",
    )
    # Below virality_min_items=3 — must be excluded even though it's high-engagement.
    for i in range(2):
        await make_content_item(
            session,
            run=run,
            account=quiet_account,
            type=ContentType.post,
            published_at=now - timedelta(days=1),
            likes=10,
            comments=0,
            views=None,
            summary=f"Quiet {i}",
        )
    await session.commit()

    lines = await _top_items_lines(session, run)

    assert len(lines) == 3  # capped at _TOP_ITEMS_LIMIT; quiet account excluded regardless
    assert "Прорывной ролик недели" in lines[0]
    assert "@viral_star" in lines[0]
    assert not any("quiet_one" in line for line in lines)
    assert not any("Quiet" in line for line in lines)
