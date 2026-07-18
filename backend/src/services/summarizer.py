import asyncio
import base64
import uuid
from decimal import Decimal
from io import BytesIO
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.models import (
    KIND_CLAUDE_INPUT_TOKENS,
    KIND_CLAUDE_OUTPUT_TOKENS,
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

_MAX_IMAGE_SIDE = 1024
_IMAGE_FETCH_TIMEOUT_SECS = 10.0
_MAX_ATTEMPTS = 3


async def summarize_run_items(
    session: AsyncSession,
    items: list[ContentItem],
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
) -> None:
    """Summarizes each item in place (sets `item.summary`) with bounded concurrency."""
    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    semaphore = asyncio.Semaphore(settings.summary_concurrency)

    async def _one(item: ContentItem) -> None:
        async with semaphore:
            await _summarize_item(session, client, item, settings, user_id=user_id, run_id=run_id)

    await asyncio.gather(*(_one(item) for item in items))


async def _summarize_item(
    session: AsyncSession,
    client: AsyncAnthropic,
    item: ContentItem,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    run_id: uuid.UUID,
) -> None:
    if not item.caption and not item.cover_url:
        item.summary = FALLBACK_TEXT
        return

    content_blocks: list[Any] = []
    image_block = await _fetch_image_block(item.cover_url) if item.cover_url else None
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


async def _fetch_image_block(url: str) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=_IMAGE_FETCH_TIMEOUT_SECS) as http_client:
            resp = await http_client.get(url)
            resp.raise_for_status()
        image = Image.open(BytesIO(resp.content))
        image.thumbnail((_MAX_IMAGE_SIDE, _MAX_IMAGE_SIDE))
        buf = BytesIO()
        image.convert("RGB").save(buf, format="JPEG")
        data = base64.b64encode(buf.getvalue()).decode()
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": data},
        }
    except Exception:  # noqa: BLE001 — an unfetchable image just means text-only summary
        return None
