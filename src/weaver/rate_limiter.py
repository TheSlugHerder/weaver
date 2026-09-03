import time
import asyncio
import logging
from typing import Optional

from src.weaver.config import settings
from src.weaver import metrics as metrics_mod

try:
    import redis.asyncio as aioredis
    from redis.exceptions import RedisError
except Exception:
    aioredis = None
    RedisError = Exception

# Redis client may not be available at import time; keep untyped to avoid referencing aioredis when absent
_redis: Optional[object] = None

# Rate limiter config
KEY_PREFIX = "ratelimit:"
MAX_IN_MEMORY_ENTRIES = int(getattr(settings, "RATE_LIMIT_IN_MEMORY_MAX", 10000))
LOGGER = logging.getLogger("weaver.rate_limiter")

_in_memory_store = {}
_in_memory_lock = asyncio.Lock()


async def _get_redis():
    global _redis
    # Prefer explicit client set via `set_redis_client` or `init_redis_from_settings`
    if _redis is not None:
        return _redis

    # Lazy-create if not set (best-effort fallback)
    redis_url = getattr(settings, "REDIS_URL", None)
    if aioredis and redis_url:
        try:
            _redis = aioredis.from_url(redis_url)
            await _redis.ping()
            try:
                metrics_mod.redis_up.set(1)
            except Exception:
                pass
            return _redis
        except Exception as e:
            LOGGER.warning("Lazy Redis connection failed: %s", e)
            try:
                metrics_mod.redis_up.set(0)
            except Exception:
                pass
    return _redis


def set_redis_client(client: object):
    """Set the global redis client (used by app startup).

    The client should be an instance returned by `redis.asyncio.from_url()`.
    """
    global _redis
    _redis = client


async def init_redis_from_settings(attempts: int = 5, raise_on_failure: bool = False) -> bool:
    """Initialize a redis client from `settings.REDIS_URL` with retries.

    Returns True if a client is available, False otherwise. If `raise_on_failure`
    is True and connection cannot be established, raises RuntimeError.
    """
    global _redis
    redis_url = getattr(settings, "REDIS_URL", None)
    if not aioredis or not redis_url:
        return False

    backoff = 0.2
    last_exc = None
    for i in range(attempts):
        try:
            client = aioredis.from_url(redis_url, max_connections=50)
            await client.ping()
            _redis = client
            try:
                metrics_mod.redis_up.set(1)
            except Exception:
                pass
            LOGGER.info("Connected to Redis at %s", redis_url)
            return True
        except Exception as e:
            last_exc = e
            LOGGER.warning("Redis init attempt %d/%d failed: %s", i + 1, attempts, e)
            try:
                metrics_mod.redis_up.set(0)
            except Exception:
                pass
            await asyncio.sleep(backoff)
            backoff *= 2

    LOGGER.error("Failed to initialize Redis after %d attempts", attempts)
    try:
        metrics_mod.redis_up.set(0)
    except Exception:
        pass
    if raise_on_failure:
        raise RuntimeError(f"Could not connect to Redis: {last_exc}")
    return False


# Typed dependency helpers for FastAPI
try:
    from redis.asyncio.client import Redis as RedisClient
except Exception:
    RedisClient = object


async def get_redis(request=None) -> Optional[RedisClient]:
    """FastAPI dependency: returns the Redis client if available, otherwise None.

    Usage in route: `redis = Depends(get_redis)`
    """
    # Accept either Request or no args; FastAPI will pass Request when used as dependency
    client = None
    try:
        if request is not None:
            app = getattr(request, "app", None)
            if app is not None:
                client = getattr(app.state, "redis", None)
    except Exception:
        client = None

    if client is None:
        client = await _get_redis()

    return client


def require_redis():
    """Dependency factory that raises 503 if Redis is not available.

    Use as `redis = Depends(require_redis())` in FastAPI routes.
    """

    async def _dep(request=None):
        client = None
        try:
            if request is not None:
                app = getattr(request, "app", None)
                if app is not None:
                    client = getattr(app.state, "redis", None)
        except Exception:
            client = None

        if client is None:
            client = await _get_redis()
        if client is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="Redis unavailable")
        return client

    return _dep


async def allow(key: str, limit: int = 5, per_seconds: int = 60) -> bool:
    """Return True if action is allowed under the rate limit, False otherwise.

    Uses Redis INCR+EXPIRE for atomic counting when `REDIS_URL` is configured.
    Falls back to a simple in-memory counter for development/testing.
    """
    r = await _get_redis()
    if r:
        try:
            # namespace the key to avoid collisions
            redis_key = f"{KEY_PREFIX}{key}"
            val = await r.incr(redis_key)
            if val == 1:
                await r.expire(redis_key, per_seconds)
            try:
                metrics_mod.redis_up.set(1)
            except Exception:
                pass
            return val <= limit
        except Exception:
            # Redis error — fall back to in-memory
            try:
                metrics_mod.rate_limiter_fallbacks.inc()
            except Exception:
                pass

    now = int(time.time())
    async with _in_memory_lock:
        # cleanup if the store grows too large
        if len(_in_memory_store) > MAX_IN_MEMORY_ENTRIES:
            # remove expired entries first
            keys_to_remove = [k for k, v in _in_memory_store.items() if v[1] <= now]
            for k in keys_to_remove:
                _in_memory_store.pop(k, None)
            # if still too large, remove oldest entries (best-effort)
            if len(_in_memory_store) > MAX_IN_MEMORY_ENTRIES:
                sorted_items = sorted(_in_memory_store.items(), key=lambda kv: kv[1][1])
                for k, _ in sorted_items[: len(_in_memory_store) - MAX_IN_MEMORY_ENTRIES]:
                    _in_memory_store.pop(k, None)

        entry = _in_memory_store.get(key)
        if not entry or entry[1] <= now:
            _in_memory_store[key] = [1, now + per_seconds]
            return True
        if entry[0] >= limit:
            return False
        entry[0] += 1
        return True


# utility for tests: clear in-memory key
async def _clear_in_memory(key: str):
    async with _in_memory_lock:
        _in_memory_store.pop(key, None)


async def close_redis():
    """Close the global redis client if present."""
    global _redis
    try:
        if _redis is not None:
            # aioredis client has an async close method
            try:
                try:
                    metrics_mod.redis_up.set(0)
                except Exception:
                    pass
                await _redis.close()
            except Exception:
                # best-effort close
                pass
    except Exception:
        pass
    _redis = None
 