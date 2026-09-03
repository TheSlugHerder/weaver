import logging
import uuid
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

LOGGER = logging.getLogger("weaver.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, hsts_value: str | None = None):
        super().__init__(app)
        self.hsts_value = hsts_value

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        # Common security headers
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=()")
        # Basic CSP — keep strict but allow inline when necessary
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
        if self.hsts_value:
            response.headers.setdefault("Strict-Transport-Security", self.hsts_value)
        return response
