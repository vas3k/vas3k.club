import logging
import time
from uuid import uuid4

import redis
from django.conf import settings

from ai.config import AI_GLOBAL_HOURLY_REQUESTS, AI_USER_DAILY_REQUESTS, AI_GLOBAL_DAILY_REQUESTS

log = logging.getLogger(__name__)
redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True,
    socket_connect_timeout=2, socket_timeout=2,
)

# Check every sliding window before consuming any quota. Redis runs this atomically.
RATE_LIMIT_SCRIPT = """
local now = tonumber(ARGV[1])
for i, key in ipairs(KEYS) do
    local window = tonumber(ARGV[2 * i + 1])
    local limit = tonumber(ARGV[2 * i + 2])
    redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
    if redis.call('ZCARD', key) >= limit then return 1 end
end
for i, key in ipairs(KEYS) do
    redis.call('ZADD', key, now, ARGV[2])
    redis.call('EXPIRE', key, tonumber(ARGV[2 * i + 1]))
end
return 0
"""


def is_rate_limited(user_id):
    limits = [
        ("ai:quota:ai_bot:hour", 3600, AI_GLOBAL_HOURLY_REQUESTS),
        ("ai:quota:ai_bot:day", 86400, AI_GLOBAL_DAILY_REQUESTS),
        (f"ai:quota:user:{user_id}:day", 86400, AI_USER_DAILY_REQUESTS),
    ]

    arguments = [time.time(), uuid4().hex]

    for name, window, limit in limits:
        arguments.extend((window, limit))

    try:
        return bool(redis_client.eval(RATE_LIMIT_SCRIPT, len(limits), *(item[0] for item in limits), *arguments))
    except redis.RedisError:
        log.warning("AI rate limiter unavailable")
        return True


def can_notify_ai_limit(user_id):
    try:
        return bool(redis_client.set(f"ai:notice:{user_id}", "1", nx=True, ex=60))
    except redis.RedisError:
        return False
