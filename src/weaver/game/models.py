import time
from typing import Any

from beanie import Document
from pydantic import Field


class Event(Document):
    session_id: str
    actor_id: str | None
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"  # pending | processing | done | failed
    result: dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(default_factory=lambda: int(time.time()))
    execute_at: int | None = None

    class Settings:
        name = "events"


class TurnOrder(Document):
    session_id: str
    order: list[str] = Field(default_factory=list)  # list of actor/user ids
    current_index: int = 0

    class Settings:
        name = "turn_orders"
