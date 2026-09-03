from beanie import Document
from pydantic import BaseModel, Field
from typing import List, Optional


class Item(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: int = 1
    keywords: List[str] = Field(default_factory=list)


class Monster(BaseModel):
    name: str
    cr: Optional[float] = None
    hp: Optional[int] = None
    ac: Optional[int] = None
    keywords: List[str] = Field(default_factory=list)


class Exit(BaseModel):
    direction: str
    target_room_id: str


class Room(Document):
    name: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    exits: List[Exit] = Field(default_factory=list)
    items: List[Item] = Field(default_factory=list)
    monsters: List[Monster] = Field(default_factory=list)

    class Settings:
        name = "rooms"


class PlayerState(BaseModel):
    user_id: str
    character_name: Optional[str] = None
    hp: Optional[int] = None
    location_room_id: Optional[str] = None
    inventory: List[Item] = Field(default_factory=list)


class GameSession(Document):
    name: str
    owner_id: Optional[str] = None
    players: List[PlayerState] = []
    room_ids: List[str] = []

    class Settings:
        name = "sessions"
