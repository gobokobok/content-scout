import copy
import logging
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    DeepAnalysisItemStatus,
    DeepAnalysisStatus,
    UsageEvent,
)
from src.services.deep_analysis_synthesis import synthesize_report
from tests.conftest import make_content_item, make_deep_analysis, make_run, make_user

_VALID_REPORT = {
    "stats": {
        "topics": [{"topic": "Тренировки", "frequency": 5, "avg_virality": "high"}],
        "formats": [{"format": "обучающий", "count": 5}],
        "hooks": [{"hook_type": "вопрос", "count": 3}],
        "cta_share": 0.4,
        "cadence_summary": "3 раза в неделю",
        "sentiment_summary": "В основном позитивные отзывы",
        "representative_quotes": ["Отличный контент!"],
    },
    "recommendations": {
        "content_ideas": [
            {"topic": "Растяжка", "format": "видео", "hook": "вопрос", "why": "популярно"}
        ],
        "do_more": ["больше туториалов"],
        "do_less": ["меньше рекламы"],
        "hook_templates": ["А ты знал, что...?"],
        "faq_pack": ["Сколько это стоит?"],
        "posting_schedule": "Пн/Ср/Пт в 18:00",
        "steal_this": [{"content_item_id": "abc", "reason": "высокая виральность"}],
    },
}


def _tool_use_response(
    data: dict, input_tokens: int = 500, output_tokens: int = 300, stop_reason: str = "tool_use"
):
    # deepcopy: synthesize_report mutates stats/recommendations in place when degrading
    # coverage (E17-S9) — sharing the module-level _VALID_REPORT dict across tests without
    # copying would let one test's mutation leak into every test that runs after it.
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use", name="submit_deep_analysis_report", input=copy.deepcopy(data)
            )
        ],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
        stop_reason=stop_reason,
    )


class _FakeMessages:
    def __init__(
        self,
        response=None,
        exc: Exception | None = None,
        responses: list | None = None,
    ) -> None:
        self._response = response
        self._exc = exc
        self._responses = responses
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc is not None:
            raise self._exc
        if self._responses is not None:
            idx = min(len(self.calls) - 1, len(self._responses) - 1)
            return self._responses[idx]
        return self._response


class _FakeClient:
    def __init__(
        self,
        response=None,
        exc: Exception | None = None,
        responses: list | None = None,
    ) -> None:
        self.messages = _FakeMessages(response, exc, responses)


async def _make_done_extraction_item(session, run, **kw):
    from src.models import DeepAnalysisItem

    item = await make_content_item(session, run=run, likes=100, comments=10)
    extraction = DeepAnalysisItem(
        deep_analysis_id=kw["deep_analysis_id"],
        content_item_id=item.id,
        status=DeepAnalysisItemStatus.done,
        topic=kw.get("topic", "Тренировки"),
        content_format=kw.get("content_format", "обучающий"),
        hook_type=kw.get("hook_type", "вопрос"),
        has_cta=kw.get("has_cta", True),
        sentiment=kw.get("sentiment", "positive"),
        complaints=kw.get("complaints"),
        praises=kw.get("praises"),
        questions=kw.get("questions"),
        notable_phrases=kw.get("notable_phrases"),
        comments_analyzed_count=kw.get("comments_analyzed_count", 5),
    )
    session.add(extraction)
    await session.flush()
    return item, extraction


async def test_synthesize_report_stores_stats_and_recommendations_and_usage(
    session: AsyncSession,
) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await _make_done_extraction_item(session, run, deep_analysis_id=analysis.id)
    await session.commit()

    fake_client = _FakeClient(_tool_use_response(_VALID_REPORT))
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.done
    assert analysis.report_stats == _VALID_REPORT["stats"]
    assert analysis.report_recommendations == _VALID_REPORT["recommendations"]
    assert analysis.completed_at is not None

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    kinds = {u.kind: u.quantity for u in usage}
    assert kinds[KIND_CLAUDE_INPUT_TOKENS] == 500
    assert kinds[KIND_CLAUDE_OUTPUT_TOKENS] == 300

    # Prompt sent to Claude reflects the extraction's content + comment signals
    sent = fake_client.messages.calls[0]["messages"][0]["content"]
    assert "тема=Тренировки" in sent
    assert "виральность=" in sent


