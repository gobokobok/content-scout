import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    Account,
    ContentItem,
    ContentType,
    DeepAnalysis,
    DeepAnalysisItem,
    DeepAnalysisItemStatus,
    DeepAnalysisStatus,
    UsageEvent,
)
from src.services.deep_analysis import fail_deep_analysis
from src.services.metrics import bucket_virality, virality_baseline_subquery, virality_ratio

logger = logging.getLogger(__name__)

_TYPE_LABELS_RU = {
    ContentType.reel: "Reels",
    ContentType.post: "Пост",
    ContentType.carousel: "Карусель",
    ContentType.video: "Видео",
    ContentType.short: "Шортс",
}

_UNPARSEABLE_MESSAGE_RU = "Не удалось сформировать отчёт. Попробуйте запустить анализ ещё раз."
_NO_DATA_MESSAGE_RU = "В запуске нет публикаций для анализа."

# tool_choice forces *a* tool call but not schema compliance — Sonnet occasionally omits a
# required top-level key (seen live: a response with only "recommendations", no "stats") despite
# a normal stop_reason=tool_use. One retry clears this without a second flaky response usually.
_MAX_SYNTHESIS_ATTEMPTS = 2

# Mirrors docs/PROMPTS.md "Deep analysis synthesis (E17-S4)" — change there first.
SYSTEM_PROMPT = """\
Ты — маркетинговый аналитик социальных сетей. По списку публикаций конкурентов (метрики, \
теги контента, сигналы из комментариев) составь два раздела отчёта: Статистика и Рекомендации.

Правила:
- Всё на русском языке.
- Статистика описывает то, что уже происходит: частота тем и их виральность, разбивка по \
форматам/типам зацепок/наличию призыва к действию, частота публикаций, тональность \
комментариев с показательными цитатами.
- Рекомендации — практические выводы: конкретные идеи для контента, что стоит делать \
больше/меньше, шаблоны зацепок, пакет частых вопросов из комментариев без ответа, \
предложение по расписанию публикаций, подборка «украсть эту идею» со ссылкой на \
content_item_id лучших постов.
- Используй только переданные данные, не выдумывай публикации или цифры.
- Ответь вызовом инструмента submit_deep_analysis_report — не отвечай обычным текстом."""

REPORT_TOOL = {
    "name": "submit_deep_analysis_report",
    "description": (
        "Отправить структурированный отчёт глубокого анализа (Статистика + Рекомендации)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "stats": {
                "type": "object",
                "properties": {
                    "topics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "topic": {"type": "string"},
                                "frequency": {"type": "integer"},
                                "avg_virality": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low", "unknown"],
                                },
                            },
                            "required": ["topic", "frequency", "avg_virality"],
                        },
                    },
                    "formats": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "format": {"type": "string"},
                                "count": {"type": "integer"},
                            },
                            "required": ["format", "count"],
                        },
                    },
                    "hooks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "hook_type": {"type": "string"},
                                "count": {"type": "integer"},
                            },
                            "required": ["hook_type", "count"],
                        },
                    },
                    "cta_share": {"type": "number"},
                    "cadence_summary": {"type": "string"},
                    "sentiment_summary": {"type": "string"},
                    "representative_quotes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["topics", "formats", "hooks", "cadence_summary", "sentiment_summary"],
            },
            "recommendations": {
                "type": "object",
                "properties": {
                    "content_ideas": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "topic": {"type": "string"},
                                "format": {"type": "string"},
                                "hook": {"type": "string"},
                                "why": {"type": "string"},
                            },
                            "required": ["topic", "format", "hook", "why"],
                        },
                    },
                    "do_more": {"type": "array", "items": {"type": "string"}},
                    "do_less": {"type": "array", "items": {"type": "string"}},
                    "hook_templates": {"type": "array", "items": {"type": "string"}},
                    "faq_pack": {"type": "array", "items": {"type": "string"}},
                    "posting_schedule": {"type": "string"},
                    "steal_this": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content_item_id": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                            "required": ["content_item_id", "reason"],
                        },
                    },
                },
                "required": [
                    "content_ideas",
                    "do_more",
                    "do_less",
                    "hook_templates",
                    "faq_pack",
                    "posting_schedule",
                ],
            },
        },
        "required": ["stats", "recommendations"],
    },
}


