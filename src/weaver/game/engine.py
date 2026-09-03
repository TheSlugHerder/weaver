import random
from typing import Optional

from src.weaver.models.game import GameSession, PlayerState, Room
from src.weaver.game import dnd_adapter


class GameEngine:
    @staticmethod
    async def create_session(name: str, owner_id: Optional[str] = None) -> GameSession:
        session = GameSession(name=name, owner_id=owner_id, players=[], room_ids=[])
        await session.insert()
        return session

    @staticmethod
    async def add_player(session_id: str, user_id: str, character_name: Optional[str] = None) -> PlayerState:
        session = await GameSession.get(session_id)
        if not session:
            raise ValueError("Session not found")
        player = PlayerState(user_id=user_id, character_name=character_name, hp=10, location_room_id=None, inventory=[])
        session.players.append(player)
        await session.save()
        return player

    @staticmethod
    async def attack_monster(session_id: str, attacker_user_id: str, target_index: int = 0, attack_mod: int = 0) -> dict:
        session = await GameSession.get(session_id)
        if not session:
            raise ValueError("Session not found")
        if not session.room_ids:
            raise ValueError("Session has no rooms")
        # pick first room for now
        room = await Room.get(session.room_ids[0])
        if not room:
            raise ValueError("Room not found")
        if target_index < 0 or target_index >= len(room.monsters):
            raise ValueError("Invalid monster index")
        monster = room.monsters[target_index]
        attacker_stats = {"attack_bonus": attack_mod}
        defender_stats = {"ac": monster.ac or 10, "hp": monster.hp}
        result = dnd_adapter.resolve_attack(attacker_stats, defender_stats, attack_mod=attack_mod)
        hit = result.get("hit", False)
        damage = result.get("damage", 0)
        # update monster hp if provided by adapter
        new_hp = None
        if isinstance(result.get("defender"), dict):
            new_hp = result["defender"].get("hp")
        if new_hp is not None:
            monster.hp = new_hp
        # persist changes to room
        room.monsters[target_index] = monster
        await room.save()
        return {
            "attacker_id": attacker_user_id,
            "monster": {"name": monster.name, "hp": monster.hp},
            "result": result,
            "hit": hit,
            "damage": damage,
        }

    @staticmethod
    async def resolve_save(session_id: str, target_type: str, target_index: int, dc: int, save_type: str = "dex") -> dict:
        """Resolve a saving throw for a target in the session's first room.

        target_type: 'monster' or 'player'
        target_index: index into monsters list (for monster) or players list (for player)
        """
        session = await GameSession.get(session_id)
        if not session:
            raise ValueError("Session not found")
        if not session.room_ids:
            raise ValueError("Session has no rooms")
        room = await Room.get(session.room_ids[0])
        if not room:
            raise ValueError("Room not found")

        if target_type == "monster":
            if target_index < 0 or target_index >= len(room.monsters):
                raise ValueError("Invalid monster index")
            monster = room.monsters[target_index]
            subject = {"save_bonus": monster.keywords.count("save") if hasattr(monster, "keywords") else 0, "hp": monster.hp}
            res = dnd_adapter.resolve_save(subject, dc, save_type)
            # include subject hp if changed
            if isinstance(res.get("defender"), dict) and res["defender"].get("hp") is not None:
                monster.hp = res["defender"]["hp"]
                room.monsters[target_index] = monster
                await room.save()
            return {"target": monster.name, "result": res}

        if target_type == "player":
            if target_index < 0 or target_index >= len(session.players):
                raise ValueError("Invalid player index")
            player = session.players[target_index]
            subject = {"save_bonus": 0, "hp": player.hp}
            res = dnd_adapter.resolve_save(subject, dc, save_type)
            # update player hp if adapter changed it
            if isinstance(res.get("defender"), dict) and res["defender"].get("hp") is not None:
                player.hp = res["defender"]["hp"]
                await session.save()
            return {"target": player.user_id, "result": res}

        raise ValueError("Unknown target_type")

    @staticmethod
    async def cast_spell(session_id: str, caster_user_id: str, spell_name: str, target_indices: list) -> dict:
        """Cast a spell from caster to targets in the session's first room.

        target_indices: list of monster indices to affect.
        """
        session = await GameSession.get(session_id)
        if not session:
            raise ValueError("Session not found")
        if not session.room_ids:
            raise ValueError("Session has no rooms")
        room = await Room.get(session.room_ids[0])
        if not room:
            raise ValueError("Room not found")

        caster = {"id": caster_user_id}
        targets = []
        for idx in target_indices:
            if idx < 0 or idx >= len(room.monsters):
                continue
            m = room.monsters[idx]
            targets.append({"name": m.name, "hp": m.hp, "ac": m.ac})

        res = dnd_adapter.resolve_spell(caster, targets, spell_name)
        # apply hp changes from adapter results
        results = res.get("results", [])
        for i, r in enumerate(results):
            t = r.get("target")
            if isinstance(t, dict) and "name" in t:
                # find monster by name and update hp if present
                name = t["name"]
                for mi, mon in enumerate(room.monsters):
                    if mon.name == name:
                        if t.get("hp") is not None:
                            room.monsters[mi].hp = t["hp"]
        await room.save()
        return {"caster": caster_user_id, "spell": spell_name, "result": res}

    @staticmethod
    async def end_session(session_id: str) -> bool:
        session = await GameSession.get(session_id)
        if not session:
            raise ValueError("Session not found")
        await session.delete()
        return True
