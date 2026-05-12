"""Tests for match router endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


class TestMatchRouter:
    """Tests for /api/v1/matches endpoints."""

    @pytest.mark.asyncio
    async def test_get_match_history_returns_summaries(self) -> None:
        """Returns match history with cursor pagination."""
        mock_match = MagicMock()
        mock_match.match_id = "VN2_123"
        mock_match.patch = "14.1"
        mock_match.game_datetime = datetime(2024, 1, 1)
        mock_match.game_length = 1800
        mock_match.tft_set_number = 13

        mock_participant = MagicMock()
        mock_participant.puuid = "test-puuid"
        mock_participant.placement = 1
        mock_participant.level = 9
        mock_participant.augments = ["TFT13_Augment_SpellBlade2"]
        mock_participant.units = []
        mock_match.participants = [mock_participant]

        async def mock_get_history(*args, **kwargs):
            return ([mock_match], None)

        with patch("app.match.router.service.get_match_history", side_effect=mock_get_history):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/player/test-puuid/matches",
                    params={"count": 20},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["match_id"] == "VN2_123"

    @pytest.mark.asyncio
    async def test_get_match_history_with_cursor(self) -> None:
        """Handles cursor for pagination."""

        async def mock_get_history(*args, **kwargs):
            return ([], "next-cursor-token")

        with patch("app.match.router.service.get_match_history", side_effect=mock_get_history):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as client:
                response = await client.get(
                    "/api/v1/player/test-puuid/matches",
                    params={"count": 10, "cursor": "prev-cursor"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["next_cursor"] == "next-cursor-token"

    @pytest.mark.asyncio
    async def test_get_match_detail_fetches_from_api(self) -> None:
        """Fetches match from Riot API when not in DB."""
        mock_match = MagicMock()
        mock_match.match_id = "VN2_123"
        mock_match.patch = "14.1"
        mock_match.patch_major = 14
        mock_match.patch_minor = 1
        mock_match.game_datetime = datetime(2024, 1, 1)
        mock_match.game_length = 1800
        mock_match.game_variation = None
        mock_match.queue_id = 1100
        mock_match.tft_set_number = 13
        mock_match.region = "vn2"
        mock_match.participants = []

        mock_get_by_match_id = AsyncMock(side_effect=[None, mock_match])
        mock_fetch = AsyncMock(return_value=True)

        with patch("app.match.router.service.get_match_by_match_id", mock_get_by_match_id):
            with patch("app.match.router.service.fetch_and_store_match", mock_fetch):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/matches/VN2_123")

        assert response.status_code == 200
        assert response.json()["match_id"] == "VN2_123"

    @pytest.mark.asyncio
    async def test_get_match_detail_returns_404_when_not_found(self) -> None:
        """Returns 404 when match not found anywhere."""

        async def mock_get_by_match_id(*args, **kwargs):
            return None

        async def mock_fetch(*args, **kwargs):
            return False

        with patch(
            "app.match.router.service.get_match_by_match_id", side_effect=mock_get_by_match_id
        ):
            with patch("app.match.router.service.fetch_and_store_match", side_effect=mock_fetch):
                async with AsyncClient(
                    transport=ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    response = await client.get("/api/v1/matches/NONEXISTENT")

        assert response.status_code == 404
