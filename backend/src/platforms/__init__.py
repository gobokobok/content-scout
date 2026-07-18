from src.config import get_settings
from src.models import PlatformSlug
from src.platforms.base import Platform, RawContentItem
from src.platforms.mock import MockPlatform


def get_platform(slug: PlatformSlug) -> Platform:
    """Instagram is the only implemented platform; mock vs. real is USE_MOCK_PLATFORM (never
    mock in PROD). YouTube/TikTok/Threads enum values exist but have no implementation yet."""
    if slug is not PlatformSlug.instagram:
        raise NotImplementedError(f"no Platform implementation for {slug}")

    if get_settings().use_mock_platform:
        return MockPlatform()

    from src.platforms.instagram import InstagramPlatform  # Apify import stays out of the mock path

    return InstagramPlatform()


__all__ = ["Platform", "RawContentItem", "get_platform"]
