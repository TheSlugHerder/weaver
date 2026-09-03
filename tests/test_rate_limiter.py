import asyncio

from weaver import rate_limiter as rl


def test_in_memory_rate_limiter():
    key = "test-rate-limiter"

    async def run():
        await rl._clear_in_memory(key)
        # allow 3 actions within window
        assert await rl.allow(key, limit=3, per_seconds=10)
        assert await rl.allow(key, limit=3, per_seconds=10)
        assert await rl.allow(key, limit=3, per_seconds=10)
        # fourth should be blocked
        assert not await rl.allow(key, limit=3, per_seconds=10)
        await rl._clear_in_memory(key)

    asyncio.run(run())
