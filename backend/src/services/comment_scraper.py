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
from src.services.apify_governor import acquire_apify_slot

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3
_APIFY_RUN_TIMEOUT_SECS = 120
_APIFY_BATCH_RUN_TIMEOUT_PER_POST_SECS = 60
_BRIGHTDATA_POLL_INTERVAL_SECS = 2.0
_BRIGHTDATA_POLL_ATTEMPTS = 30
_BRIGHTDATA_HTTP_TIMEOUT_SECS = 30.0

# E20-S1: which field on a batched comment item identifies the post (from startUrls) it came
# from. Not independently verifiable outside a live Apify account (no live Apify access in
# this sandbox — same constraint D41's own investigation had for the input schema), so this
# tries several plausible field-name conventions rather than assuming one. See
# ApifyCommentsClient._fetch_batch_once's all-unmatched abort for the safety net if every one
# of these guesses turns out wrong for the actor's real output shape — confirm on the first
# real DEV batched run (this story's Handover) and trim/correct this list then.
_POST_URL_FIELD_CANDIDATES = ("inputUrl", "postUrl", "url", "inputSource", "post_url")


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
        self._memory_mbytes = settings.apify_actor_memory_mbytes
        self._max_concurrent_actor_runs = settings.apify_max_concurrent_actor_runs

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
        async with acquire_apify_slot(self._max_concurrent_actor_runs):
            run = await self._client.actor(self._actor_id).call(
                # D41: the real field is maxItems, not resultsLimit (which the actor's schema
                # doesn't recognize at all — Apify silently ignores unknown fields, so this cap
                # has likely never been server-side enforced before this fix).
                run_input={"startUrls": [{"url": post_url}], "maxItems": limit},
                run_timeout=timedelta(seconds=_APIFY_RUN_TIMEOUT_SECS),
                max_total_charge_usd=self._max_charge_usd,
                memory_mbytes=self._memory_mbytes,
            )
        if run is None or run.status != "SUCCEEDED":
            status = run.status if run else "no run"
            raise ApifyCommentsFailedError(f"apidojo comments run for {post_url}: {status}")

        page = await self._client.dataset(run.default_dataset_id).list_items()
        valid_items = [item for item in page.items if "error" not in item]
        return [_normalize_apify_comment(item) for item in valid_items]

    async def fetch_comments_batch(
        self, post_urls: list[str], per_post_limit: int
    ) -> dict[str, list[RawComment]]:
        """One actor call for many posts (E20-S1) instead of one call per post — cuts
        sequential round-trips and per-call cold-start overhead by roughly the batch size.
        Retries the whole batch up to _MAX_ATTEMPTS times, same policy as fetch_comments.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await self._fetch_batch_once(post_urls, per_post_limit)
            except Exception as exc:  # noqa: BLE001 — retried here, converted for the caller
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
        raise ApifyCommentsFailedError(str(last_exc)) from last_exc

    async def _fetch_batch_once(
        self, post_urls: list[str], per_post_limit: int
    ) -> dict[str, list[RawComment]]:
        # maxItems is a global cap across the whole run, not per-post (verified against the
        # actor's public input schema) — request the batch-wide ceiling and let _sort_and_cap
        # enforce the per-post limit downstream, after grouping.
        max_items = len(post_urls) * per_post_limit
        timeout_secs = max(
            _APIFY_RUN_TIMEOUT_SECS, _APIFY_BATCH_RUN_TIMEOUT_PER_POST_SECS * len(post_urls)
        )
        async with acquire_apify_slot(self._max_concurrent_actor_runs):
            run = await self._client.actor(self._actor_id).call(
                run_input={
                    "startUrls": [{"url": u} for u in post_urls],
                    "maxItems": max_items,
                },
                run_timeout=timedelta(seconds=timeout_secs),
                max_total_charge_usd=self._max_charge_usd * len(post_urls),
                memory_mbytes=self._memory_mbytes,
            )
        if run is None or run.status != "SUCCEEDED":
            status = run.status if run else "no run"
            raise ApifyCommentsFailedError(
                f"apidojo batched comments run ({len(post_urls)} posts): {status}"
            )

        page = await self._client.dataset(run.default_dataset_id).list_items()
        valid_items = [item for item in page.items if "error" not in item]

        grouped: dict[str, list[RawComment]] = {u: [] for u in post_urls}
        unmatched = 0
        for item in valid_items:
            matched_url = _match_post_url(item, post_urls)
            if matched_url is None:
                unmatched += 1
                continue
            grouped[matched_url].append(_normalize_apify_comment(item))

        if valid_items and unmatched == len(valid_items):
            # Every item failed to match a known post URL — a strong signal the field-name
            # guess (_POST_URL_FIELD_CANDIDATES) is wrong for this actor version, not that the
            # posts genuinely had no comments. Abort the whole batch rather than silently
            # return all-empty results; the caller falls back to the safe per-post path.
            raise ApifyCommentsFailedError(
                "apidojo batched comments run: no items could be matched back to a source "
                "post URL — grouping field guess likely wrong for this actor version"
            )
        if unmatched:
            logger.warning(
                "apidojo batched comments run: %d/%d items could not be matched to a source "
                "post URL",
                unmatched,
                len(valid_items),
            )
        return grouped


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


def _match_post_url(item: dict[str, Any], known_urls: list[str]) -> str | None:
    """Best-effort match of one batched comment item back to the post URL it came from —
    see _POST_URL_FIELD_CANDIDATES' comment for why this is a guess, not a verified field."""
    known = {u.rstrip("/"): u for u in known_urls}
    for field_name in _POST_URL_FIELD_CANDIDATES:
        value = item.get(field_name)
        if isinstance(value, str) and value.rstrip("/") in known:
            return known[value.rstrip("/")]
    return None


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
    limit_override: int | None = None,
    apify_client: ApifyCommentsClient | None = None,
    brightdata_client: BrightDataCommentsClient | None = None,
) -> list[RawComment]:
    """Fetches up to `limit_override` (or `deep_analysis_comments_per_post` when unset) comments
    for one post, primary-then-fallback (D32). `limit_override` is D49's post-mode
    "top N comments" field, user-configurable per Analysis run; account mode always leaves it
    unset and gets the account-wide default. Never raises — both vendors failing degrades to an
    empty list for this post (E17-S9), it does not fail the whole deep analysis. Records
    usage_events for whichever vendor actually served the fetch; nothing is recorded when both
    fail (no successful fetch to bill for).
    """
    limit = limit_override or settings.deep_analysis_comments_per_post
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


