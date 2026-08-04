import re
import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    Account,
    AnalysisRun,
    ContentItem,
    ContentType,
    RunSummaryStatus,
    UsageEvent,
)

_TYPE_LABELS_RU = {
    ContentType.reel: "Reels",
    ContentType.post: "Пост",
    ContentType.carousel: "Карусель",
    ContentType.video: "Видео",
    ContentType.short: "Шортс",
}


def _format_counts_line(type_counts: "Counter[ContentType]") -> str:
    """E22-S1: deterministic per-ContentType counts (structured data, zero hallucination risk)
    handed to the model as a fact block, so format claims in the summary text cite real numbers
    instead of the model estimating from the sampled captions."""
    parts = [f"{_TYPE_LABELS_RU.get(t, 'Пост')}: {n}" for t, n in type_counts.items() if n > 0]
    return ", ".join(parts) if parts else "—"


_MAX_ITEMS = 150

# Mirrors docs/PROMPTS.md "Run summary (E15-S1)" — change there first, then here.
# E22-S1: the ТЕГИ block lets the model tag each numbered input publication with one of its
# five ТЕМЫ, so per-topic counts can be aggregated deterministically server-side (parse_summary_
# response below) instead of trusting a number the model writes freehand into the summary text.
# Format counts (Reels/Карусель/...) are real structured data already, computed before this
# prompt is even built (see _format_counts_line) and handed to the model as a fact to cite.
SYSTEM_PROMPT = """\
Ты — аналитик контента социальных сетей. По списку публикаций аккаунтов-конкурентов \
(номер, аккаунт, тип, краткое описание) составь общий обзор запуска анализа.

Тебе также дано точное количество публикаций по форматам — используй эти числа дословно, если \
упоминаешь формат в резюме, не оценивай на глаз.

Правила:
- Ответ строго в следующем формате, на русском языке:
РЕЗЮМЕ: <2–4 предложения о том, какой контент публикуют конкуренты в этой подборке и какие темы \
или форматы встречаются чаще всего; форматные утверждения подкрепляй точными числами из блока \
«Форматы», например «карусели (32), Reels (25)»>
ТЕМЫ:
1. <тема>
2. <тема>
3. <тема>
4. <тема>
5. <тема>
ТЕГИ:
<номер публикации>: <номер темы 1-5>
<номер публикации>: <номер темы 1-5>
... (по одной строке на каждую публикацию из списка, в том же порядке, без пропусков)
- Резюме описывает контент, а не оценивает его успех и не даёт рекомендаций.
- Темы — короткие (2–4 слова) названия тем/форматов, без нумерации внутри текста темы.
- В блоке ТЕГИ присвой каждой публикации ровно одну наиболее подходящую тему из списка ТЕМЫ.
- Не пересказывай хэштеги."""

_SUMMARY_RE = re.compile(r"РЕЗЮМЕ:\s*(.+?)(?=\nТЕМЫ:|\Z)", re.DOTALL)
# Stops before ТЕГИ: (if present) rather than running greedily to the end of the response —
# otherwise the tag lines below would get parsed as bogus extra "topics".
_TOPICS_RE = re.compile(r"ТЕМЫ:\s*(.+?)(?=\nТЕГИ:|\Z)", re.DOTALL)
_TOPIC_NUMBERING_RE = re.compile(r"^\d+[.)]\s*")
_TAGS_RE = re.compile(r"ТЕГИ:\s*(.+)", re.DOTALL)
_TAG_LINE_RE = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*$")


def _parse_topic_counts(text: str) -> Counter[int]:
    """Aggregates the ТЕГИ block into {topic_number (1-5): tagged-item count}. Malformed or
    out-of-range lines are silently skipped — this is a best-effort enrichment, never a reason
    to fail the whole response (same non-fatal spirit as the rest of this module)."""
    counts: Counter[int] = Counter()
    tags_match = _TAGS_RE.search(text)
    if not tags_match:
        return counts
    for line in tags_match.group(1).strip().splitlines():
        line_match = _TAG_LINE_RE.match(line)
        if not line_match:
            continue
        topic_number = int(line_match.group(2))
        if 1 <= topic_number <= 5:
            counts[topic_number] += 1
    return counts


