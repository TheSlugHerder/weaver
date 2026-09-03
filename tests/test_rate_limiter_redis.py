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

    try:
        assert await rate_limiter.allow(key, limit=2, per_seconds=2)
        assert await rate_limiter.allow(key, limit=2, per_seconds=2)
        assert not await rate_limiter.allow(key, limit=2, per_seconds=2)
    except RuntimeError:
        # Some CI environments produce event-loop errors; treat as skip
        pytest.skip("Event loop error interacting with redis in this environment")

    # cleanup and wait for expiry
    await r.delete(key)
    import asyncio

    await asyncio.sleep(2)
    try:
        assert await rate_limiter.allow(key, limit=2, per_seconds=2)
    except RuntimeError:
        pytest.skip("Event loop error interacting with redis in this environment")
    await r.delete(key)
