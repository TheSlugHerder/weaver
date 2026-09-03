from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.weaver import auth, db, rate_limiter
from src.weaver import metrics as metrics_mod
from src.weaver.config import settings
from src.weaver.game.worker import BackgroundWorker
from src.weaver.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from src.weaver.routes import game as game_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    # ensure a secure secret key is available (generates a temporary one for dev if missing)
    settings.ensure_secret()
    await db.init_db()
    auth.init_auth(app)
    app.include_router(game_routes.router)
    # admin routes for managing users/roles
    from src.weaver.routes import admin as admin_routes
    app.include_router(admin_routes.router)
    # health routes
    from src.weaver.routes import health as health_routes
    app.include_router(health_routes.router)
    # Initialize Redis client early for robust rate-limiting. In production we
    # prefer to fail fast if Redis is required; in development we log and fall back.
    try:
        # Attempt to initialize Redis from settings; raise in production on failure
        await rate_limiter.init_redis_from_settings(
            attempts=5, raise_on_failure=(settings.ENV == "production")
        )
    except Exception:
        # Allow startup to continue in development if Redis is unavailable.
        # The rate limiter falls back to in-memory counters.
        import logging

        logging.getLogger("weaver.main").exception("Redis initialization failed on startup")

    app.state._weaver_worker = BackgroundWorker()
    app.state._weaver_worker.start()
    try:
        # expose redis client to application state if available
        try:
            redis_client = await rate_limiter._get_redis()
            if redis_client is not None:
                app.state.redis = redis_client
        except Exception:
            # non-fatal: if redis cannot be exposed, continue
            import logging

            logging.getLogger("weaver.main").exception("Failed to attach redis to app.state")

        yield
    finally:
        # shutdown
        worker = getattr(app.state, "_weaver_worker", None)
        if worker:
            await worker.stop()
        # close redis client and remove from app state
        try:
            await rate_limiter.close_redis()
        except Exception:
            import logging

            logging.getLogger("weaver.main").exception("Error closing redis client")
        try:
            if hasattr(app.state, "redis"):
                app.state.redis = None
        except Exception:
            pass
        db.close_db()


app = FastAPI(title="Weaver Core", version="0.1.0", lifespan=lifespan)

# Add middleware for security and request tracing
# TrustedHostMiddleware: only apply when ALLOWED_HOSTS configured
if settings.ALLOWED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# HTTPS redirect in production if FORCE_HTTPS
if settings.FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS: only enable if origins are configured explicitly
if settings.CORS_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Request ID and security headers
hsts = None
if settings.FORCE_HTTPS:
    include_sub = "; includeSubDomains" if settings.HSTS_INCLUDE_SUBDOMAINS else ""
    hsts = f"max-age={settings.HSTS_MAX_AGE}{include_sub}; preload"
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware, hsts_value=hsts)


@app.get("/metrics")
async def metrics_endpoint():
    return metrics_mod.metrics_response()


@app.get("/", tags=["root"])
async def read_root(request: Request):
    return JSONResponse({"status": "ok", "service": "weaver"})


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.weaver.main:app", host="127.0.0.1", port=8000, reload=True)
