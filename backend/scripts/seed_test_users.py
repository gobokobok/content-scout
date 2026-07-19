"""
Create 5 beta test users each with 100 tokens.

Usage (from backend/):
    python -m scripts.seed_test_users

Requires DATABASE_URL env var (same as the app).
Existing accounts with these emails are updated in place (balance reset to 100).
"""

import asyncio
import os
import sys

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models import User  # noqa: E402
from src.models.base import Base  # noqa: E402

DATABASE_URL = os.environ["DATABASE_URL"]

TEST_USERS = [
    ("beta1@content-scout.app", "Scout2026!"),
    ("beta2@content-scout.app", "Scout2026!"),
    ("beta3@content-scout.app", "Scout2026!"),
    ("beta4@content-scout.app", "Scout2026!"),
    ("beta5@content-scout.app", "Scout2026!"),
]
INITIAL_BALANCE = 100

_pwd = CryptContext(schemes=["bcrypt"])


async def main() -> None:
    engine = create_async_engine(DATABASE_URL)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with sessionmaker() as session:
        for email, password in TEST_USERS:
            existing = await session.scalar(select(User).where(User.email == email))
            if existing:
                existing.token_balance = INITIAL_BALANCE
                existing.password_hash = _pwd.hash(password)
                print(f"  updated  {email}")
            else:
                user = User(
                    email=email,
                    password_hash=_pwd.hash(password),
                    token_balance=INITIAL_BALANCE,
                )
                session.add(user)
                print(f"  created  {email}")
        await session.commit()

    await engine.dispose()

    print("\nTest accounts:")
    for email, password in TEST_USERS:
        print(f"  {email}  /  {password}  (balance: {INITIAL_BALANCE})")


if __name__ == "__main__":
    asyncio.run(main())
