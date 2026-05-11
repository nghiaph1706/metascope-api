"""Tests for seed_service and DataDragon transformers."""

from app.ports.data_dragon.transformer import (
    determine_set_number,
    transform_augment,
    transform_champion,
    transform_item,
    transform_trait,
)


class TestDetermineSetNumber:
    """Tests for set number determination from tft-set.json."""

    def test_returns_highest_set_number(self) -> None:
        raw = {
            "sets": {
                "set12": {"name": "S锦", "tft_set_number": 12},
                "set13": {"name": "Fortune", "tft_set_number": 13},
                "set14": {"name": "Hypoge", "tft_set_number": 14},
            }
        }
        assert determine_set_number(raw) == 14

    def test_handles_missing_tft_set_number(self) -> None:
        raw = {"sets": {"set13": {"name": "Fortune"}}}
        assert determine_set_number(raw) == 13  # fallback to 13

    def test_empty_sets(self) -> None:
        assert determine_set_number({}) == 13

    def test_falls_back_to_patch_major(self) -> None:
        raw = {"sets": {}}
        assert determine_set_number(raw, patch_major=16) == 13
        assert determine_set_number(raw, patch_major=14) == 11


class TestTransformChampion:
    """Tests for champion transformation."""

    def test_transforms_valid_champion(self) -> None:
        raw = {
            "id": "TFT13_Ahri",
            "name": "Ahri",
            "cost": 3,
            "traits": ["Sorcerer", "Sage"],
            "ability": {"name": "Spirit Rush", "desc": "Dash and deal damage"},
            "stats": {"armor": 50, "mr": 50},
        }
        result = transform_champion(raw, 13, "14.10.1")
        assert result["unit_id"] == "TFT13_Ahri"
        assert result["name"] == "Ahri"
        assert result["cost"] == 3
        assert result["traits"] == []  # DataDragon doesn't provide traits
        assert result["ability_name"] is None  # DataDragon doesn't provide ability
        assert result["tft_set_number"] == 13
        assert result["is_active"] is True

    def test_handles_missing_ability(self) -> None:
        raw = {"id": "TFT13_Yone", "name": "Yone", "cost": 4, "traits": []}
        result = transform_champion(raw, 13, "14.10.1")
        assert result["ability_name"] is None
        assert result["ability_desc"] is None


class TestTransformItem:
    """Tests for item transformation."""

    def test_transforms_valid_item(self) -> None:
        raw = {
            "id": "TFT13_Item_Warmogs",
            "name": "Warmog's Armor",
            "description": "Grants health.",
            "image": {"full": "warmogs.tex"},
            "isComponent": True,
            "isCraftable": True,
            "isEmblem": False,
            "isSpatula": False,
            "from": ["TFT13_Item_Giant'sBelt"],
            "stats": {"health": 500},
        }
        result = transform_item(raw, 13)
        assert result["item_id"] == "TFT13_Item_Warmogs"
        assert result["name"] == "Warmog's Armor"
        assert result["is_component"] is False  # DataDragon doesn't provide this
        assert result["is_craftable"] is True
        assert result["icon"] == "warmogs.tex"

    def test_handles_long_name_truncated(self) -> None:
        raw = {"id": "TEST", "name": "A" * 150}
        result = transform_item(raw, 13)
        assert len(result["name"]) == 100
        assert result["name"] == "A" * 100


class TestTransformAugment:
    """Tests for augment transformation."""

    def test_transforms_valid_augment(self) -> None:
        raw = {
            "id": "TFT13_Augment_Salvage",
            "name": "Salvage",
            "description": "Gain gold when losing.",
            "tier": 1,
            "image": {"full": "augment.tex"},
        }
        result = transform_augment(raw, 13)
        assert result["augment_id"] == "TFT13_Augment_Salvage"
        assert result["tier"] == 1
        assert result["tft_set_number"] == 13
        assert result["icon"] == "augment.tex"


class TestTransformTrait:
    """Tests for trait transformation."""

    def test_transforms_valid_trait(self) -> None:
        raw = {
            "id": "TFT13_Trait_Sorcerer",
            "name": "Sorcerer",
            "description": "Spell damage boost",
            "effects": {
                "TFT13_Sorcerer": {
                    "thresholds": [
                        {"tier": 1, "minUnits": 2, "maxUnits": 2},
                        {"tier": 2, "minUnits": 3, "maxUnits": 3},
                        {"tier": 3, "minUnits": 5, "maxUnits": 5},
                    ]
                }
            },
        }
        result = transform_trait(raw, 13)
        assert result["trait_id"] == "TFT13_Trait_Sorcerer"
        assert len(result["breakpoints"]) == 3
        assert result["breakpoints"][0]["tier"] == 1

    def test_handles_empty_effects(self) -> None:
        raw = {"id": "TFT13_Trait_Empty", "name": "Empty", "effects": {}}
        result = transform_trait(raw, 13)
        assert result["breakpoints"] == []
