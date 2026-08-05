from collections import Counter
from types import SimpleNamespace
from unittest.mock import AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    ContentType,
    RunSummaryStatus,
    UsageEvent,
)
from src.services.run_summary import (
    _format_counts_line,
    generate_run_summary,
    parse_summary_response,
)
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
# E22-S1: ТЕГИ block -> real per-topic counts, and the format-counts fact line
# ---------------------------------------------------------------------------


def test_parse_summary_response_tags_block_adds_real_topic_counts() -> None:
    text = (
        "РЕЗЮМЕ: Конкуренты публикуют в основном путешествия.\n"
        "ТЕМЫ:\n1. Путешествия\n2. Еда\n"
        "ТЕГИ:\n1: 1\n2: 1\n3: 2\n4: 1"
    )

    _, topics = parse_summary_response(text)

    assert topics == ["Путешествия (3)", "Еда (1)"]


def test_parse_summary_response_no_tags_block_leaves_topics_plain() -> None:
    """Backward compatible: a response without a ТЕГИ section (older prompt shape, or the
    model just not complying) still yields plain topic strings, no "(0)" noise."""
    text = "РЕЗЮМЕ: Что-то.\nТЕМЫ:\n1. Путешествия\n2. Еда"

    _, topics = parse_summary_response(text)

    assert topics == ["Путешествия", "Еда"]


def test_parse_summary_response_tags_block_ignores_malformed_and_out_of_range_lines() -> None:
    text = "РЕЗЮМЕ: Что-то.\nТЕМЫ:\n1. Путешествия\n2. Еда\nТЕГИ:\n1: 1\nне число\n2: 9\n3: 1"

    _, topics = parse_summary_response(text)

    assert topics == ["Путешествия (2)", "Еда"]


def test_parse_summary_response_topics_with_no_tags_stay_plain_even_when_others_have_counts() -> (
    None
):
    text = "РЕЗЮМЕ: Что-то.\nТЕМЫ:\n1. Путешествия\n2. Еда\nТЕГИ:\n1: 1\n2: 1"

    _, topics = parse_summary_response(text)

    assert topics == ["Путешествия (2)", "Еда"]


def test_format_counts_line_lists_only_present_types() -> None:
    line = _format_counts_line(Counter({ContentType.reel: 25, ContentType.carousel: 32}))

    assert line == "Reels: 25, Карусель: 32"


def test_format_counts_line_empty_returns_placeholder() -> None:
    assert _format_counts_line(Counter()) == "—"


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


async def test_generate_run_summary_prompt_includes_numbered_lines_and_format_counts(
    session: AsyncSession,
) -> None:
    """E22-S1: publications are numbered (so the model's ТЕГИ block can reference them) and a
    deterministic per-format fact line is prepended — real structured counts, not a model guess."""
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    account = await make_account(session, handle="travel_blog")
    await make_content_item(
        session, run=run, account=account, type=ContentType.reel, summary="Ролик про пляж"
    )
    await make_content_item(
        session, run=run, account=account, type=ContentType.carousel, summary="Подборка фото"
    )
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_RESPONSE))
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)

    user_message = fake_client.messages.create.await_args.kwargs["messages"][0]["content"]
    assert "Форматы (точное количество, используй как есть):" in user_message
    assert "Reels: 1" in user_message
    assert "Карусель: 1" in user_message
    assert "1. @travel_blog (Reels): Ролик про пляж" in user_message or (
        "1. @travel_blog (Карусель): Подборка фото" in user_message
    )
    assert "2. @travel_blog" in user_message


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
    user = await make_user(session, token_balance=100)
    run = await make_run(session, requested_by=user)
    await session.commit()

    fake_client = _FakeClient()
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)

    assert run.summary_status == RunSummaryStatus.failed
    assert run.summary_generated_at is not None
    fake_client.messages.create.assert_not_awaited()
    # D52: no real Anthropic cost incurred (the call never happened), so no base charge either.
    assert run.tokens_charged == 0
    assert user.token_balance == 100


async def test_generate_run_summary_api_error_is_non_fatal(session: AsyncSession) -> None:
    user = await make_user(session, token_balance=100)
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
    # D52: the call raised before any response came back — no real Anthropic cost was
    # incurred, so the base charge must not apply either.
    assert run.tokens_charged == 0
    assert user.token_balance == 100


# ---------------------------------------------------------------------------
# D52: base charge for this one run-level call
# ---------------------------------------------------------------------------


async def test_generate_run_summary_charges_base_fee_on_success(session: AsyncSession) -> None:
    user = await make_user(session, token_balance=1000)
    run = await make_run(session, requested_by=user)
    account = await make_account(session, handle="travel_blog")
    await make_content_item(session, run=run, account=account, summary="Ролик про поездку")
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_RESPONSE))
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)
    await session.commit()

    assert run.summary_status == RunSummaryStatus.done
    assert run.tokens_charged == 5
    await session.refresh(user)
    assert user.token_balance == 995


async def test_generate_run_summary_base_charge_floors_at_remaining_balance(
    session: AsyncSession,
) -> None:
    user = await make_user(session, token_balance=2)
    run = await make_run(session, requested_by=user)
    account = await make_account(session, handle="acc")
    await make_content_item(session, run=run, account=account, summary="Что-то")
    await session.commit()

    fake_client = _FakeClient(_fake_response(_VALID_RESPONSE))
    await generate_run_summary(session, run, user_id=user.id, client=fake_client)
    await session.commit()

    assert run.tokens_charged == 2
    await session.refresh(user)
    assert user.token_balance == 0


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
