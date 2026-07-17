from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, CreatedAt, UuidPk


class User(UuidPk, CreatedAt, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(200))
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
