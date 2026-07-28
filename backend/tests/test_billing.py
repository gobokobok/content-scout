"""Tests for E8-S3/D37 Telegram Stars token top-ups."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.telegram_webhook import _handle_successful_payment
from src.auth.tokens import create_access_token
from src.db import get_session
from src.main import app
from src.models import TokenPurchase, User
from src.services.billing import (
    InvoiceCreationError,
    create_stars_invoice,
    credit_purchase,
    parse_topup_payload,
    stars_for_tokens,
)
from tests.conftest import make_user


class _TestClient(AsyncClient):
    async def __aexit__(self, *exc_info: object) -> None:
        app.dependency_overrides.pop(get_session, None)
        await super().__aexit__(*exc_info)


async def client(session: AsyncSession) -> _TestClient:
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    return _TestClient(transport=transport, base_url="http://test")


def auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


# --- services/billing.py -----------------------------------------------------


def test_stars_for_tokens_default_conversion():
    settings = MagicMock(stars_per_token=1.0)
    assert stars_for_tokens(1000, settings) == 1000


def test_parse_topup_payload_valid():
    user_id = uuid.uuid4()
    parsed = parse_topup_payload(f"topup:{user_id}:1500")
    assert parsed == (user_id, 1500)


@pytest.mark.parametrize(
    "payload",
    ["not-a-payload", "topup:not-a-uuid:1500", f"topup:{uuid.uuid4()}:not-an-int", "topup:1:2:3"],
)
def test_parse_topup_payload_invalid(payload: str):
    assert parse_topup_payload(payload) is None


async def test_create_stars_invoice_returns_url_and_amount():
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": "https://t.me/invoice/abc"}
    mock_http.post = AsyncMock(return_value=mock_response)

    with patch("src.services.billing.httpx.AsyncClient", return_value=mock_http):
        invoice_url, amount_stars = await create_stars_invoice(uuid.uuid4(), 1000)

    assert invoice_url == "https://t.me/invoice/abc"
    assert amount_stars == 1000


async def test_create_stars_invoice_raises_on_failure():
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.post = AsyncMock(side_effect=RuntimeError("network error"))

    with (
        patch("src.services.billing.httpx.AsyncClient", return_value=mock_http),
        pytest.raises(InvoiceCreationError),
    ):
        await create_stars_invoice(uuid.uuid4(), 1000)


async def test_credit_purchase_credits_balance_once(session: AsyncSession):
    user = await make_user(session, token_balance=100)
    await session.commit()

    credited = await credit_purchase(
        session, user_id=user.id, tokens=1000, amount_stars=1000, telegram_charge_id="charge-1"
    )
    assert credited is True

    refreshed = await session.get(User, user.id)
    assert refreshed.token_balance == 1100
    purchases = (
        (await session.execute(select(TokenPurchase).where(TokenPurchase.user_id == user.id)))
        .scalars()
        .all()
    )
    assert len(purchases) == 1
    assert purchases[0].telegram_charge_id == "charge-1"


async def test_credit_purchase_is_idempotent_on_duplicate_charge_id(session: AsyncSession):
    user = await make_user(session, token_balance=100)
    await session.commit()

    first = await credit_purchase(
        session, user_id=user.id, tokens=1000, amount_stars=1000, telegram_charge_id="charge-1"
    )
    second = await credit_purchase(
        session, user_id=user.id, tokens=1000, amount_stars=1000, telegram_charge_id="charge-1"
    )
    assert first is True
    assert second is False

    refreshed = await session.get(User, user.id)
    assert refreshed.token_balance == 1100  # not double-credited


async def test_credit_purchase_noop_for_unknown_user(session: AsyncSession):
    credited = await credit_purchase(
        session,
        user_id=uuid.uuid4(),
        tokens=1000,
        amount_stars=1000,
        telegram_charge_id="charge-unknown",
    )
    assert credited is False


# --- webhook handler ----------------------------------------------------------


async def test_handle_successful_payment_credits_tokens(session: AsyncSession):
    user = await make_user(session, token_balance=0)
    await session.commit()

    await _handle_successful_payment(
        session,
        {
            "invoice_payload": f"topup:{user.id}:2000",
            "telegram_payment_charge_id": "tg-charge-1",
            "total_amount": 2000,
        },
    )

    refreshed = await session.get(User, user.id)
    assert refreshed.token_balance == 2000


async def test_handle_successful_payment_ignores_unrecognized_payload(session: AsyncSession):
    # Should not raise even though the payload doesn't parse.
    await _handle_successful_payment(
        session,
        {
            "invoice_payload": "garbage",
            "telegram_payment_charge_id": "tg-charge-2",
            "total_amount": 2000,
        },
    )


# --- POST /billing/purchase-invoice ------------------------------------------


async def test_purchase_invoice_requires_telegram_linked(session: AsyncSession):
    user = await make_user(session, telegram_id=None)
    await session.commit()

    async with await client(session) as c:
        r = await c.post(
            "/billing/purchase-invoice", json={"tokens": 1000}, headers=auth_headers(user.id)
        )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "telegram_not_linked"


async def test_purchase_invoice_rejects_below_minimum(session: AsyncSession):
    user = await make_user(session, telegram_id=123456)
    await session.commit()

    async with await client(session) as c:
        r = await c.post(
            "/billing/purchase-invoice", json={"tokens": 50}, headers=auth_headers(user.id)
        )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "purchase_below_minimum"


async def test_purchase_invoice_success(session: AsyncSession):
    user = await make_user(session, telegram_id=123456)
    await session.commit()

    with patch(
        "src.api.billing.create_stars_invoice",
        AsyncMock(return_value=("https://t.me/invoice/xyz", 1000)),
    ):
        async with await client(session) as c:
            r = await c.post(
                "/billing/purchase-invoice", json={"tokens": 1000}, headers=auth_headers(user.id)
            )
    assert r.status_code == 200
    body = r.json()
    assert body["invoice_url"] == "https://t.me/invoice/xyz"
    assert body["tokens"] == 1000
    assert body["amount_stars"] == 1000


async def test_purchase_invoice_surfaces_creation_failure(session: AsyncSession):
    user = await make_user(session, telegram_id=123456)
    await session.commit()

    with patch(
        "src.api.billing.create_stars_invoice", AsyncMock(side_effect=InvoiceCreationError())
    ):
        async with await client(session) as c:
            r = await c.post(
                "/billing/purchase-invoice", json={"tokens": 1000}, headers=auth_headers(user.id)
            )
    assert r.status_code == 502
    assert r.json()["detail"]["code"] == "invoice_creation_failed"
