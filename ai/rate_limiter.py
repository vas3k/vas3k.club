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

# Lua script for atomic rate limiting
RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local window_seconds = tonumber(ARGV[4])

-- Remove expired entries
redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

-- Check current count
local current_count = redis.call('ZCARD', key)

if current_count >= max_requests then
    return 1
end

-- Add current timestamp
redis.call('ZADD', key, now, tostring(now))

-- Set expiry for key to allow Redis cleanup
redis.call('EXPIRE', key, window_seconds)

return 0
"""

_rate_limit_script = redis_client.register_script(RATE_LIMIT_SCRIPT)


def is_rate_limited(key: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_SLIDING_WINDOW_SECONDS

    redis_key = f"rate_limit:{key}"

    result = _rate_limit_script(
        keys=[redis_key],
        args=[now, window_start, RATE_LIMIT_REQUESTS, RATE_LIMIT_SLIDING_WINDOW_SECONDS]
    )

    return result == 1
