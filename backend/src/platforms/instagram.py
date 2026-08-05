import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from apify_client import ApifyClientAsync

from src.config import get_settings
from src.models import Account, ContentType
from src.platforms.base import ProfileInfo, RawContentItem
from src.services.apify_governor import acquire_apify_slot

logger = logging.getLogger(__name__)


class ApifyRunFailedError(Exception):
    pass


# apify/instagram-scraper's post "type" field.
_TYPE_MAP = {
    "Video": ContentType.reel,
    "Sidecar": ContentType.carousel,
    "Image": ContentType.post,
}

_MAX_ATTEMPTS = 3
_RESULTS_LIMIT = 50
# Instagram allows up to 3 pinned posts per profile; the actor returns them ahead of
# chronological order regardless of age. In item-limit ("last N publications") mode, requesting
# exactly `limit` results risks pinned posts silently eating into that budget, under-delivering
# real recent items. Request this many extra so at least `limit` real candidates remain after
# the real-published_at sort+cap in _fetch_once below.
_PINNED_POST_BUFFER = 3


class InstagramPlatform:
    """Apify-backed scraper. Nothing outside `platforms/` may import the Apify client directly."""

    slug = "instagram"

    def __init__(self) -> None:
        settings = get_settings()
        self._client = ApifyClientAsync(token=settings.apify_api_token)
        self._actor_id = settings.apify_ig_actor_id
        self._max_charge_usd = Decimal(str(settings.apify_max_charge_per_fetch_usd))
        self._memory_mbytes = settings.apify_actor_memory_mbytes
        self._max_concurrent_actor_runs = settings.apify_max_concurrent_actor_runs
        self._run_timeout_secs = settings.apify_content_scrape_timeout_secs

    async def fetch_content(
        self, account: Account, *, since: datetime | None, limit: int | None = None
    ) -> list[RawContentItem]:
        return await self._with_retries(lambda: self._fetch_once(account, since, limit))

    async def fetch_profile(self, account: Account) -> ProfileInfo:
        return await self._with_retries(lambda: self._fetch_profile_once(account))

    async def fetch_post(self, post_url: str) -> RawContentItem:
        return await self._with_retries(lambda: self._fetch_post_once(post_url))

    async def _with_retries[T](self, call: Callable[[], Awaitable[T]]) -> T:
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await call()
            except Exception as exc:  # noqa: BLE001 — retried here, re-raised to the caller
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    logger.warning(
                        "Apify call failed on attempt %d/%d, retrying: %s",
                        attempt + 1,
                        _MAX_ATTEMPTS,
                        exc,
                    )
                    await asyncio.sleep(2**attempt)
        assert last_exc is not None
        raise last_exc

    async def _fetch_once(
        self, account: Account, since: datetime | None, limit: int | None
    ) -> list[RawContentItem]:
        run_input: dict[str, Any] = {
            "directUrls": [account.normalized_url],
            "resultsType": "posts",
            "resultsLimit": (
                (limit + _PINNED_POST_BUFFER) if limit is not None else _RESULTS_LIMIT
            ),
        }
        # since=None means "last N publications" mode (item_limit) — no date cutoff, just the
        # most recent `limit` posts by real published_at (see the sort+cap below, not just
        # however many the actor happens to return before hitting resultsLimit).
        if since is not None:
            run_input["onlyPostsNewerThan"] = since.date().isoformat()

        async with acquire_apify_slot(self._max_concurrent_actor_runs):
            run = await self._client.actor(self._actor_id).call(
                run_input=run_input,
                run_timeout=timedelta(seconds=self._run_timeout_secs),
                max_total_charge_usd=self._max_charge_usd,
                memory_mbytes=self._memory_mbytes,
            )
        if run is None:
            raise ApifyRunFailedError(f"Apify actor run for @{account.handle} returned no run")
        if run.status != "SUCCEEDED":
            raise ApifyRunFailedError(
                f"Apify actor run for @{account.handle} ended with status {run.status}"
            )

        page = await self._client.dataset(run.default_dataset_id).list_items()
        # The actor emits an {"error": ...} placeholder instead of a post when a profile is
        # private/deleted/blocked — treat that as a fetch failure (caught per-account by the
        # worker), never as a real content item.
        valid_items = [item for item in page.items if "error" not in item]
        error_items = [item for item in page.items if "error" in item]
        if error_items and not valid_items:
            reason = error_items[0].get("errorDescription") or error_items[0]["error"]
            raise ApifyRunFailedError(f"@{account.handle}: {reason}")

        items = [_normalize(item) for item in valid_items]
        # Pinned posts appear at the top of the profile regardless of real publish date, and can
        # be months/years old — sort by real published_at (descending) rather than trusting the
        # actor's pin-first ordering, so a pinned post is only kept when it genuinely is among
        # the most recent items, and item-limit mode's `limit` below reflects real chronological
        # order (the "last N publications" the user actually asked for).
        items.sort(key=lambda i: i.published_at, reverse=True)
        if since is not None:
            # Defensive re-filter on top of the actor's own onlyPostsNewerThan — a pinned old
            # post is not guaranteed to be excluded by the actor's date cutoff the same way a
            # normal chronological post would be.
            items = [i for i in items if i.published_at >= since]
        if limit is not None:
            items = items[:limit]
        return items

    async def _fetch_post_once(self, post_url: str) -> RawContentItem:
        """directUrls also accepts a direct post/reel URL (not just a profile URL) — the same
        actor call shape as _fetch_once, just resultsLimit=1 and no date/limit scope, since
        there's exactly one post to return."""
        async with acquire_apify_slot(self._max_concurrent_actor_runs):
            run = await self._client.actor(self._actor_id).call(
                run_input={
                    "directUrls": [post_url],
                    "resultsType": "posts",
                    "resultsLimit": 1,
                },
                run_timeout=timedelta(seconds=self._run_timeout_secs),
                max_total_charge_usd=self._max_charge_usd,
                memory_mbytes=self._memory_mbytes,
            )
        if run is None:
            raise ApifyRunFailedError(f"Apify post run for {post_url} returned no run")
        if run.status != "SUCCEEDED":
            raise ApifyRunFailedError(
                f"Apify post run for {post_url} ended with status {run.status}"
            )

        page = await self._client.dataset(run.default_dataset_id).list_items()
        valid_items = [item for item in page.items if "error" not in item]
        if not valid_items:
            error_items = [item for item in page.items if "error" in item]
            reason = (
                error_items[0].get("errorDescription") or error_items[0]["error"]
                if error_items
                else "empty response"
            )
            raise ApifyRunFailedError(f"{post_url}: {reason}")

        return _normalize(valid_items[0])

    async def _fetch_profile_once(self, account: Account) -> ProfileInfo:
        async with acquire_apify_slot(self._max_concurrent_actor_runs):
            run = await self._client.actor(self._actor_id).call(
                run_input={
                    "directUrls": [account.normalized_url],
                    "resultsType": "details",
                },
                run_timeout=timedelta(seconds=self._run_timeout_secs),
                max_total_charge_usd=self._max_charge_usd,
                memory_mbytes=self._memory_mbytes,
            )
        if run is None:
            raise ApifyRunFailedError(f"Apify profile run for @{account.handle} returned no run")
        if run.status != "SUCCEEDED":
            raise ApifyRunFailedError(
                f"Apify profile run for @{account.handle} ended with status {run.status}"
            )

        page = await self._client.dataset(run.default_dataset_id).list_items()
        items = page.items
        if not items or "error" in items[0]:
            reason = items[0].get("errorDescription") if items else "empty response"
            raise ApifyRunFailedError(f"@{account.handle}: {reason}")

        detail = items[0]
        return ProfileInfo(
            followers_count=detail.get("followersCount"),
            display_name=detail.get("fullName") or None,
            avatar_url=detail.get("profilePicUrl") or detail.get("profilePicUrlHD"),
        )


def _normalize(item: dict[str, Any]) -> RawContentItem:
    content_type = _TYPE_MAP.get(item.get("type", "Image"), ContentType.post)
    published_at = _parse_timestamp(item.get("timestamp"))
    caption = item.get("caption")
    title = caption.splitlines()[0][:300] if caption else None

    return RawContentItem(
        external_id=str(item.get("id") or item.get("shortCode") or item.get("url", "")),
        type=content_type,
        published_at=published_at,
        url=item.get("url", ""),
        title=title,
        cover_url=item.get("displayUrl"),
        caption=caption,
        likes=item.get("likesCount"),
        views=item.get("videoViewCount") if content_type == ContentType.reel else None,
        comments=item.get("commentsCount"),
        raw=item,
    )


def _parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(UTC)
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))