async def test_synthesize_report_no_done_items_fails_without_api_call(
    session: AsyncSession,
) -> None:
    user = await make_user(session, token_balance=100)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=10)
    await session.commit()

    fake_client = _FakeClient(_tool_use_response(_VALID_REPORT))
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.failed
    assert analysis.error_message
    assert fake_client.messages.calls == []
    # D50: charging happens incrementally during extraction, not here — a synthesis-stage
    # failure has nothing to refund, tokens_charged just stays whatever extraction left it at.
    assert analysis.tokens_charged == 10
    assert user.token_balance == 100


async def test_synthesize_report_api_error_marks_failed(session: AsyncSession) -> None:
    user = await make_user(session, token_balance=100)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=10)
    await _make_done_extraction_item(session, run, deep_analysis_id=analysis.id)
    await session.commit()

    fake_client = _FakeClient(exc=RuntimeError("anthropic down"))
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.failed
    assert analysis.error_message
    assert analysis.report_stats is None
    # D50: no refund on a synthesis-stage failure — nothing artificial to give back.
    assert analysis.tokens_charged == 10
    assert user.token_balance == 100

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert usage == []


async def test_synthesize_report_missing_tool_use_marks_failed(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await _make_done_extraction_item(session, run, deep_analysis_id=analysis.id)
    await session.commit()

    text_only_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="не могу выполнить")],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
        stop_reason="end_turn",
    )
    fake_client = _FakeClient(text_only_response)
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.failed
    # Retried once before giving up — every failing attempt gets the same malformed response.
    assert len(fake_client.messages.calls) == 2


async def test_synthesize_report_malformed_tool_input_marks_failed(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await _make_done_extraction_item(session, run, deep_analysis_id=analysis.id)
    await session.commit()

    fake_client = _FakeClient(_tool_use_response({"stats": {}}))  # missing "recommendations"
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.failed
    assert len(fake_client.messages.calls) == 2


async def test_synthesize_report_retries_once_after_malformed_tool_input(
    session: AsyncSession,
) -> None:
    """Reproduces the 2026-08-04 DEV incident: Sonnet returned stop_reason=tool_use with only a
    "recommendations" key, no "stats", despite tool_choice forcing the call. One retry recovers."""
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await _make_done_extraction_item(session, run, deep_analysis_id=analysis.id)
    await session.commit()

    responses = [
        _tool_use_response({"recommendations": _VALID_REPORT["recommendations"]}),
        _tool_use_response(_VALID_REPORT),
    ]
    fake_client = _FakeClient(responses=responses)
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.done
    assert analysis.report_stats == _VALID_REPORT["stats"]
    assert analysis.report_recommendations == _VALID_REPORT["recommendations"]
    assert len(fake_client.messages.calls) == 2

    # Both attempts were billed Anthropic calls, not just the successful one.
    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.run_id == run.id))).all()
    assert len([u for u in usage if u.kind == KIND_CLAUDE_INPUT_TOKENS]) == 2
    assert len([u for u in usage if u.kind == KIND_CLAUDE_OUTPUT_TOKENS]) == 2


