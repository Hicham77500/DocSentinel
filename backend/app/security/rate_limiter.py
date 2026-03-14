from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException, status
import redis
from redis import Redis
from redis.exceptions import RedisError

from app.config.settings import settings


RATE_LIMIT = 100
WINDOW_SECONDS = 60


@lru_cache(maxsize=1)
def _get_redis_client() -> Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def enforce_rate_limit(api_key: str) -> None:
    redis_key = f"rate_limit:{api_key}"
    try:
        client = _get_redis_client()
        request_count = client.incr(redis_key)
        if request_count == 1:
            client.expire(redis_key, WINDOW_SECONDS)
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Rate limiter unavailable: {exc}",
        ) from exc

    if request_count > RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later.",
        )
