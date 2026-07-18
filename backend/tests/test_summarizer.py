from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import KIND_CLAUDE_INPUT_TOKENS, KIND_CLAUDE_OUTPUT_TOKENS, UsageEvent
from src.services.summarizer import FALLBACK_TEXT, summarize_run_items
from tests.conftest import make_content_item, make_run, make_user


def _fake_response(text: str, input_tokens: int = 120, output_tokens: int = 40):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


class _FakeMessages:
    def __init__(self, response=None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        return self._response


class _FakeClient:
    def __init__(self, response=None, exc: Exception | None = None) -> None:
        self.messages = _FakeMessages(response, exc)


async def test_summarize_writes_summary_and_usage_events(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Смешное видео про котов")
    item.cover_url = None
    await session.commit()

    fake_client = _FakeClient(_fake_response("Видео про котов, которые играют."))
    with patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client):
        await summarize_run_items(session, [item], user_id=user.id, run_id=run.id)

    assert item.summary == "Видео про котов, которые играют."
    assert len(fake_client.messages.calls) == 1

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    kinds = {u.kind: u.quantity for u in usage}
    assert kinds[KIND_CLAUDE_INPUT_TOKENS] == 120
    assert kinds[KIND_CLAUDE_OUTPUT_TOKENS] == 40


async def test_summarize_no_caption_no_image_skips_api_call(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption=None)
    item.cover_url = None
    await session.commit()

    fake_client = _FakeClient()
    with patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client):
        await summarize_run_items(session, [item], user_id=user.id, run_id=run.id)

    assert item.summary == FALLBACK_TEXT
    assert fake_client.messages.calls == []


async def test_summarize_retries_then_falls_back(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись без изображения")
    item.cover_url = None
    await session.commit()

    fake_client = _FakeClient(exc=RuntimeError("rate limited"))
    with (
        patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client),
        patch("src.services.summarizer.asyncio.sleep", new_callable=AsyncMock),
    ):
        await summarize_run_items(session, [item], user_id=user.id, run_id=run.id)

    assert item.summary == FALLBACK_TEXT
    assert len(fake_client.messages.calls) == 3

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert usage == []


async def test_summarize_skips_unfetchable_image_and_uses_text_only(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = "https://example.com/broken.jpg"
    await session.commit()

    fake_client = _FakeClient(_fake_response("Краткое описание."))
    with (
        patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client),
        patch("src.services.summarizer._fetch_image_block", new=AsyncMock(return_value=None)),
    ):
        await summarize_run_items(session, [item], user_id=user.id, run_id=run.id)

    assert item.summary == "Краткое описание."
    sent_content = fake_client.messages.calls[0]["messages"][0]["content"]
    assert len(sent_content) == 1
    assert sent_content[0]["type"] == "text"
