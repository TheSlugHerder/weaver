import os
import pytest

from src.weaver import rate_limiter


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="No REDIS_URL configured")
async def test_rate_limiter_redis_backend():
    r = await rate_limiter._get_redis()
    assert r is not None, "Redis client not available"
    key = "test:redis:rate"
    # ensure key removed
    await r.delete(key)

    assert await rate_limiter.allow(key, limit=2, per_seconds=2)
    assert await rate_limiter.allow(key, limit=2, per_seconds=2)
    assert not await rate_limiter.allow(key, limit=2, per_seconds=2)

    # cleanup and wait for expiry
    await r.delete(key)
    import asyncio

    await asyncio.sleep(2)
    assert await rate_limiter.allow(key, limit=2, per_seconds=2)
    await r.delete(key)
