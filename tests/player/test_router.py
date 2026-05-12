"""Tests for player router endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestPlayerRouter:
    """Tests for /api/v1/player endpoints."""

    @pytest.mark.asyncio
    async def test_lookup_player_by_riot_id(self) -> None:
        """Looks up player by game_name and tag_line."""
        mock_player = MagicMock()
        mock_player.puuid = "test-puuid"
        mock_player.game_name = "TestPlayer"
        mock_player.tag_line = "VN2"
        mock_player.region = "vn2"

        async def mock_lookup(*args, **kwargs):
            return mock_player

        with patch("app.player.router.service.lookup_player", side_effect=mock_lookup):
            with patch("app.player.router.get_riot_client") as mock_get_riot:
                mock_riot = MagicMock()
                mock_get_riot.return_value = mock_riot

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/player/vn2/TestPlayer/VN2")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["puuid"] == "test-puuid"
        assert data["data"]["game_name"] == "TestPlayer"

    @pytest.mark.asyncio
    async def test_lookup_player_returns_404_when_not_found(self) -> None:
        """Returns 404 when player not found."""
        from app.core.exceptions import PlayerNotFoundError

        async def mock_lookup(*args, **kwargs):
            raise PlayerNotFoundError("Unknown", "Player")

        with patch("app.player.router.service.lookup_player", side_effect=mock_lookup):
            with patch("app.player.router.get_riot_client") as mock_get_riot:
                mock_riot = MagicMock()
                mock_get_riot.return_value = mock_riot

                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/player/vn2/Unknown/Player")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_player_stats(self) -> None:
        """Returns aggregated player stats."""
        from app.player.schemas import PlayerStatsResponse

        async def mock_stats(*args, **kwargs):
            return PlayerStatsResponse(
                puuid="test-puuid",
                game_name="TestPlayer",
                tag_line="VN2",
                region="vn2",
                total_matches=10,
                wins=3,
                top4s=7,
                win_rate=0.3,
                top4_rate=0.7,
                avg_placement=3.5,
                top_champions=[],
                top_augments=[],
                avg_level=8.0,
                avg_gold_left=15.0,
                avg_damage=50.0,
                patches_played=["14.1"],
            )

        with patch("app.player.router.service.get_player_stats", side_effect=mock_stats):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/player/test-puuid/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 10
        assert data["win_rate"] == 0.3

    @pytest.mark.asyncio
    async def test_get_player_analysis(self) -> None:
        """Returns player analysis with strengths/weaknesses."""
        from app.player.schemas import PlayerAnalysisResponse

        async def mock_analysis(*args, **kwargs):
            return PlayerAnalysisResponse(
                puuid="test-puuid",
                game_name="TestPlayer",
                tag_line="VN2",
                region="vn2",
                total_matches=10,
                most_played_comps=[],
                preferred_traits=["Sorcerer"],
                strengths=["Tỷ lệ thắng cao"],
                weaknesses=["Level thấp"],
                avg_level=7.0,
                avg_gold_left=25.0,
                early_game_strength=0.0,
                late_game_strength=0.0,
                avg_damage=50.0,
                patches_played=["14.1"],
                recent_trend="stable",
                advice=["Level to 8 earlier"],
            )

        with patch("app.player.router.service.get_player_analysis", side_effect=mock_analysis):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get("/api/v1/player/test-puuid/analysis")

        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 10
        assert "Sorcerer" in data["preferred_traits"]
        assert len(data["strengths"]) > 0
