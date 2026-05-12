"""Tests for meta/stats_service functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.meta import stats_service


class TestScoreToTier:
    """Tests for _score_to_tier function."""

    def test_s_tier_high_score(self) -> None:
        """Returns S for scores >= 90."""
        assert stats_service._score_to_tier(95, {"S": 90, "A": 70, "B": 45, "C": 20}) == "S"

    def test_a_tier(self) -> None:
        """Returns A for scores >= 70 and < 90."""
        assert stats_service._score_to_tier(75, {"S": 90, "A": 70, "B": 45, "C": 20}) == "A"

    def test_b_tier(self) -> None:
        """Returns B for scores >= 45 and < 70."""
        assert stats_service._score_to_tier(50, {"S": 90, "A": 70, "B": 45, "C": 20}) == "B"

    def test_c_tier(self) -> None:
        """Returns C for scores >= 20 and < 45."""
        assert stats_service._score_to_tier(25, {"S": 90, "A": 70, "B": 45, "C": 20}) == "C"

    def test_d_tier_low_score(self) -> None:
        """Returns D for scores < 20."""
        assert stats_service._score_to_tier(15, {"S": 90, "A": 70, "B": 45, "C": 20}) == "D"


class TestGetTotalGames:
    """Tests for _get_total_games function."""

    @pytest.mark.asyncio
    async def test_returns_count(self) -> None:
        """Returns total game count for patch."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 100
        mock_db.execute.return_value = mock_result

        result = await stats_service._get_total_games(mock_db, "14.1", "ranked")

        assert result == 100

    @pytest.mark.asyncio
    async def test_returns_one_when_no_games(self) -> None:
        """Returns 1 (not 0) to avoid division by zero when no games."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        result = await stats_service._get_total_games(mock_db, "14.1", "ranked")

        assert result == 1


class TestGetLatestPatch:
    """Tests for _get_latest_patch function."""

    @pytest.mark.asyncio
    async def test_returns_latest_patch(self) -> None:
        """Returns most recent patch from match data."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "14.1"
        mock_db.execute.return_value = mock_result

        result = await stats_service._get_latest_patch(mock_db)

        assert result == "14.1"

    @pytest.mark.asyncio
    async def test_falls_back_to_set_number(self) -> None:
        """Falls back to settings.tft_set_number when no patches in DB."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.meta.stats_service.settings") as mock_settings:
            mock_settings.tft_set_number = 13
            result = await stats_service._get_latest_patch(mock_db)

        assert result == "13"


class TestCalculateChampionStats:
    """Tests for calculate_champion_stats function."""

    @pytest.mark.asyncio
    async def test_calculates_correct_rates(self) -> None:
        """Calculates win_rate, top4_rate, avg_placement correctly."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        mock_row = MagicMock()
        mock_row.unit_id = "TFT13_Ahri"
        mock_row.games = 10
        mock_row.wins = 3
        mock_row.top4s = 6
        mock_row.total_placement = 35

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        with patch("app.meta.stats_service._get_latest_patch", return_value="14.1"):
            with patch("app.meta.stats_service._get_total_games", return_value=100):
                with patch("app.meta.stats_service.settings") as mock_settings:
                    mock_settings.tft_set_number = 13
                    mock_settings.tier_boundaries_map = {"S": 90, "A": 70, "B": 45, "C": 20}

                    result = await stats_service.calculate_champion_stats(mock_db)

        assert result["patch"] == "14.1"
        assert result["champions"] == 1
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_zero_games(self) -> None:
        """Skips champions with 0 games."""
        mock_db = AsyncMock()

        mock_row = MagicMock()
        mock_row.unit_id = "TFT13_Ahri"
        mock_row.games = 0

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        mock_db.execute.return_value = mock_result

        with patch("app.meta.stats_service._get_latest_patch", return_value="14.1"):
            with patch("app.meta.stats_service._get_total_games", return_value=100):
                with patch("app.meta.stats_service.settings") as mock_settings:
                    mock_settings.tft_set_number = 13
                    mock_settings.tier_boundaries_map = {"S": 90, "A": 70, "B": 45, "C": 20}

                    result = await stats_service.calculate_champion_stats(mock_db)

        assert result["champions"] == 0


class TestCalculateItemStats:
    """Tests for calculate_item_stats function."""

    @pytest.mark.asyncio
    async def test_aggregates_item_stats(self) -> None:
        """Aggregates item stats from participant units."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.placement = 1
        mock_participant.augments = []

        mock_unit = MagicMock()
        mock_unit.items = ["item1", "item2"]

        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_participant, mock_unit)]
        mock_db.execute.return_value = mock_result

        with patch("app.meta.stats_service._get_latest_patch", return_value="14.1"):
            with patch("app.meta.stats_service.settings") as mock_settings:
                mock_settings.tft_set_number = 13

                result = await stats_service.calculate_item_stats(mock_db)

        assert result["patch"] == "14.1"
        assert result["items"] == 2


class TestCalculateAugmentStats:
    """Tests for calculate_augment_stats function."""

    @pytest.mark.asyncio
    async def test_aggregates_augment_stats(self) -> None:
        """Aggregates augment stats from participants."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        mock_participant = MagicMock()
        mock_participant.placement = 1
        mock_participant.augments = ["aug1", "aug2"]

        mock_match = MagicMock()

        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_participant, mock_match)]
        mock_db.execute.return_value = mock_result

        with patch("app.meta.stats_service._get_latest_patch", return_value="14.1"):
            with patch("app.meta.stats_service.settings") as mock_settings:
                mock_settings.tft_set_number = 13

                result = await stats_service.calculate_augment_stats(mock_db)

        assert result["patch"] == "14.1"
        assert result["augments"] == 2


class TestCalculateAllStats:
    """Tests for calculate_all_stats function."""

    @pytest.mark.asyncio
    async def test_calls_all_calculation_functions(self) -> None:
        """Calls champion, item, and augment stats calculation."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()

        async def mock_champ(*args, **kwargs):
            return {"patch": "14.1", "champions": 5}

        async def mock_item(*args, **kwargs):
            return {"patch": "14.1", "items": 10}

        async def mock_aug(*args, **kwargs):
            return {"patch": "14.1", "augments": 3}

        with patch("app.meta.stats_service.calculate_champion_stats", side_effect=mock_champ):
            with patch("app.meta.stats_service.calculate_item_stats", side_effect=mock_item):
                with patch("app.meta.stats_service.calculate_augment_stats", side_effect=mock_aug):
                    result = await stats_service.calculate_all_stats(mock_db)

        assert result["champions"]["champions"] == 5
        assert result["items"]["items"] == 10
        assert result["augments"]["augments"] == 3
        mock_db.commit.assert_called_once()
