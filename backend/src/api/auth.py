import re
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependency import CurrentUser
from src.auth.providers import EmailTakenError, email_password_provider
from src.auth.tokens import create_access_token
from src.db import get_session

router = APIRouter(prefix="/auth", tags=["auth"])

# Deliberately simple (full RFC validation needs the email-validator dep; not worth it).
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LEN = 8

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


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: SessionDep) -> TokenOut:
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
async def login(body: CredentialsIn, session: SessionDep) -> TokenOut:
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
    return UserOut(id=user.id, email=user.email)
