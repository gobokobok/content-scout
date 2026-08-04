import asyncio
import json
import uuid
from decimal import Decimal
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    ContentItem,
    ContentType,
    DeepAnalysis,
    DeepAnalysisItem,
    DeepAnalysisItemStatus,
    UsageEvent,
    User,
)
from src.services.comment_scraper import RawComment, fetch_comments
from src.services.deep_analysis import charge_tokens_for_item
from src.services.summarizer import _fetch_image_block  # deliberate D29 reuse, not duplicated here

_TYPE_LABELS_RU = {
    ContentType.reel: "Reels",
    ContentType.post: "Пост",
    ContentType.carousel: "Карусель",
    ContentType.video: "Видео",
    ContentType.short: "Шортс",
}

# Mirrors docs/PROMPTS.md "Deep analysis item extraction (E17-S3)" — change there first.
SYSTEM_PROMPT = """\
Ты — аналитик контента социальных сетей. По подписи и обложке публикации Instagram, а также \
по комментариям под ней, извлеки структурированные сигналы.

Отвечай СТРОГО в виде одного JSON-объекта без пояснений, точно по этой схеме:
{
  "topic": "<короткая тема публикации, 2-4 слова>",
  "format": "<формат публикации, например: обучающий, юмор, закулисье, обзор>",
  "hook_type": "<тип зацепки в начале, например: вопрос, шок-факт, интрига, личная история>",
  "has_cta": <true или false — есть ли призыв к действию (подписаться, купить, перейти по ссылке)>,
  "sentiment": "<positive, neutral, negative или mixed — тональность комментариев>",
  "complaints": ["<жалоба 1>", "..."],
  "praises": ["<похвала 1>", "..."],
  "questions": ["<вопрос без ответа 1>", "..."],
  "notable_phrases": ["<заметная цитата 1>", "..."]
}

Правила:
- Если комментариев нет, sentiment оставь "neutral", а списки — пустыми массивами.
- Каждый список — максимум 5 коротких элементов на русском.
- Не добавляй никакого текста вне JSON."""

_MAX_ATTEMPTS = 3
_IMAGE_FETCH_TIMEOUT_SECS = 10.0


async def extract_deep_analysis_items(
    session: AsyncSession,
    analysis: DeepAnalysis,
    items: list[ContentItem],
    *,
    user: User,
    comments_limit: int | None = None,
    client: AsyncAnthropic | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> bool:
    """One Haiku call per item (D33): content-signal tags + comment-derived sentiment/
    complaints/praises/questions. Reuses summarizer.py's concurrency scaffolding and D29's cost
    policy (512px cover images).

    D50: charges incrementally as each item's real work completes (1 token/publication +
    1/comment actually analyzed via `charge_tokens_for_item`), processed in
    concurrency-bounded batches with a balance check before each one — mirrors
    worker.py:process_run's per-batch token_balance_exhausted pattern. Returns True if the
    balance ran out before every item could be processed (some items may simply never get a
    DeepAnalysisItem row, rather than a `failed` one, since no work was attempted on them).

    Never raises for a single item's failure — an unparseable/failed extraction stores a
    `failed` DeepAnalysisItem row (metrics-only degrade) rather than failing the analysis.
    Drops the previous Message Batches API path (D50): an all-or-nothing remote batch call
    can't support this per-batch balance-exhaustion stop, and Analysis's 1-account/1-post cap
    makes the large batch sizes that path targeted rare.
    """
    settings = get_settings()
    _client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)
    _own_http = http_client is None
    _http = http_client or httpx.AsyncClient(timeout=_IMAGE_FETCH_TIMEOUT_SECS)
    batch_size = max(1, settings.summary_concurrency)
    token_exhausted = False

    try:
        for start in range(0, len(items), batch_size):
            if user.token_balance <= 0:
                token_exhausted = True
                break

            batch = items[start : start + batch_size]
            if user.token_balance < len(batch):
                batch = batch[: user.token_balance]
                token_exhausted = True

            comments_by_item: dict[uuid.UUID, list[RawComment]] = {}
            for item in batch:
                comments_by_item[item.id] = await fetch_comments(
                    session,
                    item,
                    user_id=user.id,
                    settings=settings,
                    limit_override=comments_limit,
                )

            semaphore = asyncio.Semaphore(settings.summary_concurrency)

            async def _one(item: ContentItem) -> None:
                async with semaphore:
                    await _extract_item(
                        session,
                        _client,
                        _http,
                        item,
                        comments_by_item[item.id],
                        analysis.id,
                        settings,
                        user_id=user.id,
                    )

            await asyncio.gather(*(_one(item) for item in batch))

            for item in batch:
                charge_tokens_for_item(
                    analysis, user, comments_analyzed_count=len(comments_by_item[item.id])
                )
            await session.commit()

            if token_exhausted:
                break

        return token_exhausted
    finally:
        if _own_http:
            await _http.aclose()


