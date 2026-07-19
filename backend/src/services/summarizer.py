import asyncio
import base64
import uuid
from decimal import Decimal
from io import BytesIO
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
    AnalysisRun,
    ContentItem,
    ContentType,
    UsageEvent,
)

FALLBACK_TEXT = "Описание недоступно"

_TYPE_LABELS_RU = {
    ContentType.reel: "Reels",
    ContentType.post: "Пост",
    ContentType.carousel: "Карусель",
}

# Mirrors docs/PROMPTS.md — change there first, then here.
SYSTEM_PROMPT = """\
Ты — аналитик контента социальных сетей. По подписи к публикации Instagram \
и её обложке составь краткое описание содержания публикации.

Правила:
- 1–2 предложения, на русском языке.
- Описывай, о чём контент (тема, формат, что показано/рассказано), а не его популярность.
- Не пересказывай хэштеги и призывы подписаться.
- Если подпись на другом языке — всё равно отвечай по-русски.
- Отвечай только описанием, без вступлений."""

_IMAGE_FETCH_TIMEOUT_SECS = 10.0
_MAX_ATTEMPTS = 3
_BATCH_POLL_INTERVAL_SECS = 10.0


async def summarize_run_items(
    session: AsyncSession,
    items: list[ContentItem],
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    client: AsyncAnthropic | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Summarizes each item in-place with bounded concurrency or Message Batches API.

    Pass `client` and `http_client` to reuse connections across batches within a run.
    When `project_id` is provided, items whose external_id already has a summary
    in any prior run of the same project are reused without a Claude call.
    """
    settings = get_settings()
    _client = client or AsyncAnthropic(api_key=settings.anthropic_api_key)
    _own_http = http_client is None
    _http = (
        http_client
        if http_client is not None
        else httpx.AsyncClient(timeout=_IMAGE_FETCH_TIMEOUT_SECS)
    )

    try:
        # --- Cross-run summary reuse ---
        pending: list[ContentItem] = []
        for item in items:
            if project_id and await _reuse_summary_if_available(session, item, project_id, run_id):
                continue
            pending.append(item)

        if not pending:
            return

        # --- Message Batches API path (≥ threshold items) ---
        if len(pending) >= settings.summary_batch_threshold:
            try:
                await _summarize_via_batches(
                    session,
                    _client,
                    _http,
                    pending,
                    settings,
                    user_id=user_id,
                    run_id=run_id,
                )
                return
            except Exception:  # noqa: BLE001 — fall back to concurrent path on any batch failure
                pass

        # --- Concurrent per-item path ---
        semaphore = asyncio.Semaphore(settings.summary_concurrency)

        async def _one(item: ContentItem) -> None:
            async with semaphore:
                await _summarize_item(
                    session,
                    _client,
                    _http,
                    item,
                    settings,
                    user_id=user_id,
                    run_id=run_id,
                )

        await asyncio.gather(*(_one(item) for item in pending))

    finally:
        if _own_http:
            await _http.aclose()


async def _reuse_summary_if_available(
    session: AsyncSession,
    item: ContentItem,
    project_id: uuid.UUID,
    run_id: uuid.UUID,
) -> bool:
    """Copy summary from the most recent prior run item with the same external_id in this project.

    Returns True if a prior summary was found and copied (no Claude call needed).
    """
    prior = await session.scalar(
        select(ContentItem)
        .join(AnalysisRun, ContentItem.run_id == AnalysisRun.id)
        .where(
            AnalysisRun.project_id == project_id,
            AnalysisRun.id != run_id,
            ContentItem.external_id == item.external_id,
            ContentItem.summary.is_not(None),
            ContentItem.summary != FALLBACK_TEXT,
        )
        .order_by(ContentItem.created_at.desc())
        .limit(1)
    )
    if prior is not None:
        item.summary = prior.summary
        return True
    return False


async def _build_content_blocks(
    http_client: httpx.AsyncClient,
    item: ContentItem,
    settings: Settings,
) -> list[Any]:
    """Assemble the user-turn content blocks for a single item."""
    content_blocks: list[Any] = []

    skip_image = (
        item.caption is not None and len(item.caption) > settings.summary_skip_image_caption_chars
    )
    if item.cover_url and not skip_image:
        image_block = await _fetch_image_block(http_client, item.cover_url, settings)
        if image_block:
            content_blocks.append(image_block)

    content_blocks.append(
        {
            "type": "text",
            "text": (
                f"Тип: {_TYPE_LABELS_RU.get(item.type, 'Пост')}\n"
                f"Подпись: {item.caption or '(без подписи)'}"
            ),
        }
    )
    return content_blocks


async def _summarize_item(
    session: AsyncSession,
    client: AsyncAnthropic,
    http_client: httpx.AsyncClient,
    item: ContentItem,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
) -> None:
    if not item.caption and not item.cover_url:
        item.summary = FALLBACK_TEXT
        return

    content_blocks = await _build_content_blocks(http_client, item, settings)

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=settings.summary_model,
                    max_tokens=150,
                    temperature=0.2,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content_blocks}],
                ),
                timeout=30.0,
            )
        except Exception:  # noqa: BLE001 — retried here; falls back to placeholder after
            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(2**attempt)
            continue

        text = "".join(block.text for block in response.content if block.type == "text").strip()
        item.summary = text or FALLBACK_TEXT
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=run_id,
                kind=KIND_CLAUDE_INPUT_TOKENS,
                quantity=response.usage.input_tokens,
                unit_cost_usd=Decimal(str(settings.claude_input_token_cost_usd)),
            )
        )
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=run_id,
                kind=KIND_CLAUDE_OUTPUT_TOKENS,
                quantity=response.usage.output_tokens,
                unit_cost_usd=Decimal(str(settings.claude_output_token_cost_usd)),
            )
        )
        return

    item.summary = FALLBACK_TEXT


async def _summarize_via_batches(
    session: AsyncSession,
    client: AsyncAnthropic,
    http_client: httpx.AsyncClient,
    items: list[ContentItem],
    settings: Settings,
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
) -> None:
    """Submit a Message Batch, poll until ended, map results back to items and usage_events."""
    # Build content blocks for all items (can't skip an item mid-batch if no caption/image)
    item_by_id: dict[str, ContentItem] = {}
    requests = []
    for item in items:
        if not item.caption and not item.cover_url:
            item.summary = FALLBACK_TEXT
            continue
        blocks = await _build_content_blocks(http_client, item, settings)
        custom_id = str(item.id)
        item_by_id[custom_id] = item
        requests.append(
            {
                "custom_id": custom_id,
                "params": {
                    "model": settings.summary_model,
                    "max_tokens": 150,
                    "temperature": 0.2,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": blocks}],
                },
            }
        )

    if not requests:
        return

    batch = await client.messages.batches.create(requests=requests)

    # Poll until processing_status == "ended"
    while batch.processing_status != "ended":
        await asyncio.sleep(_BATCH_POLL_INTERVAL_SECS)
        batch = await client.messages.batches.retrieve(batch.id)

    # Map results back to items and record usage
    async for result in await client.messages.batches.results(batch.id):
        item = item_by_id.get(result.custom_id)
        if item is None:
            continue
        if result.result.type == "succeeded":
            msg = result.result.message
            text = "".join(b.text for b in msg.content if b.type == "text").strip()
            item.summary = text or FALLBACK_TEXT
            session.add(
                UsageEvent(
                    user_id=user_id,
                    run_id=run_id,
                    kind=KIND_CLAUDE_INPUT_TOKENS,
                    quantity=msg.usage.input_tokens,
                    unit_cost_usd=Decimal(str(settings.claude_input_token_cost_usd)),
                )
            )
            session.add(
                UsageEvent(
                    user_id=user_id,
                    run_id=run_id,
                    kind=KIND_CLAUDE_OUTPUT_TOKENS,
                    quantity=msg.usage.output_tokens,
                    unit_cost_usd=Decimal(str(settings.claude_output_token_cost_usd)),
                )
            )
        else:
            item.summary = FALLBACK_TEXT


async def _fetch_image_block(
    http_client: httpx.AsyncClient,
    url: str,
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    max_side = settings.summary_image_max_side if settings else 512
    try:
        resp = await http_client.get(url)
        resp.raise_for_status()
        image = Image.open(BytesIO(resp.content))
        image.thumbnail((max_side, max_side))
        buf = BytesIO()
        image.convert("RGB").save(buf, format="JPEG")
        data = base64.b64encode(buf.getvalue()).decode()
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
        }
    except Exception:  # noqa: BLE001 — an unfetchable image just means text-only summary
        return None
