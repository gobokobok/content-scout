"""Set token balance for a user by email.

Usage:
    python -m scripts.set_user_balance <email> <balance>

Example:
    railway run --environment production --service api \
        python3 -m scripts.set_user_balance alexdanm@gmail.com 1000000
"""

import asyncio
import sys

from sqlalchemy import select

from src.db import get_sessionmaker
from src.models import User


async def main(email: str, balance: int) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        user = await session.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            print(f"User not found: {email}")
            sys.exit(1)
        old = user.token_balance
        user.token_balance = balance
        await session.commit()
        print(f"Updated {email}: {old} → {balance}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m scripts.set_user_balance <email> <balance>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], int(sys.argv[2])))
