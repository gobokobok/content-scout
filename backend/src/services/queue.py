import asyncio
import uuid

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from src.config import get_settings

_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


async def get_redis_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
    return _pool


async def enqueue_run(run_id: uuid.UUID) -> None:
    pool = await get_redis_pool()
    await pool.enqueue_job("run_analysis", str(run_id))


async def enqueue_profile_fetch(account_id: uuid.UUID, user_id: uuid.UUID) -> None:
    pool = await get_redis_pool()
    await pool.enqueue_job("fetch_account_profile", str(account_id), str(user_id))