def parse_summary_response(text: str) -> tuple[str, list[str]]:
    """Deterministically parses the РЕЗЮМЕ:/ТЕМЫ:/ТЕГИ: text protocol.

    Falls back to storing the full raw response as the summary with an empty
    topics list when the expected markers aren't found, rather than failing.
    Topics gain a real "(N)" count suffix when a parseable ТЕГИ block is present
    (E22-S1); older/malformed responses with no ТЕГИ block yield plain topic
    strings, unchanged from before.
    """
    summary_match = _SUMMARY_RE.search(text)
    topics_match = _TOPICS_RE.search(text)

    summary = summary_match.group(1).strip() if summary_match else text.strip()

    topics: list[str] = []
    if topics_match:
        for line in topics_match.group(1).strip().splitlines():
            cleaned = _TOPIC_NUMBERING_RE.sub("", line.strip()).strip()
            if cleaned:
                topics.append(cleaned)
    topics = topics[:5]

    topic_counts = _parse_topic_counts(text)
    if topic_counts:
        topics = [
            f"{topic} ({topic_counts[idx]})" if topic_counts.get(idx) else topic
            for idx, topic in enumerate(topics, start=1)
        ]

    return summary, topics


async def generate_run_summary(
    session: AsyncSession,
    run: AnalysisRun,
    *,
    user_id: uuid.UUID,
    client: AsyncAnthropic | None = None,
) -> None:
    """Synthesizes a run-level RU overview + top-5 topics from the run's item summaries.

    Never raises — a failure (no items, API error, unparseable response) sets
    summary_status=failed and returns, mirroring notify_run_complete's never-raises
    pattern (AC: this step must be non-fatal to the run).
    """
    settings = get_settings()
    try:
        rows = (
            await session.execute(
                select(ContentItem, Account.handle)
                .join(Account, ContentItem.account_id == Account.id)
                .where(ContentItem.run_id == run.id)
                .order_by(ContentItem.published_at.desc())
                .limit(_MAX_ITEMS)
            )
        ).all()

        prompt_lines: list[str] = []
        type_counts: Counter[ContentType] = Counter()
        for item, handle in rows:
            text = item.summary or item.caption
            if not text:
                continue
            type_label = _TYPE_LABELS_RU.get(item.type, "Пост")
            prompt_lines.append(f"{len(prompt_lines) + 1}. @{handle} ({type_label}): {text}")
            type_counts[item.type] += 1

        if not prompt_lines:
            run.summary_status = RunSummaryStatus.failed
            run.summary_generated_at = datetime.now(UTC)
            return

        format_counts_line = _format_counts_line(type_counts)

        _client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await _client.messages.create(
            model=settings.summary_model,
            max_tokens=500,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Форматы (точное количество, используй как есть): {format_counts_line}\n\n"
                        "Публикации запуска:\n" + "\n".join(prompt_lines)
                    ),
                }
            ],
        )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        summary_text, topics = parse_summary_response(text)

        run.summary_text = summary_text
        run.summary_topics = topics
        run.summary_status = RunSummaryStatus.done
        run.summary_generated_at = datetime.now(UTC)

        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=run.id,
                kind=KIND_CLAUDE_INPUT_TOKENS,
                quantity=response.usage.input_tokens,
                unit_cost_usd=Decimal(str(settings.claude_input_token_cost_usd)),
            )
        )
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=run.id,
                kind=KIND_CLAUDE_OUTPUT_TOKENS,
                quantity=response.usage.output_tokens,
                unit_cost_usd=Decimal(str(settings.claude_output_token_cost_usd)),
            )
        )
    except Exception:  # noqa: BLE001 — never fails the run (mirrors notify_run_complete)
        run.summary_status = RunSummaryStatus.failed
        run.summary_generated_at = datetime.now(UTC)
