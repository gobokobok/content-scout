import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from apify_client import ApifyClientAsync
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.models import (
    KIND_APIFY_COMMENT_RESULT,
    KIND_BRIGHTDATA_COMMENT_RESULT,
    ContentItem,
    UsageEvent,
)

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_APIFY_RUN_TIMEOUT_SECS = 120
_BRIGHTDATA_POLL_INTERVAL_SECS = 2.0
_BRIGHTDATA_POLL_ATTEMPTS = 30
_BRIGHTDATA_HTTP_TIMEOUT_SECS = 30.0


@dataclass(frozen=True)
class RawComment:
    external_id: str
    text: str
    author_username: str | None = None
    likes: int | None = None
    published_at: datetime | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ApifyCommentsFailedError(Exception):
    pass


class BrightDataCommentsFailedError(Exception):
    pass


class ApifyCommentsClient:
    """Primary vendor (D32): apidojo/instagram-comments-scraper-api, via the already-pinned
    apify-client — no new dependency for this leg."""

    def __init__(self, settings: Settings) -> None:
        self._client = ApifyClientAsync(token=settings.apify_api_token)
        self._actor_id = settings.apify_comments_actor_id
        self._max_charge_usd = Decimal(str(settings.apify_max_charge_per_fetch_usd))

    async def fetch_comments(self, post_url: str, limit: int) -> list[RawComment]:
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await self._fetch_once(post_url, limit)
            except Exception as exc:  # noqa: BLE001 — retried here, converted for the caller
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
        raise ApifyCommentsFailedError(str(last_exc)) from last_exc

    async def _fetch_once(self, post_url: str, limit: int) -> list[RawComment]:
        run = await self._client.actor(self._actor_id).call(
            run_input={"startUrls": [{"url": post_url}], "resultsLimit": limit},
            run_timeout=timedelta(seconds=_APIFY_RUN_TIMEOUT_SECS),
            max_total_charge_usd=self._max_charge_usd,
        )
        if run is None or run.status != "SUCCEEDED":
            status = run.status if run else "no run"
            raise ApifyCommentsFailedError(f"apidojo comments run for {post_url}: {status}")

        page = await self._client.dataset(run.default_dataset_id).list_items()
        valid_items = [item for item in page.items if "error" not in item]
        return [_normalize_apify_comment(item) for item in valid_items]


class BrightDataCommentsClient:
    """Fallback vendor (D32) — cross-company backstop for when the primary Apify actor fails a
    post. Bright Data's Dataset API is trigger-then-poll: POST a collection request, poll its
    snapshot status, then fetch the ready snapshot — a different shape from Apify's synchronous
    actor().call(), but still "send a URL, get structured JSON" (no DIY proxy pool, D2 unaffected).
    """

    def __init__(self, settings: Settings) -> None:
        self._token = settings.brightdata_api_token
        self._base_url = settings.brightdata_api_base_url
        self._dataset_id = settings.brightdata_ig_comments_dataset_id

    async def fetch_comments(self, post_url: str, limit: int) -> list[RawComment]:
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await self._fetch_once(post_url, limit)
            except Exception as exc:  # noqa: BLE001 — retried here, converted for the caller
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
        raise BrightDataCommentsFailedError(str(last_exc)) from last_exc

    async def _fetch_once(self, post_url: str, limit: int) -> list[RawComment]:
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=_BRIGHTDATA_HTTP_TIMEOUT_SECS) as client:
            trigger = await client.post(
                f"{self._base_url}/datasets/v3/trigger",
                params={"dataset_id": self._dataset_id, "include_errors": "true"},
                json=[{"url": post_url, "limit": limit}],
                headers=headers,
            )
            trigger.raise_for_status()
            snapshot_id = trigger.json()["snapshot_id"]

            for _ in range(_BRIGHTDATA_POLL_ATTEMPTS):
                progress = await client.get(
                    f"{self._base_url}/datasets/v3/progress/{snapshot_id}", headers=headers
                )
                progress.raise_for_status()
                body = progress.json()
                if body.get("status") == "ready":
                    break
                if body.get("status") == "failed":
                    raise BrightDataCommentsFailedError(f"snapshot {snapshot_id} failed")
                await asyncio.sleep(_BRIGHTDATA_POLL_INTERVAL_SECS)
            else:
                raise BrightDataCommentsFailedError(f"snapshot {snapshot_id} timed out")

            data = await client.get(
                f"{self._base_url}/datasets/v3/snapshot/{snapshot_id}",
                params={"format": "json"},
                headers=headers,
            )
            data.raise_for_status()
            items = data.json()

        return [_normalize_brightdata_comment(item) for item in items if "error" not in item]


