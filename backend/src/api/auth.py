import json
import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.auth.providers import EmailTakenError, email_password_provider
from src.auth.telegram import (
    find_or_create_telegram_user,
    verify_login_widget,
    verify_webapp_init_data,
)
from src.auth.tokens import create_access_token
from src.config import get_settings
from src.db import get_session
from src.middleware.rate_limit import check_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])

# Deliberately simple (full RFC validation needs the email-validator dep; not worth it).
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LEN = 8
MAX_DISPLAY_NAME_LEN = 50

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class CredentialsIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_shape(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError("Введите корректный адрес почты.")
        return v.lower()


class RegisterIn(CredentialsIn):
    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LEN:
            raise ValueError(f"Пароль должен быть не короче {MIN_PASSWORD_LEN} символов.")
        return v


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_admin: bool
    has_telegram: bool = False
    token_balance: int = 0


class DisplayNameIn(BaseModel):
    display_name: str

    @field_validator("display_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Имя не может быть пустым.")
        if len(v) > MAX_DISPLAY_NAME_LEN:
            raise ValueError(f"Имя должно быть не длиннее {MAX_DISPLAY_NAME_LEN} символов.")
        return v


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, request: Request, session: SessionDep) -> TokenOut:
    await check_rate_limit(request)

    try:
        user = await email_password_provider.register(
            session, email=body.email, password=body.password
        )
    except EmailTakenError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "email_taken",
                "message_ru": "Эта почта уже зарегистрирована. Попробуйте войти.",
            },
        ) from None
    await session.commit()
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
async def login(body: CredentialsIn, request: Request, session: SessionDep) -> TokenOut:
    await check_rate_limit(request)

    user = await email_password_provider.authenticate(
        session, email=body.email, password=body.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message_ru": "Неверная почта или пароль."},
        )
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        has_telegram=user.telegram_id is not None,
        token_balance=user.token_balance,
    )


@router.patch("/me", response_model=UserOut)
async def update_me(body: DisplayNameIn, user: CurrentUser, session: SessionDep) -> UserOut:
    user.display_name = body.display_name
    await session.commit()
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        has_telegram=user.telegram_id is not None,
        token_balance=user.token_balance,
    )


# ── Telegram Login Widget (E8-S1) ────────────────────────────────────────────


class TelegramLoginIn(BaseModel):
    """Raw fields forwarded from the Telegram Login Widget callback."""

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int  # widget sends Unix timestamp as integer
    hash: str


class TelegramConfigOut(BaseModel):
    enabled: bool
    bot_username: str


@router.get("/telegram/config", response_model=TelegramConfigOut)
async def telegram_config() -> TelegramConfigOut:
    settings = get_settings()
    return TelegramConfigOut(
        enabled=bool(settings.telegram_bot_token and settings.telegram_bot_username),
        bot_username=settings.telegram_bot_username,
    )


@router.post("/telegram/login", response_model=TokenOut)
async def telegram_login(body: TelegramLoginIn, session: SessionDep) -> TokenOut:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "telegram_not_configured",
                "message_ru": "Вход через Telegram недоступен.",
            },
        )
    data = body.model_dump(exclude_none=True)
    data = {k: str(v) for k, v in data.items()}
    if not verify_login_widget(data, settings.telegram_bot_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "telegram_invalid", "message_ru": "Неверная подпись Telegram."},
        )
    user = await find_or_create_telegram_user(session, body.id)
    await session.commit()
    return TokenOut(access_token=create_access_token(user.id))


# ── Telegram Mini App initData (E8-S5) ───────────────────────────────────────


class TelegramWebAppIn(BaseModel):
    init_data: str


@router.post("/telegram/webapp", response_model=TokenOut)
async def telegram_webapp(body: TelegramWebAppIn, session: SessionDep) -> TokenOut:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "telegram_not_configured",
                "message_ru": "Вход через Telegram недоступен.",
            },
        )
    valid, parsed = verify_webapp_init_data(body.init_data, settings.telegram_bot_token)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "telegram_invalid", "message_ru": "Неверная подпись Telegram."},
        )
    user_json = parsed.get("user", "{}")
    try:
        tg_user = json.loads(user_json)
        telegram_id = int(tg_user["id"])
    except (KeyError, ValueError, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "telegram_no_user",
                "message_ru": "Не удалось получить данные пользователя Telegram.",
            },
        )
    user = await find_or_create_telegram_user(session, telegram_id)
    await session.commit()
    return TokenOut(access_token=create_access_token(user.id))


# ── Link Telegram to existing email account (settings page, UI in E8-S2) ────


@router.post("/telegram/link", response_model=UserOut)
async def telegram_link(body: TelegramLoginIn, user: CurrentUser, session: SessionDep) -> UserOut:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "telegram_not_configured",
                "message_ru": "Вход через Telegram недоступен.",
            },
        )
    data = {k: str(v) for k, v in body.model_dump(exclude_none=True).items()}
    if not verify_login_widget(data, settings.telegram_bot_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "telegram_invalid", "message_ru": "Неверная подпись Telegram."},
        )
    user.telegram_id = body.id
    await session.commit()
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        has_telegram=user.telegram_id is not None,
        token_balance=user.token_balance,
    )
