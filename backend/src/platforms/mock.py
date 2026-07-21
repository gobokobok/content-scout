from datetime import UTC, datetime, timedelta

from src.models import Account, ContentType
from src.platforms.base import ProfileInfo, RawContentItem

_TYPES = [ContentType.reel, ContentType.post, ContentType.carousel]
_ITEMS_PER_ACCOUNT = 3
_MOCK_FOLLOWERS = 12_400


class MockPlatform:
    """Fixture scraper for local/dev — no network calls. Registered for E3-S1's worker skeleton;
    InstagramPlatform (Apify-backed) replaces it for real accounts in E3-S2."""

    slug = "mock"

    async def fetch_content(self, account: Account, since: datetime) -> list[RawContentItem]:
        now = datetime.now(UTC)
        span = max(now - since, timedelta(seconds=_ITEMS_PER_ACCOUNT))
        step = span / (_ITEMS_PER_ACCOUNT + 1)

        items: list[RawContentItem] = []
        for i in range(_ITEMS_PER_ACCOUNT):
            content_type = _TYPES[i % len(_TYPES)]
            published_at = now - step * (i + 1)
            items.append(
                RawContentItem(
                    external_id=f"{account.handle}-mock-{i}",
                    type=content_type,
                    published_at=published_at,
                    url=f"https://instagram.com/{account.handle}/mock-{i}/",
                    title=f"Тестовая публикация {i + 1} от @{account.handle}",
                    caption=f"Пример подписи к публикации {i + 1}.",
                    likes=100 * (i + 1),
                    views=1000 * (i + 1) if content_type == ContentType.reel else None,
                    comments=5 * (i + 1),
                    raw={"mock": True, "index": i},
                )
            )
        return items

    async def fetch_profile(self, account: Account) -> ProfileInfo:
        return ProfileInfo(
            followers_count=_MOCK_FOLLOWERS,
            display_name=f"Тестовый аккаунт @{account.handle}",
            avatar_url=None,
        )
