"""Tests for match service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.match import service


class TestFetchAndStoreMatch:
    """Tests for fetch_and_store_match."""

    @pytest.mark.asyncio
    async def test_skips_existing_match(self) -> None:
        """Returns None if match already in DB."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = MagicMock()
        mock_db.execute.return_value = mock_result

        mock_riot = AsyncMock()

        result = await service.fetch_and_store_match(mock_db, "VN2_123", mock_riot)

        assert result is None
        mock_riot.get_match_detail.assert_not_called()

    @pytest.mark.asyncio
    async def test_stores_new_match(self, sample_match_response: dict) -> None:
        """Fetches from Riot and stores match + participants + units."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        mock_riot = AsyncMock()
        mock_riot.get_match_detail.return_value = sample_match_response

        result = await service.fetch_and_store_match(mock_db, "VN2_123456789", mock_riot)

        assert result is not None
        assert result.match_id == "VN2_123456789"
        assert len(result.participants) == 1
        assert len(result.participants[0].units) == 1
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_response(self) -> None:
        """Returns None if Riot returns empty/invalid data."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        mock_riot = AsyncMock()
        mock_riot.get_match_detail.return_value = {}

        result = await service.fetch_and_store_match(mock_db, "VN2_999", mock_riot)

        assert result is None


class TestGetMatchByMatchId:
    """Tests for get_match_by_match_id."""

    @pytest.mark.asyncio
    async def test_returns_match_if_exists(self) -> None:
        """Returns match from DB."""
        mock_match = MagicMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = mock_match
        mock_db.execute.return_value = mock_result

        result = await service.get_match_by_match_id(mock_db, "VN2_123")

        assert result is mock_match

    @pytest.mark.asyncio
    async def test_returns_none_if_not_exists(self) -> None:
        """Returns None if match not in DB."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_match_by_match_id(mock_db, "VN2_999")

        assert result is None
