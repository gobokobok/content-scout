from src.models import PlatformSlug
from src.platforms.base import Platform, RawContentItem
from src.platforms.mock import MockPlatform

# Only the mock platform exists until E3-S2 ships InstagramPlatform (Apify-backed).
_PLATFORMS: dict[PlatformSlug, Platform] = {PlatformSlug.instagram: MockPlatform()}


def get_platform(slug: PlatformSlug) -> Platform:
    return _PLATFORMS[slug]


__all__ = ["Platform", "RawContentItem", "get_platform"]
