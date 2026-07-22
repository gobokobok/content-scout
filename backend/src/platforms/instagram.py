import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from apify_client import ApifyClientAsync

from src.config import get_settings
from src.models import Account, ContentType
from src.platforms.base import ProfileInfo, RawContentItem


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
_RUN_TIMEOUT_SECS = 180


class InstagramPlatform:
    """Apify-backed scraper. Nothing outside `platforms/` may import the Apify client directly."""

    slug = "instagram"

    def __init__(self) -> None:
        settings = get_settings()
        self._client = ApifyClientAsync(token=settings.apify_api_token)
        self._actor_id = settings.apify_ig_actor_id
        self._max_charge_usd = Decimal(str(settings.apify_max_charge_per_fetch_usd))

    async def fetch_content(
        self, account: Account, *, since: datetime | None, limit: int | None = None
    ) -> list[RawContentItem]:
        return await self._with_retries(lambda: self._fetch_once(account, since, limit))

    async def fetch_profile(self, account: Account) -> ProfileInfo:
        return await self._with_retries(lambda: self._fetch_profile_once(account))

    async def _with_retries[T](self, call: Callable[[], Awaitable[T]]) -> T:
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await call()
            except Exception as exc:  # noqa: BLE001 — retried here, re-raised to the caller
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
        assert last_exc is not None
        raise last_exc

    async def _fetch_once(
        self, account: Account, since: datetime | None, limit: int | None
    ) -> list[RawContentItem]:
        run_input: dict[str, Any] = {
            "directUrls": [account.normalized_url],
            "resultsType": "posts",
            "resultsLimit": limit if limit is not None else _RESULTS_LIMIT,
        }
        # since=None means "last N publications" mode (item_limit) — no date cutoff, just the
        # most recent `limit` posts regardless of when they were published.
        if since is not None:
            run_input["onlyPostsNewerThan"] = since.date().isoformat()

        run = await self._client.actor(self._actor_id).call(
            run_input=run_input,
            run_timeout=timedelta(seconds=_RUN_TIMEOUT_SECS),
            max_total_charge_usd=self._max_charge_usd,
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
        # worker), never as a real content item. Also skip pinned posts: they appear at the top
        # of the profile regardless of date and can be months/years old.
        valid_items = [
            item for item in page.items if "error" not in item and not item.get("isPinned", False)
        ]
        error_items = [item for item in page.items if "error" in item]
        if error_items and not valid_items:
            reason = error_items[0].get("errorDescription") or error_items[0]["error"]
            raise ApifyRunFailedError(f"@{account.handle}: {reason}")

        return [_normalize(item) for item in valid_items]

    async def _fetch_profile_once(self, account: Account) -> ProfileInfo:
        run = await self._client.actor(self._actor_id).call(
            run_input={
                "directUrls": [account.normalized_url],
                "resultsType": "details",
            },
            run_timeout=timedelta(seconds=_RUN_TIMEOUT_SECS),
            max_total_charge_usd=self._max_charge_usd,
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
