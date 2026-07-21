import uuid
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import KIND_APIFY_RESULT, UsageEvent
from src.platforms.base import ProfileInfo
from src.worker import fetch_account_profile
from tests.conftest import make_account, make_account_list, make_user


async def test_fetch_account_profile_updates_account(session: AsyncSession) -> None:
    user = await make_user(session)
    account_list = await make_account_list(session)
    account = await make_account(session, account_list=account_list)
    await session.commit()

    class _FakePlatform:
        slug = "mock"

        async def fetch_profile(self, account):
            return ProfileInfo(
                followers_count=54_321, display_name="Тестовый блогер", avatar_url="https://x/a.jpg"
            )

    with patch("src.worker.get_platform", return_value=_FakePlatform()):
        await fetch_account_profile({}, str(account.id), str(user.id))

    await session.refresh(account)
    assert account.followers_count == 54_321
    assert account.display_name == "Тестовый блогер"
    assert account.avatar_url == "https://x/a.jpg"
    assert account.followers_updated_at is not None

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.user_id == user.id))).all()
    apify_events = [u for u in usage if u.kind == KIND_APIFY_RESULT]
    assert len(apify_events) == 1
    assert apify_events[0].quantity == 1
    assert apify_events[0].run_id is None


async def test_fetch_account_profile_failure_leaves_account_usable(session: AsyncSession) -> None:
    user = await make_user(session)
    account_list = await make_account_list(session)
    account = await make_account(session, account_list=account_list)
    await session.commit()

    class _FailingPlatform:
        slug = "mock"

        async def fetch_profile(self, account):
            raise RuntimeError("apify boom")

    with patch("src.worker.get_platform", return_value=_FailingPlatform()):
        await fetch_account_profile({}, str(account.id), str(user.id))

    await session.refresh(account)
    assert account.followers_count is None
    assert account.display_name is None
    assert account.followers_updated_at is None

    usage = (await session.scalars(select(UsageEvent).where(UsageEvent.user_id == user.id))).all()
    assert usage == []


async def test_fetch_account_profile_missing_account_is_noop(session: AsyncSession) -> None:
    user = await make_user(session)
    await session.commit()

    await fetch_account_profile({}, str(uuid.uuid4()), str(user.id))
    # No exception, nothing to assert beyond "did not raise" — the account simply doesn't exist.
