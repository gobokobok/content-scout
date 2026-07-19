"""Telegram auth provider — Login Widget (E8-S1) and Mini App initData (E8-S5).

Login Widget:  secret = SHA-256(bot_token); hash = HMAC-SHA256(sorted_data, secret)
Mini App:      secret = HMAC-SHA256("WebAppData", bot_token);
               hash = HMAC-SHA256(sorted_data, secret)
"""

import hashlib
import hmac
import time
import urllib.parse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.providers import create_user_with_workspace
from src.models import User

MAX_AUTH_AGE_SECONDS = 86400  # 24 h


def verify_login_widget(data: dict[str, str], bot_token: str) -> bool:
    """Return True iff the Telegram Login Widget hash is valid and fresh."""
    received_hash = data.get("hash", "")
    auth_date = data.get("auth_date", "0")
    if int(auth_date) < time.time() - MAX_AUTH_AGE_SECONDS:
        return False
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()) if k != "hash")
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_hash)


def verify_webapp_init_data(init_data: str, bot_token: str) -> tuple[bool, dict]:
    """Return (is_valid, parsed_fields) for Telegram Web App initData."""
    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", "")
    auth_date = parsed.get("auth_date", "0")
    if int(auth_date) < time.time() - MAX_AUTH_AGE_SECONDS:
        return False, {}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_hash), parsed


async def find_or_create_telegram_user(session: AsyncSession, telegram_id: int) -> User:
    """Return the user linked to this telegram_id, creating one if needed."""
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is not None:
        return user
    placeholder_email = f"tg_{telegram_id}@telegram.local"
    user = await create_user_with_workspace(session, email=placeholder_email, password_hash=None)
    user.telegram_id = telegram_id
    await session.flush()
    return user