def _comment_coverage_ratio(rows: Sequence[Any]) -> float:
    """E17-S9: share of synthesized items that had any fetched comments at all — the signal
    a thin/degraded comment-data run is detected from."""
    if not rows:
        return 0.0
    with_comments = sum(1 for extract, *_ in rows if extract.comments_analyzed_count > 0)
    return with_comments / len(rows)


def _strip_comment_derived_sections(stats: dict[str, Any], recommendations: dict[str, Any]) -> None:
    """Below the coverage threshold, comment-derived sections are stripped server-side rather
    than trusted to come back empty from the model — this guarantees no fabricated sentiment/
    quotes/FAQ regardless of what Sonnet actually returned. Content-layer sections (topics,
    formats, hooks, cadence, content ideas, do-more/less, hook templates, posting schedule,
    steal-this) are untouched — they don't depend on comments."""
    stats["sentiment_summary"] = ""
    stats["representative_quotes"] = []
    stats["comment_coverage_degraded"] = True
    recommendations["faq_pack"] = []
    recommendations["comment_coverage_degraded"] = True


def _build_prompt_lines(rows: Sequence[Any]) -> list[str]:
    lines: list[str] = []
    for extract, item, handle, median_engagement, median_views, item_count in rows:
        type_label = _TYPE_LABELS_RU.get(item.type, "Пост")
        virality = bucket_virality(
            virality_ratio(
                likes=item.likes,
                comments=item.comments,
                views=item.views,
                median_engagement=median_engagement,
                median_views=median_views,
            ),
            item_count,
            get_settings(),
        )
        line = (
            f"- id={item.id} @{handle} ({type_label}, {item.published_at.date()}): "
            f"тема={extract.topic or '?'}, формат={extract.content_format or '?'}, "
            f"зацепка={extract.hook_type or '?'}, cta={extract.has_cta}, "
            f"виральность={virality or 'н/д'}, лайки={item.likes or 0}, "
            f"комментарии={item.comments or 0}"
        )
        if extract.sentiment:
            line += f", тональность={extract.sentiment}"
        if extract.complaints:
            line += f"; жалобы: {'; '.join(extract.complaints)}"
        if extract.praises:
            line += f"; похвалы: {'; '.join(extract.praises)}"
        if extract.questions:
            line += f"; вопросы без ответа: {'; '.join(extract.questions)}"
        if extract.notable_phrases:
            line += f"; заметные цитаты: {'; '.join(extract.notable_phrases)}"
        lines.append(line)
    return lines