async def fetch_comments_batch(
    session: AsyncSession,
    items: list[ContentItem],
    *,
    user_id: uuid.UUID,
    settings: Settings,
    limit_override: int | None = None,
    apify_client: ApifyCommentsClient | None = None,
    brightdata_client: BrightDataCommentsClient | None = None,
) -> dict[uuid.UUID, list[RawComment]]:
    """Batched sibling of fetch_comments (E20-S1): one Apify actor call for the whole `items`
    batch instead of one sequential call per post — the real bottleneck this story targets
    (a 130-item run meant ~26 sequential rounds of actor cold-starts). Falls back to the
    original per-item primary-then-fallback path (fetch_comments, unchanged) for every item in
    the batch if the batched call fails outright, so Bright Data still covers whatever the
    batched Apify call didn't — never raises, same never-fails contract as fetch_comments.
    Cost accounting stays per-post either way (_record_apify_usage called once per item) —
    batching changes latency, not what gets billed.
    """
    if not items:
        return {}
    limit = limit_override or settings.deep_analysis_comments_per_post
    apify = apify_client or ApifyCommentsClient(settings)
    brightdata = brightdata_client or BrightDataCommentsClient(settings)

    try:
        grouped_by_url = await apify.fetch_comments_batch([item.url for item in items], limit)
        result: dict[uuid.UUID, list[RawComment]] = {}
        for item in items:
            comments = _sort_and_cap(grouped_by_url.get(item.url, []), limit)
            result[item.id] = comments
            _record_apify_usage(session, user_id, item, len(comments), settings)
        return result
    except ApifyCommentsFailedError as apify_exc:
        logger.warning(
            "Batched Apify comment fetch failed for %d items, falling back to the per-item "
            "path (Apify retry, then Bright Data) for each: %s",
            len(items),
            apify_exc,
        )

    return {
        item.id: await fetch_comments(
            session,
            item,
            user_id=user_id,
            settings=settings,
            limit_override=limit_override,
            apify_client=apify,
            brightdata_client=brightdata,
        )
        for item in items
    }


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
