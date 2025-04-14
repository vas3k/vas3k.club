import time

import redis
from django.conf import settings

from ai.config import RATE_LIMIT_REQUESTS, RATE_LIMIT_SLIDING_WINDOW_SECONDS

redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,
    decode_responses=True
)


def is_rate_limited(key: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_SLIDING_WINDOW_SECONDS

    redis_key = f"rate_limit:{key}"

    # Remove expired entries
    redis_client.zremrangebyscore(redis_key, 0, window_start)

    # Check current count
    current_count = redis_client.zcard(redis_key)
    if current_count >= RATE_LIMIT_REQUESTS:
        return True

    # Add current timestamp
    redis_client.zadd(redis_key, {str(now): now})

    # Set expiry for key to allow Redis cleanup
    redis_client.expire(redis_key, RATE_LIMIT_SLIDING_WINDOW_SECONDS)

    return False
