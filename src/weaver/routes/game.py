from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from src.weaver.game.engine import GameEngine
from src.weaver.auth import get_current_user
from src.weaver.models.user import User
from src.weaver.game.turns import TurnManager
from src.weaver.decorators import rate_limit_dep, require_role_dep
from typing import Dict, Any

router = APIRouter(prefix="/game", tags=["game"])


class CreateSessionPayload(BaseModel):
    name: str


class JoinPayload(BaseModel):
    character_name: Optional[str] = None


class AttackPayload(BaseModel):
    target_index: int = 0
    attack_mod: int = 0


class ActionPayload(BaseModel):
    type: str
    payload: Dict[str, Any] = {}


@router.post("/create")
async def create_session(
    payload: CreateSessionPayload,
    user: User = Depends(get_current_user),
    _rl: None = Depends(rate_limit_dep(10, 60)),
    _role: None = Depends(require_role_dep('dm')),
):
    session = await GameEngine.create_session(payload.name, owner_id=str(user.id))
    return {"id": str(session.id), "name": session.name}


@router.post("/{session_id}/join")
async def join_session(
    session_id: str,
    payload: JoinPayload,
    user: User = Depends(get_current_user),
    _rl: None = Depends(rate_limit_dep(20, 60)),
):
    try:
        player = await GameEngine.add_player(session_id, str(user.id), payload.character_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"id": str(player.user_id), "character_name": player.character_name}


@router.post("/{session_id}/attack")
async def attack(
    session_id: str,
    payload: AttackPayload,
    user: User = Depends(get_current_user),
    _rl: None = Depends(rate_limit_dep(30, 60)),
):
    try:
        result = await GameEngine.attack_monster(session_id, str(user.id), payload.target_index, payload.attack_mod)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/{session_id}/action")
async def submit_action(
    session_id: str,
    action: ActionPayload,
    user: User = Depends(get_current_user),
    _rl: None = Depends(rate_limit_dep(60, 60)),
):
    # enqueue action for background processing
    evt = await TurnManager.enqueue_action(session_id, str(user.id), action.type, action.payload)
    return {"event_id": str(evt.id), "status": evt.status}



@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    user: User = Depends(get_current_user),
    _role: None = Depends(require_role_dep('dm')),
):
    try:
        await GameEngine.end_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "ended", "id": session_id}
