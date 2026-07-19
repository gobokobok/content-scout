"""Integration tests for Telegram auth API endpoints (E8-S1, E8-S5).

These tests run against a real DB (via conftest fixtures) and mock the
TELEGRAM_BOT_TOKEN setting so no real bot credentials are needed in CI.
"""

import hashlib
import hmac
import json
import time
import urllib.parse
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

BOT_TOKEN = "123456789:test-bot-token-for-integration"


def _bot_secret() -> bytes:
    return hashlib.sha256(BOT_TOKEN.encode()).digest()


def _make_login_widget(telegram_id: int = 333) -> dict:
    auth_date = str(int(time.time()))
    data = {"id": str(telegram_id), "first_name": "Интег", "auth_date": auth_date}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    data["hash"] = hmac.new(_bot_secret(), check_string.encode(), hashlib.sha256).hexdigest()
    return {k: (int(v) if k == "id" else v) for k, v in data.items()}


def _make_init_data(telegram_id: int = 444) -> str:
    auth_date = str(int(time.time()))
    user_json = json.dumps({"id": telegram_id, "first_name": "Инит"})
    fields = {"auth_date": auth_date, "user": user_json}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urllib.parse.urlencode(fields)


@pytest.fixture()
def mock_tg_settings():
    """Patch settings so bot token is available without real env vars."""
    with patch("src.api.auth.get_settings") as m:
        from src.config import Settings

        s = Settings(
            telegram_bot_token=BOT_TOKEN,
            telegram_bot_username="test_bot",
            telegram_webhook_secret="",
        )
        m.return_value = s
        yield s


@pytest.mark.asyncio
async def test_telegram_config_enabled(mock_tg_settings, migrated_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/auth/telegram/config")
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is True
    assert body["bot_username"] == "test_bot"


@pytest.mark.asyncio
async def test_telegram_login_creates_user(mock_tg_settings, session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = _make_login_widget(telegram_id=55555)
        r = await client.post("/auth/telegram/login", json=payload)
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_telegram_login_idempotent(mock_tg_settings, session):
    """Second login with the same telegram_id returns a fresh JWT for the same user."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = _make_login_widget(telegram_id=66666)
        r1 = await client.post("/auth/telegram/login", json=payload)
        payload2 = _make_login_widget(telegram_id=66666)
        r2 = await client.post("/auth/telegram/login", json=payload2)
    assert r1.status_code == 200
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_telegram_login_bad_hash(mock_tg_settings, session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = _make_login_widget(telegram_id=77777)
        payload["hash"] = "badhash"
        r = await client.post("/auth/telegram/login", json=payload)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_telegram_webapp_login(mock_tg_settings, session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/auth/telegram/webapp", json={"init_data": _make_init_data(88888)})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_telegram_webapp_bad_hash(mock_tg_settings, session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post(
            "/auth/telegram/webapp",
            json={"init_data": "auth_date=12345&hash=badhash&user=%7B%22id%22%3A1%7D"},
        )
    assert r.status_code == 401
