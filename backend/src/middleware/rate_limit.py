import time

from fastapi import HTTPException, Request, status

from src.services.queue import get_redis_pool

_WINDOW_SECS = 60
_DEFAULT_LIMIT = 10


async def check_rate_limit(
    request: Request, limit: int = _DEFAULT_LIMIT, key: str | None = None
) -> None:
    """Raise 429 if the caller has exceeded `limit` requests to this path in the current minute
    window. Buckets by `key` when given (e.g. a user id, for authenticated write endpoints where
    per-user identity is a better fit than IP — shared/mobile NATs put many users behind one
    IP); falls back to the caller's IP for anonymous endpoints like login/register."""
    identity = key or (request.client.host if request.client else "unknown")
    bucket = int(time.time()) // _WINDOW_SECS
    rl_key = f"rl:{request.url.path}:{identity}:{bucket}"

    redis = await get_redis_pool()
    count = await redis.incr(rl_key)
    if count == 1:
        await redis.expire(rl_key, _WINDOW_SECS + 5)

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message_ru": "Слишком много попыток. Повторите через минуту.",
            },
        )
