import pytest
from src.weaver import auth
from src.weaver import rate_limiter


def test_hash_and_verify_password():
    pwd = "s3cret"
    h = auth._hash_password(pwd)
    assert auth._verify_password(pwd, h)
    assert not auth._verify_password("wrong", h)


@pytest.mark.asyncio
async def test_rate_limiter_simple():
    key = "test:key"
    # clear any previous in-memory counter
    await rate_limiter._clear_in_memory(key)
    # allow up to 3 calls per 2 seconds
    assert await rate_limiter.allow(key, limit=3, per_seconds=2)
    assert await rate_limiter.allow(key, limit=3, per_seconds=2)
    assert await rate_limiter.allow(key, limit=3, per_seconds=2)
    # next should be rejected
    assert not await rate_limiter.allow(key, limit=3, per_seconds=2)

    # wait for window to expire
    import time

    time.sleep(2)
    assert await rate_limiter.allow(key, limit=3, per_seconds=2)
