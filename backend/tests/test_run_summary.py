from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    RunSummaryStatus,
    UsageEvent,
)
from src.services.run_summary import generate_run_summary, parse_summary_response
from tests.conftest import make_account, make_content_item, make_run, make_user


def _fake_response(text: str, input_tokens: int = 300, output_tokens: int = 80):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


class _FakeClient:
    def __init__(self, response=None, exc: Exception | None = None) -> None:
        self.messages = SimpleNamespace(create=AsyncMock())
        if exc is not None:
            self.messages.create.side_effect = exc
        else:
            self.messages.create.return_value = response


_VALID_RESPONSE = """\
РЕЗЮМЕ: Конкуренты в основном публикуют короткие видео о путешествиях и еде. \
Больше вовлечённости получают ролики с личными историями.
ТЕМЫ:
1. Путешествия
2. Еда и рестораны
3. Личные истории
4. Бытовые советы
5. Обзоры продуктов"""


# ---------------------------------------------------------------------------
# parse_summary_response — pure function, no DB/API needed
# ---------------------------------------------------------------------------


def test_parse_summary_response_standard_format() -> None:
    summary, topics = parse_summary_response(_VALID_RESPONSE)

    assert summary.startswith("Конкуренты в основном публикуют")
    assert topics == [
        "Путешествия",
        "Еда и рестораны",
        "Личные истории",
        "Бытовые советы",
        "Обзоры продуктов",
    ]


def test_parse_summary_response_unparseable_fallback() -> None:
    raw = "Просто текст без ожидаемых маркеров формата."

    summary, topics = parse_summary_response(raw)

    assert summary == raw
    assert topics == []


def test_parse_summary_response_more_than_five_topics_truncated() -> None:
    text = "РЕЗЮМЕ: Что-то.\nТЕМЫ:\n1. A\n2. B\n3. C\n4. D\n5. E\n6. F"

    _, topics = parse_summary_response(text)

    assert topics == ["A", "B", "C", "D", "E"]


# ---------------------------------------------------------------------------
# generate_run_summary — integration against the DB
# ---------------------------------------------------------------------------


async def test_generate_run_summary_writes_fields_and_usage(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    account = await make_account(session, handle="travel_blog")
    await make_content_item(session, run=run, account=account, summary="Ролик про поездку в горы")
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_RESPONSE))
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)

    assert run.summary_status == RunSummaryStatus.done
    assert run.summary_text.startswith("Конкуренты в основном публикуют")
    assert run.summary_topics == [
        "Путешествия",
        "Еда и рестораны",
        "Личные истории",
        "Бытовые советы",
        "Обзоры продуктов",
    ]
    assert run.summary_generated_at is not None
    fake_client.messages.create.assert_awaited_once()

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    kinds = {u.kind: u.quantity for u in usage}
    assert kinds[KIND_CLAUDE_INPUT_TOKENS] == 300
    assert kinds[KIND_CLAUDE_OUTPUT_TOKENS] == 80


async def test_generate_run_summary_falls_back_to_caption(session: AsyncSession) -> None:
    """Items without a summary (e.g. summarization itself failed) still contribute
    via their raw caption — the run summary shouldn't skip them."""
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    account = await make_account(session, handle="foodie")
    await make_content_item(
        session, run=run, account=account, summary=None, caption="Новый рецепт пасты"
    )
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_RESPONSE))
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)

    assert run.summary_status == RunSummaryStatus.done
    call_kwargs = fake_client.messages.create.await_args.kwargs
    user_message = call_kwargs["messages"][0]["content"]
    assert "Новый рецепт пасты" in user_message


async def test_generate_run_summary_no_items_marks_failed(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    await session.commit()

    fake_client = _FakeClient()
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)

    assert run.summary_status == RunSummaryStatus.failed
    assert run.summary_generated_at is not None
    fake_client.messages.create.assert_not_awaited()


async def test_generate_run_summary_api_error_is_non_fatal(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    account = await make_account(session, handle="acc")
    await make_content_item(session, run=run, account=account, summary="Что-то интересное")
    await session.commit()

    fake_client = _FakeClient(exc=RuntimeError("api down"))

    # Must not raise — non-fatal per AC, mirrors notify_run_complete
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)

    assert run.summary_status == RunSummaryStatus.failed
    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert usage == []


async def test_generate_run_summary_unparseable_response_still_stores_text(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    account = await make_account(session, handle="acc")
    await make_content_item(session, run=run, account=account, summary="Что-то")
    await session.commit()

    raw = "Ответ без маркеров формата, но не пустой."
    fake_client = _FakeClient(_fake_response(raw))
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)

    assert run.summary_status == RunSummaryStatus.done
    assert run.summary_text == raw
    assert run.summary_topics == []
