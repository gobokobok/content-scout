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

    async def fetch_content(self, account: Account, since: datetime) -> list[RawContentItem]: ...

    async def fetch_profile(self, account: Account) -> ProfileInfo: ...
