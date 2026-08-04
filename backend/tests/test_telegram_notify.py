"""Unit tests for Telegram run-complete notification (E8-S2)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import AnalysisRun, ContentType, DeepAnalysis, DeepAnalysisStatus, RunStatus, User
from src.services.telegram_notify import (
    _top_items_lines,
    notify_deep_analysis_complete,
    notify_run_complete,
)
from tests.conftest import (
    make_account,
    make_account_list,
    make_content_item,
    make_project,
    make_run,
    make_user,
    make_workspace,
)


def _make_run(
    status: RunStatus,
    items: int = 5,
    error: str | None = None,
    progress_summarized: int | None = None,
) -> AnalysisRun:
    run = MagicMock(spec=AnalysisRun)
    run.id = uuid.uuid4()
    run.project_id = uuid.uuid4()
    run.status = status
    run.progress_accounts = 2
    run.progress_items = items
    # Defaults to items (the common case: nothing truncated) unless a test wants to prove the
    # two counters diverge (E22-S1 — progress_items is never adjusted down on a mid-run
    # token-balance exhaustion, so it's the wrong field for "tokens actually spent").
    run.progress_summarized = progress_summarized if progress_summarized is not None else items
    run.error_message = error
    run.summary_text = None
    return run


def _make_deep_analysis(
    status: DeepAnalysisStatus, tokens_charged: int = 90, error: str | None = None
) -> DeepAnalysis:
    analysis = MagicMock(spec=DeepAnalysis)
    analysis.id = uuid.uuid4()
    analysis.status = status
    analysis.tokens_charged = tokens_charged
    analysis.error_message = error
    return analysis


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
        mock_top.return_value = ["<b>@natgeo</b>: Отличный ролик про океан"]
        await notify_run_complete(run, user, MagicMock())

    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    payload = call_kwargs["json"]
    assert payload["chat_id"] == 99999
    text = payload["text"]
    # E22-S1 target format
    assert "✅ Задача «Ревью» завершена!" in text
    assert "- Аккаунтов проверено: <b>2</b>" in text
    assert "- Публикаций найдено: <b>42</b>" in text
    assert "<b>Резюме</b>" in text
    assert run.summary_text in text
    assert "<b>Топ публикации по виральности</b>" in text
    assert "natgeo" in text
    # E15-S3: links to the run detail page, not the old /results?run=... query param
    assert f"https://example.com/projects/{run.project_id}/runs/{run.id}" in text
    assert "Потрачено токенов: <b>42</b>" in text
    assert "358" in text


@pytest.mark.asyncio
async def test_notify_done_tokens_spent_uses_progress_summarized_not_progress_items():
    """E22-S1 real finding: progress_items is the total scraped count, never adjusted down when
    a mid-run token-balance exhaustion summarizes (and charges) fewer items than were scraped —
    progress_summarized is the field that actually tracks what got charged."""
    run = _make_run(RunStatus.done, items=50, progress_summarized=30)
    user = _make_user(telegram_id=99999, token_balance=0)

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
        mock_top.return_value = []
        await notify_run_complete(run, user, MagicMock())

    payload = mock_post.call_args[1]["json"]
    text = payload["text"]
    assert "- Публикаций найдено: <b>50</b>" in text
    assert "Потрачено токенов: <b>30</b>" in text


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
    assert "❌ Задача «Ревью» завершилась с ошибкой." in payload["text"]
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


# --- notify_deep_analysis_complete (E20-S3 follow-up: deferred deep-analysis notification) -


@pytest.mark.asyncio
async def test_notify_deep_analysis_done_sends_message_with_link():
    run = _make_run(RunStatus.done, items=15)
    analysis = _make_deep_analysis(DeepAnalysisStatus.done, tokens_charged=225)
    user = _make_user(telegram_id=99999, token_balance=775)

    mock_session = AsyncMock()
    mock_session.scalar = AsyncMock(return_value=150)

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
        await notify_deep_analysis_complete(analysis, run, user, mock_session)

    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["json"]
    assert payload["chat_id"] == 99999
    assert "15" in payload["text"]  # publications
    assert "150" in payload["text"]  # comments analyzed
    assert "225" in payload["text"]  # tokens charged
    assert "775" in payload["text"]  # balance
    assert (
        f"https://example.com/projects/{run.project_id}/deep-analyses/{analysis.id}"
        in (payload["text"])
    )


@pytest.mark.asyncio
async def test_notify_deep_analysis_failed_sends_error_message():
    run = _make_run(RunStatus.done, items=15)
    analysis = _make_deep_analysis(DeepAnalysisStatus.failed, error="Не удалось сформировать отчёт")
    user = _make_user(telegram_id=88888, token_balance=100)

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
        await notify_deep_analysis_complete(analysis, run, user, AsyncMock())

    payload = mock_post.call_args[1]["json"]
    assert "Не удалось сформировать отчёт" in payload["text"]
    assert "100" in payload["text"]


@pytest.mark.asyncio
async def test_notify_deep_analysis_skipped_when_no_telegram_id():
    run = _make_run(RunStatus.done)
    analysis = _make_deep_analysis(DeepAnalysisStatus.done)
    user = _make_user(telegram_id=None)
    with patch("src.services.telegram_notify.httpx.AsyncClient") as mock_client:
        await notify_deep_analysis_complete(analysis, run, user, AsyncMock())
    mock_client.assert_not_called()


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
