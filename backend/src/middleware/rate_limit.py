import time

from fastapi import HTTPException, Request, status

from src.services.queue import get_redis_pool

_WINDOW_SECS = 60
_DEFAULT_LIMIT = 10


async def check_rate_limit(request: Request, limit: int = _DEFAULT_LIMIT) -> None:
    """Raise 429 if the caller IP has exceeded `limit` requests in the current minute window."""
    client_ip = request.client.host if request.client else "unknown"
    bucket = int(time.time()) // _WINDOW_SECS
    key = f"rl:{request.url.path}:{client_ip}:{bucket}"

    redis = await get_redis_pool()
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _WINDOW_SECS + 5)

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "rate_limited",
                "message_ru": "Слишком много попыток. Повторите через минуту.",
            },
        )
