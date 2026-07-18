import re
from dataclasses import dataclass
from urllib.parse import urlparse

# IG usernames: letters, digits, periods, underscores, 1-30 chars, no leading/trailing period.
_HANDLE_RE = re.compile(r"^(?!\.)(?!.*\.\.)[A-Za-z0-9_.]{1,30}(?<!\.)$")

# First path segment of a non-profile IG URL (post/reel/story links etc.) — out of scope for MVP.
_RESERVED_SEGMENTS = {
    "p",
    "reel",
    "reels",
    "tv",
    "stories",
    "explore",
    "accounts",
    "direct",
    "about",
    "legal",
    "developer",
}


class InvalidAccountUrlError(Exception):
    def __init__(self, message_ru: str):
        self.message_ru = message_ru
        super().__init__(message_ru)


@dataclass(frozen=True)
class NormalizedAccount:
    handle: str
    normalized_url: str


def normalize_instagram_input(raw: str) -> NormalizedAccount:
    """Accepts a handle (with or without @) or an instagram.com profile URL."""
    value = raw.strip()
    if not value:
        raise InvalidAccountUrlError("Пустая строка.")

    handle: str
    if value.startswith("@"):
        handle = value[1:]
    elif "instagram.com" in value.lower() or "/" in value:
        handle = _extract_handle_from_url(value)
    else:
        handle = value

    handle = handle.strip().lower()
    if not _HANDLE_RE.match(handle):
        raise InvalidAccountUrlError(f'Некорректный адрес или имя пользователя: "{raw.strip()}".')
    if handle in _RESERVED_SEGMENTS:
        raise InvalidAccountUrlError(
            f'Похоже на ссылку не на профиль, а на публикацию: "{raw.strip()}".'
        )
    return NormalizedAccount(handle=handle, normalized_url=f"https://instagram.com/{handle}")


def _extract_handle_from_url(value: str) -> str:
    candidate = value if "://" in value else f"https://{value}"
    parsed = urlparse(candidate)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "instagram.com":
        raise InvalidAccountUrlError(f'Ссылка не на Instagram: "{value.strip()}".')
    segments = [s for s in parsed.path.split("/") if s]
    if not segments:
        raise InvalidAccountUrlError(f'Не удалось определить аккаунт: "{value.strip()}".')
    return segments[0]
