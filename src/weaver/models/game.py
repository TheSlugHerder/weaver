
from beanie import Document
from pydantic import BaseModel, Field


class Item(BaseModel):
    name: str
    description: str | None = None
    quantity: int = 1
    keywords: list[str] = Field(default_factory=list)


class Monster(BaseModel):
    name: str
    cr: float | None = None
    hp: int | None = None
    ac: int | None = None
    keywords: list[str] = Field(default_factory=list)


class Exit(BaseModel):
    direction: str
    target_room_id: str


class Room(Document):
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    exits: list[Exit] = Field(default_factory=list)
    items: list[Item] = Field(default_factory=list)
    monsters: list[Monster] = Field(default_factory=list)

    class Settings:
        name = "rooms"


class PlayerState(BaseModel):
    user_id: str
    character_name: str | None = None
    hp: int | None = None
    location_room_id: str | None = None
    inventory: list[Item] = Field(default_factory=list)


class GameSession(Document):
    name: str
    owner_id: str | None = None
    players: list[PlayerState] = []
    room_ids: list[str] = []

    class Settings:
        name = "sessions"
