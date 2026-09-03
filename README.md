Weaver — D&D multiplayer core

Minimal scaffold for a FastAPI-based game engine that integrates dnd-5e-core, Beanie (MongoDB), and LLM interfaces.

Quickstart

1. Create and activate a virtualenv with Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the dev server:

```bash
python -m src.weaver.main
```

What's included

- `requirements.txt` — project dependencies
- `src/weaver/main.py` — minimal FastAPI app and entrypoint
- `tests/test_main.py` — basic healthcheck test

Next steps

- Add authentication and Beanie models
- Integrate `dnd-5e-core` game loop and rules engine
- Add AI parsers and narrator interfaces
- Build frontend and deployment configs

See the deployment guide for production setup: [DEPLOYMENT.md](DEPLOYMENT.md)

Redis dependency helpers
------------------------

The project exposes typed FastAPI dependency helpers for accessing the Redis client:

- `get_redis` — optional dependency that returns the Redis client if available (`None` otherwise).
- `require_redis()` — dependency factory that raises `503` when Redis is unavailable.

Example usage in a route:

```python
from fastapi import APIRouter, Depends
from src.weaver.rate_limiter import get_redis, require_redis

router = APIRouter()

@router.get("/maybe")
async def maybe(redis=Depends(get_redis)):
	# `redis` will be a Redis client instance or None
	return {"has_redis": redis is not None}

@router.get("/required")
async def required(redis=Depends(require_redis())):
	# `redis` is guaranteed to be present; otherwise a 503 response is returned
	await redis.ping()
	return {"ok": True}
```

When the app starts it will attempt to initialize a Redis client from `REDIS_URL` and attach it to `app.state.redis`. In development the app falls back to an in-memory limiter when Redis is unavailable; in production (when `ENV=production`) startup will fail if Redis cannot be reached.

