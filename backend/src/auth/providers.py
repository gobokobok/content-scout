import random
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.passwords import dummy_verify, hash_password, verify_password
from src.models import Project, User, Workspace, WorkspaceKind, WorkspaceMember


class EmailTakenError(Exception):
    pass


class AuthProvider(Protocol):
    """Future providers (Telegram D18, VK ID D4) implement this without touching call sites."""

    slug: str

    async def authenticate(self, session: AsyncSession, /, **credentials: str) -> User | None: ...


def _random_display_name() -> str:
    """Placeholder shown until the user picks their own name in Settings."""
    return f"Пользователь{random.randint(1000, 9999)}"


async def create_user_with_workspace(
    session: AsyncSession, *, email: str, password_hash: str | None
) -> User:
    """User + personal workspace + owner membership + default project, one transaction (D6,
    D38). "Project" isn't a user-facing concept (D38) — every user gets exactly one, invisibly,
    so nothing ever needs to prompt them to create one."""
    user = User(
        email=email.lower(),
        password_hash=password_hash,
        display_name=_random_display_name(),
        token_balance=50,
    )
    session.add(user)
    await session.flush()
    workspace = Workspace(name="Личное пространство", kind=WorkspaceKind.personal)
    session.add(workspace)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id))
    session.add(Project(workspace_id=workspace.id, name="Мой блог"))
    await session.flush()
    return user


class EmailPasswordProvider:
    slug = "email"

    async def register(self, session: AsyncSession, *, email: str, password: str) -> User:
        existing = await session.scalar(select(User).where(User.email == email.lower()))
        if existing is not None:
            raise EmailTakenError(email)
        return await create_user_with_workspace(
            session, email=email, password_hash=hash_password(password)
        )

    async def authenticate(self, session: AsyncSession, /, **credentials: str) -> User | None:
        email, password = credentials["email"], credentials["password"]
        user = await session.scalar(select(User).where(User.email == email.lower()))
        if user is None or user.password_hash is None:
            dummy_verify()  # Constant-time path to prevent user-enumeration via response time
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


email_password_provider = EmailPasswordProvider()
