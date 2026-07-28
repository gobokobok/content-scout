"""Telegram Bot webhook and setup — E8-S5 (D27: raw httpx, no bot framework)."""

import hmac
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.db import get_session
from src.services.billing import credit_purchase, parse_topup_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])

BOT_API = "https://api.telegram.org/bot{token}/{method}"

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _bot_call(method: str, **payload) -> dict:
    settings = get_settings()
    url = BOT_API.format(token=settings.telegram_bot_token, method=method)
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


@router.post("/webhook")
async def telegram_webhook(
    update: dict,
    session: SessionDep,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    if not settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    if not hmac.compare_digest(
        x_telegram_bot_api_secret_token or "", settings.telegram_webhook_secret
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    if "pre_checkout_query" in update:
        await _answer_pre_checkout(update["pre_checkout_query"])
        return {"ok": True}

    message = update.get("message", {})

    if "successful_payment" in message:
        await _handle_successful_payment(session, message["successful_payment"])
        return {"ok": True}

    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if chat_id and text.startswith("/start"):
        await _send_open_button(chat_id)

    return {"ok": True}


async def _answer_pre_checkout(pre_checkout_query: dict) -> None:
    """Telegram requires an answer within 10s or the payment sheet shows an error. We always
    accept — the only validation (minimum amount) already happened when the invoice was
    created (billing.create_stars_invoice), so there's nothing left to reject here."""
    try:
        await _bot_call(
            "answerPreCheckoutQuery",
            pre_checkout_query_id=pre_checkout_query["id"],
            ok=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("answerPreCheckoutQuery failed: %s", exc)


async def _handle_successful_payment(session: AsyncSession, successful_payment: dict) -> None:
    parsed = parse_topup_payload(successful_payment.get("invoice_payload", ""))
    if parsed is None:
        logger.warning("successful_payment with unrecognized payload: %s", successful_payment)
        return
    user_id, tokens = parsed
    credited = await credit_purchase(
        session,
        user_id=user_id,
        tokens=tokens,
        amount_stars=successful_payment.get("total_amount", 0),
        telegram_charge_id=successful_payment["telegram_payment_charge_id"],
    )
    if not credited:
        logger.info(
            "Stars payment for user %s (charge %s) already credited or user missing — skipped",
            user_id,
            successful_payment.get("telegram_payment_charge_id"),
        )


async def _send_open_button(chat_id: int) -> None:
    settings = get_settings()
    await _bot_call(
        "sendMessage",
        chat_id=chat_id,
        text="Привет! Открывай content-scout прямо здесь — без лишних кликов.",
        reply_markup={
            "inline_keyboard": [
                [
                    {
                        "text": "Открыть content-scout",
                        "web_app": {"url": settings.web_url},
                    }
                ]
            ]
        },
    )


async def setup_webhook_and_menu() -> None:
    """Idempotent: register webhook + set chat menu button. Called at startup."""
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_webhook_secret:
        logger.info("Telegram bot not configured — skipping webhook setup")
        return

    api_webhook_url = f"{_get_api_base_url()}/telegram/webhook"

    try:
        await _bot_call(
            "setWebhook",
            url=api_webhook_url,
            secret_token=settings.telegram_webhook_secret,
            # pre_checkout_query/successful_payment (E8-S3) are separate update types from
            # "message" — Telegram won't deliver them unless explicitly listed here.
            allowed_updates=["message", "pre_checkout_query"],
        )
        await _bot_call(
            "setChatMenuButton",
            menu_button={
                "type": "web_app",
                "text": "Открыть",
                "web_app": {"url": settings.web_url},
            },
        )
        logger.info("Telegram webhook registered: %s", api_webhook_url)
    except Exception as exc:
        logger.warning("Telegram webhook setup failed (non-fatal): %s", exc)


def _get_api_base_url() -> str:
    """Return the public base URL of this API service."""
    import os

    # RAILWAY_PUBLIC_DOMAIN is set automatically on Railway services
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if domain:
        return f"https://{domain}"
    # Local fallback — won't work for Telegram (needs public HTTPS) but avoids a crash
    return "http://localhost:8000"
