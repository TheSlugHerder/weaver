import pytest
import asyncio

from src.weaver.game import engine


class MockMonster:
    def __init__(self, name, ac=10, hp=10):
        self.name = name
        self.ac = ac
        self.hp = hp


class MockRoom:
    def __init__(self, monsters):
        self.monsters = monsters
        self.saved = False

    async def save(self):
        self.saved = True


class MockSession:
    def __init__(self, room_ids):
        self.room_ids = room_ids


@pytest.mark.asyncio
async def test_attack_monster_uses_adapter(monkeypatch):
    # Prepare mock room and session
    mock_monster = MockMonster("orc", ac=12, hp=15)
    mock_room = MockRoom([mock_monster])

    async def mock_get_room(room_id):
        return mock_room

    async def mock_get_session(session_id):
        return MockSession(room_ids=["r1"])

    # Patch engine's GameSession.get and Room.get
    monkeypatch.setattr(engine, "GameSession", type("X", (), {"get": staticmethod(mock_get_session)}))
    monkeypatch.setattr(engine, "Room", type("Y", (), {"get": staticmethod(mock_get_room)}))

    # Patch adapter to return a deterministic hit
    async def fake_resolve_attack(att, defn, attack_mod=0):
        return {"hit": True, "damage": 5, "defender": {"hp": 10}}

    # dnd_adapter.resolve_attack is synchronous in our adapter, so patch there
    from src.weaver.game import dnd_adapter

    monkeypatch.setattr(dnd_adapter, "resolve_attack", lambda a, d, attack_mod=0: {"hit": True, "damage": 5, "defender": {"hp": 10}})

    res = await engine.GameEngine.attack_monster("s1", "u1", target_index=0, attack_mod=2)
    assert res["hit"] is True
    assert res["damage"] == 5
    assert mock_room.saved is True
    # monster hp updated
    assert mock_room.monsters[0].hp == 10
