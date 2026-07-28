"""Telegram Stars token top-ups (E8-S3/D37) — one-time invoice, no subscription.

Pricing: 1 token = 1 rouble, converted to a Stars amount via `stars_per_token`
(placeholder pending a real FX check, D37 — Stars can't invoice in RUB directly).
"""

import logging
import math
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings, get_settings
from src.models import TokenPurchase, User

logger = logging.getLogger(__name__)

_CREATE_INVOICE_LINK_URL = "https://api.telegram.org/bot{token}/createInvoiceLink"


class InvoiceCreationError(Exception):
    """Raised when Telegram's createInvoiceLink call fails (bad request, network, etc.)."""


def stars_for_tokens(tokens: int, settings: Settings) -> int:
    return math.ceil(tokens * settings.stars_per_token)


async def create_stars_invoice(user_id: uuid.UUID, tokens: int) -> tuple[str, int]:
    """Return (invoice_url, amount_stars) for a one-time Stars top-up invoice."""
    settings = get_settings()
    amount_stars = stars_for_tokens(tokens, settings)
    url = _CREATE_INVOICE_LINK_URL.format(token=settings.telegram_bot_token)
    payload = {
        "title": "Пополнение баланса content-scout",
        "description": f"{tokens} токенов",
        "payload": f"topup:{user_id}:{tokens}",
        "provider_token": "",
        "currency": "XTR",
        "prices": [{"label": f"{tokens} токенов", "amount": amount_stars}],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        invoice_url = str(data["result"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("createInvoiceLink failed for user %s (%s tokens): %s", user_id, tokens, exc)
        raise InvoiceCreationError from exc

    return invoice_url, amount_stars


def parse_topup_payload(invoice_payload: str) -> tuple[uuid.UUID, int] | None:
    """Parse the `topup:<user_id>:<tokens>` payload set in create_stars_invoice. Returns None
    if the payload doesn't match (e.g. a payload from some other invoice type, future-proofing
    against this webhook one day handling more than one purchase kind)."""
    parts = invoice_payload.split(":")
    if len(parts) != 3 or parts[0] != "topup":
        return None
    try:
        return uuid.UUID(parts[1]), int(parts[2])
    except ValueError:
        return None


async def credit_purchase(
    session: AsyncSession,
    user_id: uuid.UUID,
    tokens: int,
    amount_stars: int,
    telegram_charge_id: str,
) -> bool:
    """Credit a successful Stars payment onto the user's token_balance, idempotently keyed on
    telegram_charge_id (Telegram may resend the same successful_payment update). Returns False
    (no-op) if this charge was already credited or the user no longer exists."""
    existing = await session.scalar(
        select(TokenPurchase).where(TokenPurchase.telegram_charge_id == telegram_charge_id)
    )
    if existing is not None:
        return False

    user = await session.get(User, user_id)
    if user is None:
        logger.warning(
            "Stars payment for unknown user_id %s (charge %s)", user_id, telegram_charge_id
        )
        return False

    session.add(
        TokenPurchase(
            user_id=user_id,
            tokens=tokens,
            amount_stars=amount_stars,
            telegram_charge_id=telegram_charge_id,
        )
    )
    user.token_balance += tokens
    await session.commit()
    return True
