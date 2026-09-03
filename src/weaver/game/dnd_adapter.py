"""Adapter layer for dnd-5e-core integration.

This module provides `resolve_attack`, `resolve_save`, and `resolve_spell` helpers.
If `dnd_5e_core` is available in the environment, it will delegate to that
library; otherwise it falls back to lightweight random-roll behavior so the
engine remains functional for development and testing.
"""
import random
from typing import Any

HAS_DND = False
try:
    import dnd_5e_core as dnd_core  # type: ignore
    HAS_DND = True
except Exception:
    HAS_DND = False


def resolve_attack(attacker: dict[str, Any], defender: dict[str, Any], attack_mod: int = 0) -> dict[str, Any]:
    """Resolve an attack between attacker and defender.

    attacker, defender: lightweight dicts containing at least keys used by
    the fallback implementation (e.g., `ac`, `hp`). The adapter will try to
    call into dnd-5e-core if available; otherwise it performs a d20 + mod
    versus AC and d8 damage on hit.
    """
    if HAS_DND:
        try:
            # Best-effort delegation; exact API depends on dnd-5e-core, so we
            # guard against attribute errors. If the package exposes a
            # resolution function, prefer it.
            if hasattr(dnd_core, "resolve_attack"):
                return dnd_core.resolve_attack(attacker, defender, attack_mod=attack_mod)
        except Exception:
            pass

    # Fallback simple resolution
    roll = random.randint(1, 20)
    total = roll + attack_mod + int(attacker.get("attack_bonus", 0))
    ac = int(defender.get("ac", 10))
    hit = total >= ac
    damage = 0
    if hit:
        damage = random.randint(1, 8) + int(attacker.get("damage_mod", 0))
        defender_hp = defender.get("hp")
        if defender_hp is not None:
            defender["hp"] = max(0, int(defender_hp) - damage)
    return {"roll": roll, "total": total, "ac": ac, "hit": hit, "damage": damage, "defender": defender}


def resolve_save(subject: dict[str, Any], dc: int, save_type: str = "dex") -> dict[str, Any]:
    """Resolve a saving throw for `subject` against `dc`.

    Returns dict with `roll`, `total`, `success`.
    """
    if HAS_DND:
        try:
            if hasattr(dnd_core, "resolve_save"):
                return dnd_core.resolve_save(subject, dc, save_type)
        except Exception:
            pass

    roll = random.randint(1, 20)
    total = roll + int(subject.get("save_bonus", 0))
    success = total >= dc
    return {"roll": roll, "total": total, "dc": dc, "success": success}


def resolve_spell(caster: dict[str, Any], targets: Any, spell_name: str, cast_mods: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve a spell cast. Returns a descriptive result dict.

    This is intentionally generic: when `dnd-5e-core` is present, it will be
    delegated; otherwise this returns a simple placeholder effect.
    """
    cast_mods = cast_mods or {}
    if HAS_DND:
        try:
            if hasattr(dnd_core, "resolve_spell"):
                return dnd_core.resolve_spell(caster, targets, spell_name, **cast_mods)
        except Exception:
            pass

    # Fallback: apply minor damage/heal to targets if they have `hp`.
    results = []
    for t in targets or []:
        if isinstance(t, dict) and "hp" in t:
            dmg = random.randint(1, 6)
            t["hp"] = max(0, int(t["hp"]) - dmg)
            results.append({"target": t, "effect": "damage", "amount": dmg})
        else:
            results.append({"target": t, "effect": "none"})
    return {"spell": spell_name, "results": results, "caster": caster}