def _normalize_apify_comment(item: dict[str, Any]) -> RawComment:
    return RawComment(
        external_id=str(item.get("id") or item.get("commentId") or uuid.uuid4()),
        text=item.get("text", ""),
        author_username=item.get("ownerUsername"),
        likes=item.get("likesCount"),
        published_at=_parse_timestamp(item.get("timestamp")),
        raw=item,
    )


def _normalize_brightdata_comment(item: dict[str, Any]) -> RawComment:
    return RawComment(
        external_id=str(item.get("comment_id") or uuid.uuid4()),
        text=item.get("comment_text", ""),
        author_username=item.get("user_name"),
        likes=item.get("likes"),
        published_at=_parse_timestamp(item.get("comment_date")),
        raw=item,
    )


def _parse_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _sort_and_cap(comments: list[RawComment], limit: int) -> list[RawComment]:
    """Empirically verifying whether apidojo's per-comment ranking field correlates with
    engagement order requires a live run (deferred to the DEV smoke test, same pattern as every
    other Apify-dependent verification in this project — see BACKLOG.md). Sorting client-side by
    likes descending is correct regardless of what we find, so it's the safe default rather than
    trusting vendor order blindly."""
    return sorted(comments, key=lambda c: c.likes or 0, reverse=True)[:limit]


async def fetch_comments(
    session: AsyncSession,
    item: ContentItem,
    *,
    user_id: uuid.UUID,
    settings: Settings,
    apify_client: ApifyCommentsClient | None = None,
    brightdata_client: BrightDataCommentsClient | None = None,
) -> list[RawComment]:
    """Fetches up to `deep_analysis_comments_per_post` comments for one post, primary-then-
    fallback (D32). Never raises — both vendors failing degrades to an empty list for this post
    (E17-S9), it does not fail the whole deep analysis. Records usage_events for whichever
    vendor actually served the fetch; nothing is recorded when both fail (no successful fetch to
    bill for).
    """
    limit = settings.deep_analysis_comments_per_post
    apify = apify_client or ApifyCommentsClient(settings)
    brightdata = brightdata_client or BrightDataCommentsClient(settings)

    try:
        comments = await apify.fetch_comments(item.url, limit)
        comments = _sort_and_cap(comments, limit)
        _record_apify_usage(session, user_id, item, len(comments), settings)
        return comments
    except ApifyCommentsFailedError as apify_exc:
        logger.warning(
            "Apify comment fetch failed for item_id=%s, trying Bright Data: %s",
            item.id,
            apify_exc,
        )

    try:
        comments = await brightdata.fetch_comments(item.url, limit)
        comments = _sort_and_cap(comments, limit)
        _record_brightdata_usage(session, user_id, item, settings)
        return comments
    except BrightDataCommentsFailedError as brightdata_exc:
        logger.warning(
            "Both comment vendors failed for item_id=%s (Apify already failed above); "
            "Bright Data: %s — this item's comments will be empty",
            item.id,
            brightdata_exc,
        )
        return []


def _record_apify_usage(
    session: AsyncSession,
    user_id: uuid.UUID,
    item: ContentItem,
    comments_count: int,
    settings: Settings,
) -> None:
    session.add(
        UsageEvent(
            user_id=user_id,
            run_id=item.run_id,
            kind=KIND_APIFY_COMMENT_RESULT,
            quantity=1,
            unit_cost_usd=Decimal(str(settings.apify_comment_query_cost_usd)),
        )
    )
    overage = max(0, comments_count - settings.apify_comment_included_comments)
    if overage > 0:
        session.add(
            UsageEvent(
                user_id=user_id,
                run_id=item.run_id,
                kind=KIND_APIFY_COMMENT_RESULT,
                quantity=overage,
                unit_cost_usd=Decimal(str(settings.apify_comment_overage_cost_usd)),
            )
        )


def _record_brightdata_usage(
    session: AsyncSession, user_id: uuid.UUID, item: ContentItem, settings: Settings
) -> None:
    session.add(
        UsageEvent(
            user_id=user_id,
            run_id=item.run_id,
            kind=KIND_BRIGHTDATA_COMMENT_RESULT,
            quantity=1,
            unit_cost_usd=Decimal(str(settings.brightdata_comment_request_cost_usd)),
        )
    )
