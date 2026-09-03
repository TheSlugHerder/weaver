from fastapi import APIRouter, Depends, HTTPException

from src.weaver.rate_limiter import get_redis, require_redis

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/redis")
async def health_redis(r=Depends(require_redis())):
    """Public health endpoint that returns 200 when Redis is available.

    This endpoint requires Redis and returns 503 if Redis cannot be reached.
    """
    try:
        pong = await r.ping()
        return {"status": "ok", "redis": True, "pong": pong}
    except Exception:
        raise HTTPException(status_code=503, detail="Redis ping failed")


@router.get("/redis-optional")
async def health_redis_optional(r=Depends(get_redis)):
    """Optional Redis health: returns Redis status if present, otherwise reports unavailable without 503."""
    if not r:
        return {"status": "ok", "redis": False}
    try:
        pong = await r.ping()
        return {"status": "ok", "redis": True, "pong": pong}
    except Exception:
        return {"status": "ok", "redis": False}
