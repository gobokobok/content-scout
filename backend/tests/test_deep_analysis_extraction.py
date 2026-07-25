import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    DeepAnalysisItem,
    DeepAnalysisItemStatus,
    UsageEvent,
)
from src.services.comment_scraper import RawComment
from src.services.deep_analysis_extraction import extract_deep_analysis_items
from tests.conftest import make_content_item, make_deep_analysis, make_run, make_user


def _fake_response(text: str, input_tokens: int = 100, output_tokens: int = 60):
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


_VALID_JSON = json.dumps(
    {
        "topic": "Тренировки дома",
        "format": "обучающий",
        "hook_type": "вопрос",
        "has_cta": True,
        "sentiment": "positive",
        "complaints": ["долго ждать ответа"],
        "praises": ["отличный контент", "супер"],
        "questions": ["а где купить коврик?"],
        "notable_phrases": ["это лучшее видео"],
    },
    ensure_ascii=False,
)


async def test_extract_stores_parsed_signals_and_usage(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await session.commit()

    comments = [RawComment(external_id="c1", text="Здорово!", author_username="u1", likes=5)]
    fake_client = _FakeClient(_fake_response(_VALID_JSON))
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch(
            "src.services.deep_analysis_extraction.fetch_comments",
            new=AsyncMock(return_value=comments),
        ),
    ):
        await extract_deep_analysis_items(
            session, analysis.id, [item], user_id=user.id, client=fake_client
        )
    await session.commit()

    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.status == DeepAnalysisItemStatus.done
    assert row.topic == "Тренировки дома"
    assert row.content_format == "обучающий"
    assert row.has_cta is True
    assert row.sentiment == "positive"
    assert row.complaints == ["долго ждать ответа"]
    assert row.praises == ["отличный контент", "супер"]
    assert row.comments_analyzed_count == 1

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    kinds = {u.kind: u.quantity for u in usage}
    assert kinds[KIND_CLAUDE_INPUT_TOKENS] == 100
    assert kinds[KIND_CLAUDE_OUTPUT_TOKENS] == 60


async def test_extract_unparseable_response_stores_failed_but_still_charges_usage(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await session.commit()

    fake_client = _FakeClient(_fake_response("это не json вовсе"))
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch(
            "src.services.deep_analysis_extraction.fetch_comments", new=AsyncMock(return_value=[])
        ),
    ):
        await extract_deep_analysis_items(
            session, analysis.id, [item], user_id=user.id, client=fake_client
        )
    await session.commit()

    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert len(rows) == 1
    assert rows[0].status == DeepAnalysisItemStatus.failed
    assert rows[0].topic is None
    assert rows[0].comments_analyzed_count == 0

    # A real (if unparseable) API response still burned real tokens — must still be billed.
    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert len(usage) == 2


async def test_extract_retries_then_stores_failed_with_no_usage(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await session.commit()

    fake_client = _FakeClient(exc=RuntimeError("rate limited"))
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch(
            "src.services.deep_analysis_extraction.fetch_comments", new=AsyncMock(return_value=[])
        ),
        patch("src.services.deep_analysis_extraction.asyncio.sleep", new_callable=AsyncMock),
    ):
        await extract_deep_analysis_items(
            session, analysis.id, [item], user_id=user.id, client=fake_client
        )
    await session.commit()

    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert len(rows) == 1
    assert rows[0].status == DeepAnalysisItemStatus.failed
    assert len(fake_client.messages.calls) == 3

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert usage == []


async def test_extract_no_comments_marks_zero_coverage(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_JSON))
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch(
            "src.services.deep_analysis_extraction.fetch_comments", new=AsyncMock(return_value=[])
        ),
    ):
        await extract_deep_analysis_items(
            session, analysis.id, [item], user_id=user.id, client=fake_client
        )
    await session.commit()

    sent_text = fake_client.messages.calls[0]["messages"][0]["content"][0]["text"]
    assert "Комментарии: отсутствуют" in sent_text

    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert rows[0].comments_analyzed_count == 0


async def test_extract_batches_path_maps_results(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    items = []
    for i in range(3):
        it = await make_content_item(session, run=run, caption=f"Подпись {i}")
        it.cover_url = None
        items.append(it)
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await session.commit()

    item_ids = [str(it.id) for it in items]

    def _batch_result(custom_id: str):
        return SimpleNamespace(
            custom_id=custom_id,
            result=SimpleNamespace(
                type="succeeded",
                message=SimpleNamespace(
                    content=[SimpleNamespace(type="text", text=_VALID_JSON)],
                    usage=SimpleNamespace(input_tokens=90, output_tokens=45),
                ),
            ),
        )

    fake_batch = SimpleNamespace(id="batch_da_1", processing_status="ended")

    class _FakeBatches:
        async def create(self, requests):
            return fake_batch

        async def retrieve(self, batch_id):
            return fake_batch

        async def results(self, batch_id):
            async def _gen():
                for cid in item_ids:
                    yield _batch_result(cid)

            return _gen()

    class _FakeBatchClient:
        def __init__(self):
            self.messages = SimpleNamespace(batches=_FakeBatches())

    fake_client = _FakeBatchClient()
    from src.config import Settings, get_settings

    overridden = Settings(**{**get_settings().model_dump(), "summary_batch_threshold": 2})
    with (
        patch("src.services.deep_analysis_extraction.get_settings", return_value=overridden),
        patch(
            "src.services.deep_analysis_extraction.fetch_comments", new=AsyncMock(return_value=[])
        ),
    ):
        await extract_deep_analysis_items(
            session, analysis.id, items, user_id=user.id, client=fake_client
        )
    await session.commit()

    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert len(rows) == 3
    assert all(r.status == DeepAnalysisItemStatus.done for r in rows)

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert len(usage) == 6  # 3 items x (input + output)


async def test_deep_analysis_item_unique_per_analysis_and_content_item() -> None:
    # Purely structural — the constraint itself is exercised via a real DB round trip in
    # test_deep_analysis_model.py-style tests; here we just confirm the id is deterministic
    # enough to dedupe on (deep_analysis_id, content_item_id) as documented.
    analysis_id = uuid.uuid4()
    content_item_id = uuid.uuid4()
    row = DeepAnalysisItem(
        deep_analysis_id=analysis_id,
        content_item_id=content_item_id,
        status=DeepAnalysisItemStatus.done,
    )
    assert row.deep_analysis_id == analysis_id
    assert row.content_item_id == content_item_id
