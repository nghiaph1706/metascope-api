"""Transform Riot API JSON responses to domain models."""

from datetime import UTC, datetime
from typing import Any


def parse_patch(game_version: str) -> tuple[str, int, int]:
    """Extract patch string and major/minor from game version.

    Riot returns versions like "14.10.628.4857" — we need "14.10".
    """
    parts = game_version.split(".")
    major = int(parts[0]) if len(parts) > 0 else 0
    minor = int(parts[1]) if len(parts) > 1 else 0
    return f"{major}.{minor}", major, minor


def parse_match_response(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Transform Riot match JSON to flat dict for Match model.

    Returns None if response is empty or invalid.
    """
    if not raw or "info" not in raw or "metadata" not in raw:
        return None

    info = raw["info"]
    metadata = raw["metadata"]

    game_datetime = datetime.fromtimestamp(
        info["game_datetime"] / 1000,
        tz=UTC,
    )
    patch_str, patch_major, patch_minor = parse_patch(
        info.get("game_version", "0.0"),
    )

    return {
        "match_id": metadata["match_id"],
        "patch": patch_str,
        "patch_major": patch_major,
        "patch_minor": patch_minor,
        "game_datetime": game_datetime,
        "game_length": int(info.get("game_length", 0)),
        "game_variation": info.get("game_variation") or None,
        "queue_id": info.get("queue_id"),
        "tft_set_number": info.get("tft_set_number"),
        "tft_set_core_name": info.get("tft_set_core_name"),
        "region": metadata["match_id"].split("_")[0] if "_" in metadata["match_id"] else "unknown",
    }


def parse_participant(raw_participant: dict[str, Any]) -> dict[str, Any]:
    """Transform Riot participant JSON to flat dict for MatchParticipant."""
    return {
        "puuid": raw_participant["puuid"],
        "placement": raw_participant["placement"],
        "level": raw_participant["level"],
        "gold_left": raw_participant.get("gold_left", 0),
        "last_round": raw_participant.get("last_round"),
        "players_eliminated": raw_participant.get("players_eliminated", 0),
        "total_damage_to_players": raw_participant.get("total_damage_to_players", 0),
        "augments": raw_participant.get("augments", []),
        "traits_active": [
            {
                "name": t["name"],
                "tier_current": t.get("tier_current", 0),
                "tier_total": t.get("tier_total", 0),
                "num_units": t.get("num_units", 0),
            }
            for t in raw_participant.get("traits", [])
            if t.get("tier_current", 0) > 0
        ],
        "time_eliminated": raw_participant.get("time_eliminated"),
    }


def parse_unit(raw_unit: dict[str, Any]) -> dict[str, Any]:
    """Transform Riot unit JSON to flat dict for ParticipantUnit."""
    return {
        "unit_id": raw_unit["character_id"],
        "tier": raw_unit.get("tier", 1),
        "rarity": raw_unit.get("rarity"),
        "items": raw_unit.get("itemNames", []),
    }


def parse_account_to_player(
    account: dict[str, Any], summoner: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Combine account + summoner data into Player dict."""
    player = {
        "puuid": account["puuid"],
        "game_name": account["gameName"],
        "tag_line": account["tagLine"],
    }
    if summoner:
        player.update(
            {
                "summoner_id": summoner.get("id"),
                "account_id": summoner.get("accountId"),
                "profile_icon_id": summoner.get("profileIconId"),
                "summoner_level": summoner.get("summonerLevel"),
            }
        )
    return player