async def test_synthesize_report_thin_coverage_strips_sections(session: AsyncSession) -> None:
    user = await make_user(session, token_balance=1000)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=100)
    # Two items, neither with any fetched comments — coverage ratio 0.0, below the 0.5 default.
    await _make_done_extraction_item(
        session, run, deep_analysis_id=analysis.id, comments_analyzed_count=0
    )
    await _make_done_extraction_item(
        session, run, deep_analysis_id=analysis.id, comments_analyzed_count=0
    )
    await session.commit()

    fake_client = _FakeClient(_tool_use_response(_VALID_REPORT))
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.done
    assert analysis.report_stats["sentiment_summary"] == ""
    assert analysis.report_stats["representative_quotes"] == []
    assert analysis.report_stats["comment_coverage_degraded"] is True
    assert analysis.report_recommendations["faq_pack"] == []
    assert analysis.report_recommendations["comment_coverage_degraded"] is True
    # Content-layer sections are untouched.
    assert analysis.report_stats["topics"] == _VALID_REPORT["stats"]["topics"]
    assert (
        analysis.report_recommendations["content_ideas"]
        == _VALID_REPORT["recommendations"]["content_ideas"]
    )

    # D50: synthesis never touches tokens_charged/token_balance at all — charging happens
    # entirely during extraction, incrementally per item, not reconciled here afterward.
    assert analysis.tokens_charged == 100
    await session.refresh(user)
    assert user.token_balance == 1000


async def test_synthesize_report_never_charges_or_refunds(session: AsyncSession) -> None:
    """D50 supersedes the old post-hoc reconciliation (D48): extraction already charges the
    real per-item/per-comment cost incrementally as it happens, so synthesis has nothing left
    to true up — tokens_charged/token_balance must be exactly whatever they were beforehand,
    regardless of how many items/comments the report actually covers."""
    user = await make_user(session, token_balance=1000)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user, tokens_charged=6)
    await _make_done_extraction_item(
        session, run, deep_analysis_id=analysis.id, comments_analyzed_count=5
    )
    await _make_done_extraction_item(
        session, run, deep_analysis_id=analysis.id, comments_analyzed_count=3
    )
    await session.commit()

    fake_client = _FakeClient(_tool_use_response(_VALID_REPORT))
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.tokens_charged == 6
    assert "comment_coverage_degraded" not in analysis.report_stats
    await session.refresh(user)
    assert user.token_balance == 1000


async def test_synthesize_report_uses_configured_sonnet_model(session: AsyncSession) -> None:
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await _make_done_extraction_item(session, run, deep_analysis_id=analysis.id)
    await session.commit()

    fake_client = _FakeClient(_tool_use_response(_VALID_REPORT))
    await synthesize_report(session, analysis, user_id=user.id, client=fake_client)

    assert fake_client.messages.calls[0]["model"] == "claude-sonnet-5"
    assert fake_client.messages.calls[0]["tool_choice"] == {
        "type": "tool",
        "name": "submit_deep_analysis_report",
    }
    assert fake_client.messages.calls[0]["max_tokens"] == 8192


async def test_synthesize_report_truncated_response_marks_failed_and_logs_stop_reason(
    session: AsyncSession, caplog
) -> None:
    """Reproduces the 2026-08-03 DEV incident: Sonnet hit its output-token ceiling mid tool
    call, so no tool_use block came back at all — no exception raised, so the except-Exception
    branch (which does log) never fires. The stop_reason must be logged from this path directly,
    otherwise there is zero trace of why the analysis failed anywhere but the DB row itself."""
    user = await make_user(session)
    run = await make_run(session, requested_by=user)
    analysis = await make_deep_analysis(session, run=run, requested_by=user)
    await _make_done_extraction_item(session, run, deep_analysis_id=analysis.id)
    await session.commit()

    truncated_response = SimpleNamespace(
        content=[],
        usage=SimpleNamespace(input_tokens=6000, output_tokens=8192),
        stop_reason="max_tokens",
    )
    fake_client = _FakeClient(truncated_response)
    with caplog.at_level(logging.WARNING):
        await synthesize_report(session, analysis, user_id=user.id, client=fake_client)
    await session.commit()

    assert analysis.status == DeepAnalysisStatus.failed
    assert "max_tokens" in caplog.text
    assert str(analysis.id) in caplog.text
    assert len(fake_client.messages.calls) == 2
