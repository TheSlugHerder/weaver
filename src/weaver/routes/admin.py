
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.weaver import hooks
from src.weaver.auth import get_current_user
from src.weaver.decorators import require_role_dep
from src.weaver.models.user import User
from src.weaver.rate_limiter import get_redis

router = APIRouter(prefix="/admin", tags=["admin"])


class RolePayload(BaseModel):
    role: str


@router.get("/users")
async def list_users(user=Depends(get_current_user), _auth=Depends(require_role_dep('admin'))):
    users = await User.find_all().to_list()
    # return minimal fields
    return [{"id": str(u.id), "email": u.email, "roles": u.roles} for u in users]


@router.get("/users/{user_id}")
async def get_user(user_id: str, user=Depends(get_current_user), _auth=Depends(require_role_dep('admin'))):
    u = await User.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": str(u.id), "email": u.email, "roles": u.roles}


@router.post("/users/{user_id}/roles")
async def add_role(user_id: str, payload: RolePayload, user=Depends(get_current_user), _auth=Depends(require_role_dep('admin'))):
    role = payload.role
    if not role:
        raise HTTPException(status_code=400, detail="role required")
    u = await User.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if role.lower() not in [r.lower() for r in u.roles]:
        u.roles.append(role)
        await u.save()
        await hooks.on_role_change(str(u.id), role, 'added')
    return {"id": str(u.id), "roles": u.roles}


@router.delete("/users/{user_id}/roles")
async def remove_role(user_id: str, payload: RolePayload, user=Depends(get_current_user), _auth=Depends(require_role_dep('admin'))):
    role = payload.role
    if not role:
        raise HTTPException(status_code=400, detail="role required")
    u = await User.get(user_id)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.roles = [r for r in u.roles if r.lower() != role.lower()]
    await u.save()
    await hooks.on_role_change(str(u.id), role, 'removed')
    return {"id": str(u.id), "roles": u.roles}


@router.get("/health/redis")
async def admin_redis_health(user=Depends(get_current_user), _auth=Depends(require_role_dep('admin')), r=Depends(get_redis)):
    """Admin-only Redis health endpoint with limited details."""
    if not r:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    try:
        pong = await r.ping()
        info = await r.info()
        return {"status": "ok", "redis": True, "pong": pong, "clients": info.get("connected_clients")}
    except Exception:
        raise HTTPException(status_code=503, detail="Redis ping failed")
