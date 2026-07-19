"""Unit tests for Telegram Login Widget verification (E8-S1)."""

import hashlib
import hmac
import time
import urllib.parse

from src.auth.telegram import verify_login_widget, verify_webapp_init_data

BOT_TOKEN = "123456789:test-bot-token-for-unit-tests"


def _make_login_widget_data(telegram_id: int = 111, offset_secs: int = 0) -> dict[str, str]:
    """Build a correctly-signed Login Widget payload."""
    auth_date = str(int(time.time()) + offset_secs)
    data = {
        "id": str(telegram_id),
        "first_name": "Тест",
        "auth_date": auth_date,
    }
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    data["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return data


def _make_init_data(telegram_id: int = 222, offset_secs: int = 0) -> str:
    """Build a correctly-signed Mini App initData string."""
    auth_date = str(int(time.time()) + offset_secs)
    user_json = f'{{"id":{telegram_id},"first_name":"Тест"}}'
    fields = {"auth_date": auth_date, "user": user_json}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    fields["hash"] = h
    return urllib.parse.urlencode(fields)


# ── Login Widget ─────────────────────────────────────────────────────────────


def test_login_widget_valid():
    data = _make_login_widget_data()
    assert verify_login_widget(data, BOT_TOKEN) is True


def test_login_widget_tampered_hash():
    data = _make_login_widget_data()
    data["hash"] = "deadbeef" * 8
    assert verify_login_widget(data, BOT_TOKEN) is False


def test_login_widget_wrong_token():
    data = _make_login_widget_data()
    assert verify_login_widget(data, "wrong-token") is False


def test_login_widget_expired():
    data = _make_login_widget_data(offset_secs=-(86400 + 1))
    assert verify_login_widget(data, BOT_TOKEN) is False


# ── Mini App initData ─────────────────────────────────────────────────────────


def test_webapp_init_data_valid():
    init_data = _make_init_data()
    ok, parsed = verify_webapp_init_data(init_data, BOT_TOKEN)
    assert ok is True
    assert "user" in parsed


def test_webapp_init_data_tampered():
    init_data = _make_init_data() + "&hash=deadbeef"
    ok, _ = verify_webapp_init_data(init_data, BOT_TOKEN)
    assert ok is False


def test_webapp_init_data_wrong_token():
    init_data = _make_init_data()
    ok, _ = verify_webapp_init_data(init_data, "wrong-token")
    assert ok is False


def test_webapp_init_data_expired():
    init_data = _make_init_data(offset_secs=-(86400 + 1))
    ok, _ = verify_webapp_init_data(init_data, BOT_TOKEN)
    assert ok is False
