"""Tests for match service."""

from datetime import datetime
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


class TestCalcNextCursor:
    """Tests for _calc_next_cursor."""

    def test_none_when_fewer_results_than_count(self) -> None:
        """Returns None if matches length <= count (no more pages)."""
        mock_matches = [MagicMock(game_datetime=datetime(2026, 5, i)) for i in range(1, 11)]
        result = service._calc_next_cursor(mock_matches, 20)
        assert result is None

    def test_returns_cursor_when_more_results_exist(self) -> None:
        """Returns ISO datetime of 20th match when 24 matches returned with count=20."""
        mock_matches = [MagicMock(game_datetime=datetime(2026, 5, i)) for i in range(1, 25)]
        result = service._calc_next_cursor(mock_matches, 20)
        expected = datetime(2026, 5, 20).isoformat()
        assert result == expected

    def test_returns_cursor_when_exactly_count_plus_one(self) -> None:
        """Returns cursor when count+1 results (indicates more pages)."""
        # Query returns 22 matches, service checks if 22 > 21
        mock_matches = [MagicMock(game_datetime=datetime(2026, 5, i)) for i in range(1, 23)]
        result = service._calc_next_cursor(mock_matches, 21)
        assert result == datetime(2026, 5, 21).isoformat()


class TestGetMatchHistory:
    """Tests for get_match_history with cursor pagination."""

    @pytest.mark.asyncio
    async def test_returns_matches_with_cursor(self) -> None:
        """Returns matches and next_cursor when more pages exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = [
            MagicMock(match_id="m1", game_datetime=datetime(2026, 5, i), participants=[])
            for i in range(1, 25)
        ]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_riot = AsyncMock()
        mock_riot.get_match_ids.return_value = [f"m{i}" for i in range(1, 101)]

        with patch.object(service, "redis_client") as mock_redis:
            mock_redis.get.return_value = None
            mock_redis.setex = AsyncMock()
            mock_redis.delete = AsyncMock()

            matches, next_cursor = await service.get_match_history(
                mock_db, "test_puuid", mock_riot, count=20, cursor=None
            )

        assert len(matches) == 24
        assert next_cursor == datetime(2026, 5, 20).isoformat()

    @pytest.mark.asyncio
    async def test_returns_none_cursor_when_no_more_pages(self) -> None:
        """Returns next_cursor=None when fewer matches than count."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.unique.return_value.all.return_value = [
            MagicMock(match_id=f"m{i}", game_datetime=datetime(2026, 5, i), participants=[])
            for i in range(1, 11)
        ]
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        mock_riot = AsyncMock()
        mock_riot.get_match_ids.return_value = [f"m{i}" for i in range(1, 21)]

        with patch.object(service, "redis_client") as mock_redis:
            mock_redis.get.return_value = None
            mock_redis.setex = AsyncMock()
            mock_redis.delete = AsyncMock()

            matches, next_cursor = await service.get_match_history(
                mock_db, "test_puuid", mock_riot, count=20, cursor=None
            )

        assert len(matches) == 10
        assert next_cursor is None
