from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.tokens import decode_access_token
from src.db import get_session
from src.models import User

_bearer = HTTPBearer(auto_error=False)

UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "unauthorized", "message_ru": "Требуется вход в систему."},
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if credentials is None:
        raise UNAUTHORIZED
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise UNAUTHORIZED
    user = await session.get(User, user_id)
    if user is None:
        raise UNAUTHORIZED
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
