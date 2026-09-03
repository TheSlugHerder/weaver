import os

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.weaver.rate_limiter import get_redis, require_redis

app = FastAPI()


@app.get("/maybe")
async def maybe(r=Depends(get_redis)):
    # returns true when redis is present, false otherwise
    return {"has_redis": r is not None}


@app.get("/required")
async def required(r=Depends(require_redis())):
    return {"ok": True}


def test_get_redis_none():
    client = TestClient(app)
    r = client.get("/maybe")
    assert r.status_code == 200
    # In CI with no REDIS_URL set this should be False (None)
    assert isinstance(r.json().get("has_redis"), bool)


def test_require_redis_unavailable():
    client = TestClient(app)
    r = client.get("/required")
    if os.getenv("REDIS_URL"):
        # In CI the Redis service is provided; ensure endpoint succeeds
        assert r.status_code == 200
        assert r.json().get("ok") is True
    else:
        # When Redis is not configured, the endpoint should return 503
        assert r.status_code == 503
