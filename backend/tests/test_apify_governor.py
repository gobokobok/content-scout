"""E20-S3: global Apify concurrency governor."""

import asyncio
from unittest.mock import patch

import pytest

from src.services.apify_governor import acquire_apify_slot


class _FakeGovernorRedis:
    """In-memory stand-in for the sorted-set the real governor uses, mirroring exactly what the
    Lua script in apify_governor.py does — mocked rather than pointed at a real Redis, same
    pattern as test_guardrails.py's test_rate_limit_blocks_after_threshold."""

    def __init__(self) -> None:
        self._members: dict[str, float] = {}

    async def eval(self, _script, _numkeys, _key, limit, now, stale_before, member):  # noqa: ANN001
        limit = int(float(limit))
        now = float(now)
        stale_before = float(stale_before)
        for m, score in list(self._members.items()):
            if score < stale_before:
                del self._members[m]
        if len(self._members) < limit:
            self._members[member] = now
            return 1
        return 0

    async def zrem(self, _key, member) -> None:  # noqa: ANN001
        self._members.pop(member, None)


async def test_acquire_apify_slot_serializes_beyond_limit() -> None:
    fake_redis = _FakeGovernorRedis()
    order: list[str] = []

    async def _get_fake_pool():
        return fake_redis

    with (
        patch("src.services.apify_governor.get_redis_pool", _get_fake_pool),
        patch("src.services.apify_governor._POLL_INTERVAL_SECS", 0.01),
    ):
        async with acquire_apify_slot(limit=1):
            order.append("first-acquired")
            assert len(fake_redis._members) == 1

            async def _second():
                async with acquire_apify_slot(limit=1):
                    order.append("second-acquired")

            task = asyncio.create_task(_second())
            await asyncio.sleep(0.05)
            # Second acquirer must still be blocked while the first holds the only slot.
            assert "second-acquired" not in order

        await task

    assert order == ["first-acquired", "second-acquired"]
    assert fake_redis._members == {}


async def test_acquire_apify_slot_releases_slot_on_exception() -> None:
    fake_redis = _FakeGovernorRedis()

    async def _get_fake_pool():
        return fake_redis

    with patch("src.services.apify_governor.get_redis_pool", _get_fake_pool):
        with pytest.raises(RuntimeError):
            async with acquire_apify_slot(limit=1):
                assert len(fake_redis._members) == 1
                raise RuntimeError("boom")

    assert fake_redis._members == {}


async def test_acquire_apify_slot_allows_up_to_limit_concurrently() -> None:
    fake_redis = _FakeGovernorRedis()
    concurrent = 0
    max_concurrent = 0

    async def _get_fake_pool():
        return fake_redis

    async def _worker():
        nonlocal concurrent, max_concurrent
        async with acquire_apify_slot(limit=3):
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0.02)
            concurrent -= 1

    with (
        patch("src.services.apify_governor.get_redis_pool", _get_fake_pool),
        patch("src.services.apify_governor._POLL_INTERVAL_SECS", 0.01),
    ):
        await asyncio.gather(*(_worker() for _ in range(6)))

    assert max_concurrent == 3
    assert fake_redis._members == {}
