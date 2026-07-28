from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.auth.dependency import CurrentUser
from src.config import get_settings
from src.services.billing import InvoiceCreationError, create_stars_invoice

router = APIRouter(prefix="/billing", tags=["billing"])

NOT_IN_TELEGRAM = HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail={
        "code": "telegram_not_linked",
        "message_ru": (
            "Пополнение доступно только внутри Telegram — откройте приложение через бота."
        ),
    },
)
INVOICE_FAILED = HTTPException(
    status_code=status.HTTP_502_BAD_GATEWAY,
    detail={
        "code": "invoice_creation_failed",
        "message_ru": "Не удалось создать счёт для оплаты. Попробуйте ещё раз позже.",
    },
)


class PurchaseInvoiceIn(BaseModel):
    tokens: int = Field(ge=1)


class PurchaseInvoiceOut(BaseModel):
    invoice_url: str
    tokens: int
    amount_stars: int


@router.post("/purchase-invoice", response_model=PurchaseInvoiceOut)
async def create_purchase_invoice(body: PurchaseInvoiceIn, user: CurrentUser) -> PurchaseInvoiceOut:
    settings = get_settings()
    if user.telegram_id is None:
        raise NOT_IN_TELEGRAM
    if body.tokens < settings.min_token_purchase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "purchase_below_minimum",
                "message_ru": (
                    f"Минимальная сумма пополнения — {settings.min_token_purchase} токенов."
                ),
            },
        )

    try:
        invoice_url, amount_stars = await create_stars_invoice(user.id, body.tokens)
    except InvoiceCreationError:
        raise INVOICE_FAILED from None

    return PurchaseInvoiceOut(
        invoice_url=invoice_url, tokens=body.tokens, amount_stars=amount_stars
    )
