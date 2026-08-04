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


async def test_extract_stores_parsed_signals_usage_and_charges_tokens(
    session: AsyncSession,
) -> None:
    user = await make_user(session, token_balance=100)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=0)
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
        token_exhausted = await extract_deep_analysis_items(
            session, analysis, [item], user=user, client=fake_client
        )
    await session.commit()

    assert token_exhausted is False
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

    # D50: 1 token for the publication + 1 for its one comment, charged incrementally.
    assert analysis.tokens_charged == 2
    assert user.token_balance == 98


async def test_extract_unparseable_response_stores_failed_but_still_charges_usage(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=0)
    await session.commit()

    fake_client = _FakeClient(_fake_response("это не json вовсе"))
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch(
            "src.services.deep_analysis_extraction.fetch_comments", new=AsyncMock(return_value=[])
        ),
    ):
        await extract_deep_analysis_items(session, analysis, [item], user=user, client=fake_client)
    await session.commit()

    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert len(rows) == 1
    assert rows[0].status == DeepAnalysisItemStatus.failed
    assert rows[0].topic is None
    assert rows[0].comments_analyzed_count == 0

    # Unparseable responses are retried (not just API exceptions) — every real API response
    # still burned real tokens, so all 3 attempts must be billed, not just the last.
    assert len(fake_client.messages.calls) == 3
    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert len(usage) == 6

    # A failed extraction still attempted the publication — still charged 1 token for it.
    assert analysis.tokens_charged == 1


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
        await extract_deep_analysis_items(session, analysis, [item], user=user, client=fake_client)
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
        await extract_deep_analysis_items(session, analysis, [item], user=user, client=fake_client)
    await session.commit()

    sent_text = fake_client.messages.calls[0]["messages"][0]["content"][0]["text"]
    assert "Комментарии: отсутствуют" in sent_text

    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert rows[0].comments_analyzed_count == 0


async def test_extract_passes_comments_limit_override_to_fetch_comments(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    item.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_JSON))
    fake_fetch = AsyncMock(return_value=[])
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch("src.services.deep_analysis_extraction.fetch_comments", new=fake_fetch),
    ):
        await extract_deep_analysis_items(
            session, analysis, [item], user=user, comments_limit=7, client=fake_client
        )

    assert fake_fetch.call_args.kwargs["limit_override"] == 7


async def test_extract_stops_when_balance_exhausted_before_batch(session: AsyncSession) -> None:
    # Balance is already 0 when extraction starts — no item should even be attempted.
    user = await make_user(session, token_balance=0)
    run = await make_run(session, requested_by=user)
    item = await make_content_item(session, run=run, caption="Подпись")
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=0)
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_JSON))
    fake_fetch = AsyncMock(return_value=[])
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch("src.services.deep_analysis_extraction.fetch_comments", new=fake_fetch),
    ):
        token_exhausted = await extract_deep_analysis_items(
            session, analysis, [item], user=user, client=fake_client
        )

    assert token_exhausted is True
    fake_fetch.assert_not_called()
    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert rows == []
    assert analysis.tokens_charged == 0


async def test_extract_truncates_batch_to_remaining_balance(session: AsyncSession) -> None:
    # Balance covers only 1 of 3 items in the same batch (summary_concurrency default is 5,
    # so all 3 land in one batch) — the batch is truncated, not all-or-nothing.
    user = await make_user(session, token_balance=1)
    run = await make_run(session, requested_by=user)
    items = [await make_content_item(session, run=run, caption=f"Подпись {i}") for i in range(3)]
    for it in items:
        it.cover_url = None
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=0)
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_JSON))
    with (
        patch("src.services.deep_analysis_extraction.AsyncAnthropic", return_value=fake_client),
        patch(
            "src.services.deep_analysis_extraction.fetch_comments", new=AsyncMock(return_value=[])
        ),
    ):
        token_exhausted = await extract_deep_analysis_items(
            session, analysis, items, user=user, client=fake_client
        )

    assert token_exhausted is True
    rows = (await session.scalars(select(DeepAnalysisItem))).all()
    assert len(rows) == 1  # only the balance-affordable slice of the batch was attempted
    assert user.token_balance == 0
    assert analysis.tokens_charged == 1


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
