import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from apify_client import ApifyClientAsync

from src.config import get_settings
from src.models import Account, ContentType
from src.platforms.base import RawContentItem


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

    async def fetch_content(self, account: Account, since: datetime) -> list[RawContentItem]:
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return await self._fetch_once(account, since)
            except Exception as exc:  # noqa: BLE001 — retried here, re-raised to the caller
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2**attempt)
        assert last_exc is not None
        raise last_exc

    async def _fetch_once(self, account: Account, since: datetime) -> list[RawContentItem]:
        run = await self._client.actor(self._actor_id).call(
            run_input={
                "directUrls": [account.normalized_url],
                "resultsType": "posts",
                "resultsLimit": _RESULTS_LIMIT,
                "onlyPostsNewerThan": since.date().isoformat(),
            },
            run_timeout=timedelta(seconds=_RUN_TIMEOUT_SECS),
        )
        if run is None:
            raise ApifyRunFailedError(f"Apify actor run for @{account.handle} returned no run")
        page = await self._client.dataset(run.default_dataset_id).list_items()
        return [_normalize(item) for item in page.items]


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