def _build_user_text(item: ContentItem, comments: list[RawComment]) -> str:
    type_label = _TYPE_LABELS_RU.get(item.type, "Пост")
    lines = [
        f"Тип: {type_label}",
        f"Подпись: {item.caption or '(без подписи)'}",
    ]
    if comments:
        lines.append("Комментарии:")
        # comments is already capped to the resolved comments_limit by fetch_comments'
        # _sort_and_cap — every comment here was actually fetched and charged for
        # (charge_tokens_for_item uses this same list's length), so none get silently
        # dropped from the analysis the user is paying for.
        for c in comments:
            author = f"@{c.author_username}" if c.author_username else "аноним"
            lines.append(f"- {author}: {c.text}")
    else:
        lines.append("Комментарии: отсутствуют")
    return "\n".join(lines)


async def _build_content_blocks(
    http_client: httpx.AsyncClient,
    item: ContentItem,
    comments: list[RawComment],
    settings: Settings,
) -> list[Any]:
    blocks: list[Any] = []
    skip_image = (
        item.caption is not None and len(item.caption) > settings.summary_skip_image_caption_chars
    )
    if item.cover_url and not skip_image:
        image_block = await _fetch_image_block(http_client, item.cover_url, settings)
        if image_block:
            blocks.append(image_block)
    blocks.append({"type": "text", "text": _build_user_text(item, comments)})
    return blocks


def _parse_extraction(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        cleaned = cleaned.removesuffix("```").strip()
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _store_extraction(
    item: ContentItem,
    comments: list[RawComment],
    deep_analysis_id: uuid.UUID,
    data: dict[str, Any] | None,
) -> DeepAnalysisItem:
    if data is None:
        return DeepAnalysisItem(
            id=uuid.uuid4(),
            deep_analysis_id=deep_analysis_id,
            content_item_id=item.id,
            status=DeepAnalysisItemStatus.failed,
            comments_analyzed_count=len(comments),
        )

    def _str_list(key: str) -> list[str] | None:
        value = data.get(key)
        if not isinstance(value, list):
            return None
        return [str(v)[:300] for v in value[:5] if v]

    return DeepAnalysisItem(
        id=uuid.uuid4(),
        deep_analysis_id=deep_analysis_id,
        content_item_id=item.id,
        status=DeepAnalysisItemStatus.done,
        topic=(str(data["topic"])[:200] if data.get("topic") else None),
        content_format=(str(data["format"])[:100] if data.get("format") else None),
        hook_type=(str(data["hook_type"])[:100] if data.get("hook_type") else None),
        has_cta=(bool(data["has_cta"]) if isinstance(data.get("has_cta"), bool) else None),
        sentiment=(str(data["sentiment"])[:20] if data.get("sentiment") else None),
        complaints=_str_list("complaints"),
        praises=_str_list("praises"),
        questions=_str_list("questions"),
        notable_phrases=_str_list("notable_phrases"),
        comments_analyzed_count=len(comments),
    )


async def _extract_item(
    session: AsyncSession,
    client: AsyncAnthropic,
    http_client: httpx.AsyncClient,
    item: ContentItem,
    comments: list[RawComment],
    deep_analysis_id: uuid.UUID,
    settings: Settings,
    *,
    user_id: uuid.UUID,
) -> None:
    content_blocks = await _build_content_blocks(http_client, item, comments, settings)

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=settings.summary_model,
                    max_tokens=500,
                    temperature=0.2,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content_blocks}],
                ),
                timeout=30.0,
            )
        except Exception:  # noqa: BLE001 — retried here; falls back to a failed row after
            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(2**attempt)
            continue

        text = "".join(block.text for block in response.content if block.type == "text").strip()
        data = _parse_extraction(text)
        # Tokens were spent regardless of whether the response parsed — record the cost
        # every time a call actually returns, not just on the attempt that succeeds.
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=item.run_id,
                kind=KIND_CLAUDE_INPUT_TOKENS,
                quantity=response.usage.input_tokens,
                unit_cost_usd=Decimal(str(settings.claude_input_token_cost_usd)),
            )
        )
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=item.run_id,
                kind=KIND_CLAUDE_OUTPUT_TOKENS,
                quantity=response.usage.output_tokens,
                unit_cost_usd=Decimal(str(settings.claude_output_token_cost_usd)),
            )
        )
        if data is not None:
            session.add(_store_extraction(item, comments, deep_analysis_id, data))
            return
        if attempt < _MAX_ATTEMPTS - 1:
            await asyncio.sleep(2**attempt)

    session.add(_store_extraction(item, comments, deep_analysis_id, None))
