"""Tests for transformer functions."""

import pytest

from app.ports.riot.transformer import (
    parse_account_to_player,
    parse_match_response,
    parse_participant,
    parse_patch,
    parse_unit,
)


class TestParsePatch:
    """Tests for patch string extraction."""

    def test_standard_version(self) -> None:
        patch, major, minor = parse_patch("14.10.628.4857")
        assert patch == "14.10"
        assert major == 14
        assert minor == 10

    def test_short_version(self) -> None:
        patch, major, minor = parse_patch("14.1")
        assert patch == "14.1"

    def test_empty_version(self) -> None:
        patch, major, minor = parse_patch("0.0")
        assert major == 0


class TestParseMatchResponse:
    """Tests for match response transformation."""

    def test_valid_match(self, sample_match_response: dict) -> None:
        result = parse_match_response(sample_match_response)
        assert result is not None
        assert result["match_id"] == "VN2_123456789"
        assert result["region"] == "VN2"
        assert result["tft_set_number"] == 13

    def test_empty_response(self) -> None:
        assert parse_match_response({}) is None
        assert parse_match_response(None) is None

    def test_missing_info(self) -> None:
        assert parse_match_response({"metadata": {}}) is None


class TestParseParticipant:
    """Tests for participant transformation."""

    def test_extracts_fields(self, sample_match_response: dict) -> None:
        raw = sample_match_response["info"]["participants"][0]
        result = parse_participant(raw)
        assert result["puuid"] == "Cst5vZKHi4Pxj_TEST"
        assert result["placement"] == 1
        assert result["level"] == 9
        assert len(result["traits_active"]) > 0

    def test_filters_inactive_traits(self, sample_match_response: dict) -> None:
        raw = sample_match_response["info"]["participants"][0]
        raw["traits"].append({"name": "Inactive", "tier_current": 0, "tier_total": 1, "num_units": 1})
        result = parse_participant(raw)
        trait_names = [t["name"] for t in result["traits_active"]]
        assert "Inactive" not in trait_names


class TestParseUnit:
    """Tests for unit transformation."""

    def test_extracts_fields(self, sample_match_response: dict) -> None:
        raw = sample_match_response["info"]["participants"][0]["units"][0]
        result = parse_unit(raw)
        assert result["unit_id"] == "TFT13_Yone"
        assert result["tier"] == 2
        assert len(result["items"]) == 2


class TestParseAccountToPlayer:
    """Tests for account+summoner merge."""

    def test_account_only(self) -> None:
        account = {"puuid": "abc", "gameName": "Player", "tagLine": "VN2"}
        result = parse_account_to_player(account)
        assert result["puuid"] == "abc"
        assert result["game_name"] == "Player"
        assert "summoner_level" not in result

    def test_with_summoner(self) -> None:
        account = {"puuid": "abc", "gameName": "Player", "tagLine": "VN2"}
        summoner = {"id": "s1", "accountId": "a1", "profileIconId": 5295, "summonerLevel": 100}
        result = parse_account_to_player(account, summoner)
        assert result["summoner_level"] == 100
        assert result["profile_icon_id"] == 5295
