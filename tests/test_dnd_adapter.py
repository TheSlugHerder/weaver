import asyncio
from src.weaver.game import dnd_adapter


def test_resolve_attack_fallback():
    attacker = {"attack_bonus": 2, "damage_mod": 1}
    defender = {"ac": 12, "hp": 10}
    res = dnd_adapter.resolve_attack(attacker, defender, attack_mod=2)
    assert "roll" in res
    assert "total" in res
    assert "hit" in res
    assert "damage" in res
    # defender hp should be present in returned 'defender'
    if res.get("hit"):
        assert res["defender"]["hp"] <= 10


def test_resolve_save_fallback():
    subject = {"save_bonus": 1, "hp": 8}
    res = dnd_adapter.resolve_save(subject, dc=10, save_type="dex")
    assert "roll" in res and "total" in res and "success" in res


def test_resolve_spell_fallback():
    caster = {"id": "c1"}
    targets = [{"name": "goblin", "hp": 6}, {"name": "wolf", "hp": 10}]
    res = dnd_adapter.resolve_spell(caster, targets, "firebolt")
    assert res["spell"] == "firebolt"
    assert isinstance(res.get("results"), list)
