import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from src.services.queue import get_redis_pool

_GOVERNOR_KEY = "apify:concurrency:slots"
_POLL_INTERVAL_SECS = 0.5
# A worker that dies mid-call (OOM kill, hard restart) never reaches the `finally` release
# below, leaving a phantom slot occupied forever. Stale entries are pruned on every acquire
# attempt using the worker's own job_timeout as the staleness bound, plus margin.
_STALE_AFTER_SECS = 3600 + 300

# Atomic check-and-add: without the Lua script, a "ZCARD then ZADD" done as two round-trips
# would let concurrent acquirers all pass the check before any of them adds, overshooting the
# limit under real contention.
_ACQUIRE_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local stale_before = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, '-inf', stale_before)
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, member)
    return 1
end
return 0
"""


@asynccontextmanager
async def acquire_apify_slot(limit: int) -> AsyncIterator[None]:
    """Global, Redis-backed semaphore bounding simultaneous Apify actor calls at `limit`
    (D44's confirmed 25-concurrent-Actor-run ceiling) across every worker process — not just
    within one, which is all arq's own max_jobs/scrape_concurrency can see. Wrap the actual
    `ActorClientAsync...call()` invocation, not the whole fetch/retry loop, so each retry
    attempt acquires its own slot rather than holding one across sleep-and-retry."""
    redis = await get_redis_pool()
    member = str(uuid.uuid4())
    while True:
        now = time.time()
        acquired = await redis.eval(  # type: ignore[misc]
            _ACQUIRE_SCRIPT,
            1,
            _GOVERNOR_KEY,
            str(limit),
            str(now),
            str(now - _STALE_AFTER_SECS),
            member,
        )
        if acquired:
            break
        await asyncio.sleep(_POLL_INTERVAL_SECS)
    try:
        yield
    finally:
        await redis.zrem(_GOVERNOR_KEY, member)
