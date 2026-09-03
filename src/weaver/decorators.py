from typing import Callable, Optional
from functools import wraps
from fastapi import HTTPException, Request

from src.weaver import rate_limiter
from fastapi import Depends
from src.weaver.auth import get_current_user
from src.weaver.models.user import User


def _default_key_func(user, request: Optional[Request]):
    if user is not None:
        return f"user:{getattr(user, 'id', getattr(user, 'pk', str(user)))}"
    if request is not None:
        client = getattr(request, 'client', None)
        if client is not None:
            return f"ip:{client.host}"
    return "anon:global"


def rate_limit(limit: int = 30, per_seconds: int = 60, key_func: Optional[Callable] = None):
    """Decorator to apply a simple rate limit per user or IP.

    Usage:
    @rate_limit(10, 60)
    async def endpoint(..., user=Depends(get_current_user)):
        ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get('request', None)
            user = kwargs.get('user', None)
            key_f = key_func or _default_key_func
            try:
                key = key_f(user, request)
            except Exception:
                key = _default_key_func(user, request)

            allowed = await rate_limiter.allow(key, limit, per_seconds)
            if not allowed:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: str):
    """Simple role check decorator.

    By default checks `user.is_superuser` for any privileged role.
    If your `User` model adds a `roles` or `is_dm` field, update this check.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('user')
            if user is None:
                raise HTTPException(status_code=401, detail="Authentication required")
            # basic DM check
            # allow if superuser or has the requested role
            if not (getattr(user, 'is_superuser', False) or role.lower() in [r.lower() for r in getattr(user, 'roles', [])]):
                raise HTTPException(status_code=403, detail=f"{role} role required")
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_dep(limit: int = 30, per_seconds: int = 60, key_func: Optional[Callable] = None):
    """Dependency factory returning a FastAPI dependency that enforces rate limiting.

    Use in routes as: `Depends(rate_limit_dep(10, 60))`.
    """

    async def _dep(request: Request, user: Optional[User] = Depends(get_current_user)):
        key_f = key_func or _default_key_func
        try:
            key = key_f(user, request)
        except Exception:
            key = _default_key_func(user, request)

        allowed = await rate_limiter.allow(key, limit, per_seconds)
        if not allowed:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return _dep


def require_role_dep(role: str):
    """Dependency factory returning a FastAPI dependency that enforces a role.

    Use in routes as: `Depends(require_role_dep('dm'))`.
    """

    async def _dep(user: Optional[User] = Depends(get_current_user)):
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not (getattr(user, 'is_superuser', False) or role.lower() in [r.lower() for r in getattr(user, 'roles', [])]):
            raise HTTPException(status_code=403, detail=f"{role} role required")

    return _dep
