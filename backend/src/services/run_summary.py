import re
import uuid
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

_MAX_ITEMS = 150

# Mirrors docs/PROMPTS.md "Run summary (E15-S1)" — change there first, then here.
SYSTEM_PROMPT = """\
Ты — аналитик контента социальных сетей. По списку публикаций аккаунтов-конкурентов \
(аккаунт, тип, краткое описание) составь общий обзор запуска анализа.

Правила:
- Ответ строго в следующем формате, на русском языке:
РЕЗЮМЕ: <2–4 предложения о том, какой контент публикуют конкуренты в этой подборке \
и какие темы или форматы встречаются чаще всего>
ТЕМЫ:
1. <тема>
2. <тема>
3. <тема>
4. <тема>
5. <тема>
- Резюме описывает контент, а не оценивает его успех и не даёт рекомендаций.
- Темы — короткие (2–4 слова) названия тем/форматов, без нумерации внутри текста темы.
- Не пересказывай хэштеги."""

_SUMMARY_RE = re.compile(r"РЕЗЮМЕ:\s*(.+?)(?=\nТЕМЫ:|\Z)", re.DOTALL)
_TOPICS_RE = re.compile(r"ТЕМЫ:\s*(.+)", re.DOTALL)
_TOPIC_NUMBERING_RE = re.compile(r"^\d+[.)]\s*")


def parse_summary_response(text: str) -> tuple[str, list[str]]:
    """Deterministically parses the РЕЗЮМЕ:/ТЕМЫ: text protocol.

    Falls back to storing the full raw response as the summary with an empty
    topics list when the expected markers aren't found, rather than failing.
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

    return summary, topics[:5]


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
        for item, handle in rows:
            text = item.summary or item.caption
            if not text:
                continue
            type_label = _TYPE_LABELS_RU.get(item.type, "Пост")
            prompt_lines.append(f"- @{handle} ({type_label}): {text}")

        if not prompt_lines:
            run.summary_status = RunSummaryStatus.failed
            run.summary_generated_at = datetime.now(UTC)
            return

        _client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await _client.messages.create(
            model=settings.summary_model,
            max_tokens=500,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Публикации запуска:\n" + "\n".join(prompt_lines),
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
