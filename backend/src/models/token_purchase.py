import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class TokenPurchase(UuidPk, CreatedAt, Base):
    """One credited Telegram Stars top-up (E8-S3/D37). telegram_charge_id is unique so the
    webhook can dedupe a retried successful_payment update instead of double-crediting."""

    __tablename__ = "token_purchases"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    telegram_charge_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
