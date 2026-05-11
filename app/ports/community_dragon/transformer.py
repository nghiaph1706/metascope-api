"""Transform Community Dragon JSON responses to model-compatible dicts."""

from typing import Any


def transform_champion(raw: dict[str, Any], set_number: int, patch: str) -> dict[str, Any] | None:
    """Transform a champion entry from Community Dragon to Champion model dict.

    Community Dragon provides: ability, cost, stats (hp, damage, armor, etc.),
    and trait apiNames. These are not available from DataDragon CDN.
    Returns None if the champion has no name (placeholder entry).
    """
    name = raw.get("name")
    if not name:  # Skip champions with no name (placeholder entries)
        return None

    traits = raw.get("traits", [])
    ability = raw.get("ability", {})
    stats = raw.get("stats", {})

    return {
        "unit_id": raw.get("apiName", raw.get("characterName", "")),
        "name": name,
        "cost": raw.get("cost", 0),
        "traits": traits,
        "ability_name": ability.get("name") if isinstance(ability, dict) else None,
        "ability_desc": ability.get("desc") if isinstance(ability, dict) else None,
        "stats": {
            "hp": stats.get("hp"),
            "damage": stats.get("damage"),
            "armor": stats.get("armor"),
            "magic_resist": stats.get("magicResist"),
            "attack_speed": stats.get("attackSpeed"),
            "crit_chance": stats.get("critChance"),
            "crit_multiplier": stats.get("critMultiplier"),
            "mana": stats.get("mana"),
            "initial_mana": stats.get("initialMana"),
            "range": stats.get("range"),
        },
        "tft_set_number": set_number,
        "patch_added": patch,
        "is_active": True,
    }


def transform_item(raw: dict[str, Any], set_number: int | None) -> dict[str, Any] | None:
    """Transform an item entry from Community Dragon to Item model dict.

    Community Dragon provides: composition (recipe), effects (stat bonuses),
    desc, is unique item, etc.
    Returns None if the item has no apiName or name.
    """
    api_name = raw.get("apiName")
    name = raw.get("name")
    if not api_name or not name:
        return None

    return {
        "item_id": api_name,
        "name": name[:100] if len(name) > 100 else name,
        "description": raw.get("desc"),
        "icon": raw.get("icon"),
        "is_component": bool(raw.get("from")) and not raw.get("composition"),
        "is_craftable": bool(raw.get("composition")),
        "is_embleme": "Emblem" in name or raw.get("unique", False),
        "is_spatula": "Spatula" in name,
        "composition": raw.get("composition", []) or [],
        "stats": raw.get("effects", {}),
        "tft_set_number": set_number,
        "is_active": True,
    }


def transform_augment(raw: dict[str, Any], set_number: int | None) -> dict[str, Any]:
    """Transform an augment entry from Community Dragon to Augment model dict.

    Community Dragon provides: description, associatedTraits, tier, etc.
    """
    return {
        "augment_id": raw.get("apiName", ""),
        "name": raw.get("name", ""),
        "description": raw.get("desc"),
        "tier": raw.get("tier", 1),
        "icon": raw.get("icon"),
        "tft_set_number": set_number,
        "is_active": True,
    }


def transform_trait(raw: dict[str, Any], set_number: int) -> dict[str, Any]:
    """Transform a trait entry from Community Dragon to Trait model dict.

    Community Dragon provides: desc, breakpoints via effects[].thresholds.
    """
    effects = raw.get("effects", [])
    thresholds: list[dict[str, Any]] = []
    for effect in effects:
        if isinstance(effect, dict):
            thresholds.extend(effect.get("thresholds", []))

    return {
        "trait_id": raw.get("apiName", ""),
        "name": raw.get("name", ""),
        "description": raw.get("desc"),
        "tft_set_number": set_number,
        "breakpoints": thresholds,
        "is_active": True,
    }
