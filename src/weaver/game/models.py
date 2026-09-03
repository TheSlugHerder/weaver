import time
from beanie import Document
from pydantic import Field
from typing import Optional, Dict, Any, List


class Event(Document):
    session_id: str
    actor_id: Optional[str]
    type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending | processing | done | failed
    result: Dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    execute_at: Optional[int] = None

    class Settings:
        name = "events"


class TurnOrder(Document):
    session_id: str
    order: List[str] = Field(default_factory=list)  # list of actor/user ids
    current_index: int = 0

    class Settings:
        name = "turn_orders"
