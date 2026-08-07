from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class User(UuidPk, CreatedAt, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    token_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # E22-S3: global per-user notification preferences, replacing the per-run/per-schedule
    # notify_on_complete/notify_enabled fields (E14-S6/E22-S2) — explicit user decision, no
    # per-run override. Default True preserves pre-existing unconditional-notify behavior.
    notify_review_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_analysis_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
