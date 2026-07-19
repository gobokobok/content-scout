from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import KIND_CLAUDE_INPUT_TOKENS, KIND_CLAUDE_OUTPUT_TOKENS, UsageEvent
from src.services.summarizer import FALLBACK_TEXT, summarize_run_items
from tests.conftest import (
    make_content_item,
    make_project,
    make_run,
    make_user,
    make_workspace,
)


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


# ---------------------------------------------------------------------------
# Existing tests (unchanged behaviour)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# E4-S3 new tests
# ---------------------------------------------------------------------------


async def test_cross_run_summary_reuse_skips_claude_call(session: AsyncSession) -> None:
    user = await make_user(session)
    workspace = await make_workspace(session, owner=user)
    project = await make_project(session, workspace=workspace)
    run1 = await make_run(session, project=project, requested_by=user)
    run2 = await make_run(session, project=project, requested_by=user)

    external_id = "post_abc123"
    prior_item = await make_content_item(
        session,
        run=run1,
        caption="Подпись",
        external_id=external_id,
        summary="Ранее готовое описание",
    )
    current_item = await make_content_item(
        session, run=run2, caption="Подпись", external_id=external_id
    )
    await session.commit()

    fake_client = _FakeClient(_fake_response("Новое описание"))
    with patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client):
        await summarize_run_items(
            session,
            [current_item],
            user_id=user.id,
            run_id=run2.id,
            project_id=project.id,
        )

    assert current_item.summary == prior_item.summary
    assert fake_client.messages.calls == []  # no Claude call

    # No usage events recorded for reused item
    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run2.id))).all()
    assert usage == []


async def test_cross_run_reuse_does_not_reuse_fallback(session: AsyncSession) -> None:
    user = await make_user(session)
    workspace = await make_workspace(session, owner=user)
    project = await make_project(session, workspace=workspace)
    run1 = await make_run(session, project=project, requested_by=user)
    run2 = await make_run(session, project=project, requested_by=user)

    external_id = "post_xyz789"
    await make_content_item(
        session,
        run=run1,
        caption="Подпись",
        external_id=external_id,
        summary=FALLBACK_TEXT,  # failed summarization — must not be reused
    )
    current_item = await make_content_item(
        session, run=run2, caption="Хорошая подпись", external_id=external_id
    )
    current_item.cover_url = None
    await session.commit()

    fresh_summary = "Свежее описание"
    fake_client = _FakeClient(_fake_response(fresh_summary))
    with patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client):
        await summarize_run_items(
            session,
            [current_item],
            user_id=user.id,
            run_id=run2.id,
            project_id=project.id,
        )

    assert current_item.summary == fresh_summary
    assert len(fake_client.messages.calls) == 1  # Claude was called (fallback not reused)


async def test_skip_image_when_caption_exceeds_threshold(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    long_caption = "А" * 201  # over the default 200-char threshold
    item = await make_content_item(session, run=run, caption=long_caption)
    item.cover_url = "https://example.com/img.jpg"
    await session.commit()

    fetch_calls: list = []

    async def _spy_fetch(http_client, url, settings=None):
        fetch_calls.append(url)
        return None

    fake_client = _FakeClient(_fake_response("Описание из длинной подписи"))
    with (
        patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client),
        patch("src.services.summarizer._fetch_image_block", side_effect=_spy_fetch),
    ):
        await summarize_run_items(session, [item], user_id=user.id, run_id=run.id)

    assert fetch_calls == []  # image fetch skipped entirely


async def test_short_caption_still_fetches_image(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Короткая подпись")
    item.cover_url = "https://example.com/img.jpg"
    await session.commit()

    fetch_calls: list = []

    async def _spy_fetch(http_client, url, settings=None):
        fetch_calls.append(url)
        return None  # return None so no image block is added (network not available in tests)

    fake_client = _FakeClient(_fake_response("Описание"))
    with (
        patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client),
        patch("src.services.summarizer._fetch_image_block", side_effect=_spy_fetch),
    ):
        await summarize_run_items(session, [item], user_id=user.id, run_id=run.id)

    assert fetch_calls == [item.cover_url]  # image fetch was attempted


async def test_batch_api_maps_results_to_summaries_and_usage(session: AsyncSession) -> None:
    """Message Batches path: results are mapped back to items and usage_events recorded."""
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    items = []
    for i in range(3):
        it = await make_content_item(session, run=run, caption=f"Подпись {i}")
        it.cover_url = None
        items.append(it)
    await session.commit()

    item_ids = [str(it.id) for it in items]

    def _batch_result(custom_id: str, text: str):
        return SimpleNamespace(
            custom_id=custom_id,
            result=SimpleNamespace(
                type="succeeded",
                message=SimpleNamespace(
                    content=[SimpleNamespace(type="text", text=text)],
                    usage=SimpleNamespace(input_tokens=80, output_tokens=25),
                ),
            ),
        )

    fake_batch = SimpleNamespace(id="batch_001", processing_status="ended")

    class _FakeBatches:
        async def create(self, requests):
            return fake_batch

        async def retrieve(self, batch_id):
            return fake_batch  # already "ended"

        async def results(self, batch_id):
            async def _gen():
                for idx, cid in enumerate(item_ids):
                    yield _batch_result(cid, f"Описание {idx}")

            return _gen()

    class _FakeBatchClient:
        def __init__(self):
            self.messages = SimpleNamespace(batches=_FakeBatches())

    fake_client = _FakeBatchClient()
    # Patch threshold to 2 so 3 items triggers the batch path
    from src.config import Settings, get_settings

    overridden = Settings(**{**get_settings().model_dump(), "summary_batch_threshold": 2})
    with (
        patch("src.services.summarizer.get_settings", return_value=overridden),
        patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client),
    ):
        await summarize_run_items(session, items, user_id=user.id, run_id=run.id)

    for idx, item in enumerate(items):
        assert item.summary == f"Описание {idx}"

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    # 3 items × 2 events (input + output tokens) each
    assert len(usage) == 6
    input_events = [u for u in usage if u.kind == KIND_CLAUDE_INPUT_TOKENS]
    assert all(u.quantity == 80 for u in input_events)


async def test_batch_failure_falls_back_to_concurrent_path(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    items = []
    for i in range(3):
        it = await make_content_item(session, run=run, caption=f"Подпись {i}")
        it.cover_url = None
        items.append(it)
    await session.commit()

    class _FakeBatches:
        async def create(self, requests):
            raise RuntimeError("batch API unavailable")

    class _FakeBatchClient:
        def __init__(self, response):
            self.messages = SimpleNamespace(
                batches=_FakeBatches(),
                create=AsyncMock(return_value=response),
            )
            # Concurrent path fallback uses messages.create() directly
            self.messages.create = _FakeMessages(response).create

    fallback_response = _fake_response("Резервное описание")

    class _FullFakeClient:
        def __init__(self):
            self.messages = SimpleNamespace(
                batches=_FakeBatches(),
                create=_FakeMessages(fallback_response).create,
            )

    fake_client = _FullFakeClient()
    from src.config import Settings, get_settings

    overridden = Settings(**{**get_settings().model_dump(), "summary_batch_threshold": 2})
    with (
        patch("src.services.summarizer.get_settings", return_value=overridden),
        patch("src.services.summarizer.AsyncAnthropic", return_value=fake_client),
    ):
        await summarize_run_items(session, items, user_id=user.id, run_id=run.id)

    # All items should have been summarized via the fallback concurrent path
    assert all(it.summary == "Резервное описание" for it in items)
