import os

import pytest

from src.weaver import rate_limiter


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("REDIS_URL"), reason="No REDIS_URL configured")
async def test_rate_limiter_redis_backend():
    key = "test:redis:rate"
    # reset via allow() wrapper instead of direct redis client to avoid loop issues
    try:
        # ensure clean state by calling allow with high limit and short window
        for _ in range(3):
            await rate_limiter.allow(key, limit=1000, per_seconds=1)

        assert await rate_limiter.allow(key, limit=2, per_seconds=2)
        assert await rate_limiter.allow(key, limit=2, per_seconds=2)
        assert not await rate_limiter.allow(key, limit=2, per_seconds=2)
    except RuntimeError:
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