async def synthesize_report(
    session: AsyncSession,
    analysis: DeepAnalysis,
    *,
    user_id: uuid.UUID,
    client: AsyncAnthropic | None = None,
) -> None:
    """One Sonnet call (D33) synthesizing the full two-tab report from the run's metrics plus
    every item's E17-S3 extract. Never raises — an API error or a response with no tool_use
    block sets status=failed with a Russian message, mirroring generate_run_summary's
    never-raises pattern so the deep analysis is never left stuck mid-pipeline.
    """
    settings = get_settings()
    try:
        virality_subq = virality_baseline_subquery(ContentItem.run_id == analysis.run_id)
        rows = (
            await session.execute(
                select(
                    DeepAnalysisItem,
                    ContentItem,
                    Account.handle,
                    virality_subq.c.median_engagement,
                    virality_subq.c.median_views,
                    virality_subq.c.item_count,
                )
                .join(ContentItem, DeepAnalysisItem.content_item_id == ContentItem.id)
                .join(Account, ContentItem.account_id == Account.id)
                .join(
                    virality_subq,
                    (virality_subq.c.account_id == ContentItem.account_id)
                    & (virality_subq.c.run_id == ContentItem.run_id),
                )
                .where(
                    DeepAnalysisItem.deep_analysis_id == analysis.id,
                    DeepAnalysisItem.status == DeepAnalysisItemStatus.done,
                )
                .order_by(ContentItem.published_at.desc())
            )
        ).all()

        if not rows:
            await fail_deep_analysis(session, analysis, _NO_DATA_MESSAGE_RU, user_id=user_id)
            return

        prompt_lines = _build_prompt_lines(rows)

        _client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)

        stats: dict[str, Any] | None = None
        recommendations: dict[str, Any] | None = None
        for attempt in range(1, _MAX_SYNTHESIS_ATTEMPTS + 1):
            response = await _client.messages.create(  # type: ignore[call-overload]
                model=settings.deep_analysis_synthesis_model,
                max_tokens=settings.deep_analysis_synthesis_max_tokens,
                system=SYSTEM_PROMPT,
                tools=[REPORT_TOOL],
                tool_choice={"type": "tool", "name": "submit_deep_analysis_report"},
                messages=[
                    {
                        "role": "user",
                        "content": "Публикации для анализа:\n" + "\n".join(prompt_lines),
                    }
                ],
            )
            # Every attempt is a billed Anthropic call, regardless of whether its output parses.
            session.add(
                UsageEvent(
                    user_id=user_id,
                    run_id=analysis.run_id,
                    kind=KIND_CLAUDE_INPUT_TOKENS,
                    quantity=response.usage.input_tokens,
                    unit_cost_usd=Decimal(str(settings.claude_input_token_cost_usd)),
                )
            )
            session.add(
                UsageEvent(
                    user_id=user_id,
                    run_id=analysis.run_id,
                    kind=KIND_CLAUDE_OUTPUT_TOKENS,
                    quantity=response.usage.output_tokens,
                    unit_cost_usd=Decimal(str(settings.claude_output_token_cost_usd)),
                )
            )

            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if tool_use is None or not isinstance(tool_use.input, dict):
                # No exception was raised, so the except-Exception branch below (which does log)
                # never fires for this path — log explicitly. stop_reason="max_tokens" is the
                # fingerprint of a truncated tool call (deep_analysis_synthesis_max_tokens);
                # stop_reason="tool_use" means the model just omitted a required field.
                logger.warning(
                    "deep analysis synthesis: no usable tool_use block for analysis_id=%s "
                    "attempt=%s/%s (stop_reason=%s, content_types=%s)",
                    analysis.id,
                    attempt,
                    _MAX_SYNTHESIS_ATTEMPTS,
                    response.stop_reason,
                    [b.type for b in response.content],
                )
                continue

            data = tool_use.input
            candidate_stats = data.get("stats")
            candidate_recommendations = data.get("recommendations")
            if not isinstance(candidate_stats, dict) or not isinstance(
                candidate_recommendations, dict
            ):
                logger.warning(
                    "deep analysis synthesis: tool_use missing stats/recommendations for "
                    "analysis_id=%s attempt=%s/%s (stop_reason=%s, keys=%s)",
                    analysis.id,
                    attempt,
                    _MAX_SYNTHESIS_ATTEMPTS,
                    response.stop_reason,
                    list(data.keys()),
                )
                continue

            stats, recommendations = candidate_stats, candidate_recommendations
            break

        if stats is None or recommendations is None:
            await fail_deep_analysis(session, analysis, _UNPARSEABLE_MESSAGE_RU, user_id=user_id)
            return

        if _comment_coverage_ratio(rows) < settings.deep_analysis_comment_coverage_threshold:
            _strip_comment_derived_sections(stats, recommendations)

        analysis.report_stats = stats
        analysis.report_recommendations = recommendations
        analysis.status = DeepAnalysisStatus.done
        analysis.completed_at = datetime.now(UTC)
    except Exception:  # noqa: BLE001 — never fails the caller (mirrors generate_run_summary)
        logger.exception("deep analysis synthesis failed for analysis_id=%s", analysis.id)
        await fail_deep_analysis(session, analysis, _UNPARSEABLE_MESSAGE_RU, user_id=user_id)
