"""Transform DataDragon CDN JSON responses to model-compatible dicts."""

from typing import Any


def determine_set_number(set_data: dict[str, Any], patch_major: int | None = None) -> int:
    """Return the TFT set number from tft-set.json or infer from patch major version.

    DataDragon's tft-set.json endpoint (https://.../cdn/{v}/data/en_US/tft-set.json)
    is currently returning 403 for all versions, so we fall back to inferring from patch.

    TFT set numbering aligns with patch major version (e.g., patch 14.x = Set 10,
    patch 13.x = Set 9, patch 12.x = Set 8, patch 11.x = Set 7, etc.).
    """
    sets = set_data.get("sets", {})
    numbers = [
        int(info["tft_set_number"])
        for info in sets.values()
        if info.get("tft_set_number") is not None
    ]
    if numbers:
        return max(numbers)

    if patch_major is not None:
        return patch_major - 3  # patch 16.x → set 13, patch 14.x → set 11, etc.

    return 13  # safe default


def transform_champion(raw: dict[str, Any], set_number: int, patch: str) -> dict[str, Any]:
    """Transform a champion entry from tft-champion.json to Champion model dict.

    DataDragon tft-champion.json provides minimal data: id, name, cost, tier, image.
    No traits, ability, or stats fields are present in the current CDN response.
    """
    return {
        "unit_id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "cost": raw.get("cost", 0),
        "traits": [],
        "ability_name": None,
        "ability_desc": None,
        "stats": {},
        "tft_set_number": set_number,
        "patch_added": patch,
        "is_active": True,
    }


def transform_item(raw: dict[str, Any], set_number: int | None) -> dict[str, Any]:
    """Transform an item entry from tft-item.json to Item model dict.

    DataDragon tft-item.json provides minimal data: id, name, image.
    No description, composition, or stats fields are present in the current CDN response.
    Basic items like components and consumables are available; crafted items with
    'from' (composition) and detailed stats are not available from this CDN source.
    """
    icon = raw.get("image", {})
    icon_full = icon.get("full") if isinstance(icon, dict) else None
    name = raw.get("name", "")
    if len(name) > 100:
        name = name[:100]
    return {
        "item_id": raw.get("id", ""),
        "name": name,
        "description": None,
        "icon": icon_full,
        "is_component": False,
        "is_craftable": bool(raw.get("from")),
        "is_embleme": False,
        "is_spatula": False,
        "composition": raw.get("from", []) or [],
        "stats": {},
        "tft_set_number": set_number,
        "is_active": True,
    }


def transform_augment(raw: dict[str, Any], set_number: int | None) -> dict[str, Any]:
    """Transform an augment entry from tft-augments.json to Augment model dict.

    DataDragon tft-augments.json provides: id, name, description, image.
    No tier field is present in the current CDN response - tier will default to 1.
    """
    return {
        "augment_id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "description": raw.get("description"),
        "tier": raw.get("tier", 1),
        "icon": raw.get("image", {}).get("full") if isinstance(raw.get("image"), dict) else None,
        "tft_set_number": set_number,
        "is_active": True,
    }


def transform_trait(raw: dict[str, Any], set_number: int) -> dict[str, Any]:
    """Transform a trait entry from tft-trait.json to Trait model dict."""
    effects = raw.get("effects", {})
    thresholds: list[dict[str, Any]] = []
    for effect_data in effects.values():
        if isinstance(effect_data, dict):
            thresholds.extend(effect_data.get("thresholds", []))

    return {
        "trait_id": raw.get("id", raw.get("key", "")),
        "name": raw.get("name", ""),
        "description": raw.get("description"),
        "tft_set_number": set_number,
        "breakpoints": thresholds,
        "is_active": True,
    }
