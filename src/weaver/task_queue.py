import os
from typing import Optional

try:
    import redis.asyncio as aioredis
except Exception:
    aioredis = None

REDIS_URL = os.getenv("REDIS_URL")
_QUEUE_KEY = os.getenv("WEAVER_QUEUE_KEY", "weaver:events")
_redis: Optional[object] = None


async def get_redis():
    global _redis
    if _redis is None and aioredis and REDIS_URL:
        _redis = aioredis.from_url(REDIS_URL)
    return _redis


async def enqueue(event_id: str) -> bool:
    r = await get_redis()
    if not r:
        return False
    try:
        # LPUSH to push to left, worker BRPOP pops from right (FIFO)
        await r.lpush(_QUEUE_KEY, event_id)
        return True
    except Exception:
        return False


async def dequeue(timeout: int = 1):
    r = await get_redis()
    if not r:
        return None
    try:
        item = await r.brpop(_QUEUE_KEY, timeout=timeout)
        if not item:
            return None
        # item is (key, value)
        return item[1]
    except Exception:
        return None