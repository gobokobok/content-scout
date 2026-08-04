from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from src.models import Account, ContentType


@dataclass
class RawContentItem:
    external_id: str
    type: ContentType
    published_at: datetime
    url: str
    title: str | None = None
    cover_url: str | None = None
    caption: str | None = None
    likes: int | None = None
    views: int | None = None
    comments: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileInfo:
    followers_count: int | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class Platform(Protocol):
    slug: str

    async def fetch_content(
        self, account: Account, *, since: datetime | None, limit: int | None = None
    ) -> list[RawContentItem]:
        """since=None means no date cutoff — fetch the most recent `limit` posts instead of a
        day window. Exactly one of since/limit is meaningfully set by the caller (mirrors
        AnalysisRun.duration_days / item_limit), but both are accepted so a platform can apply
        whichever combination makes sense for it."""
        ...

    async def fetch_profile(self, account: Account) -> ProfileInfo: ...

    async def fetch_post(self, post_url: str) -> RawContentItem:
        """Standalone Analysis post mode (D49/D50) — fetches exactly one publication by URL,
        no account/profile context needed. `RawContentItem.raw` carries the vendor's owner
        username field so the caller can resolve/create the post's author as a real Account."""
        ...
