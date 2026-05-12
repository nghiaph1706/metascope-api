"""Tests for match jobs (Celery tasks)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.match import jobs


class TestCollectNewMatches:
    """Tests for collect_new_matches task."""

    def test_returns_empty_when_no_seed_puuids(self) -> None:
        """Returns empty result when SEED_PUUIDS is not configured."""
        with patch("app.match.jobs.settings") as mock_settings:
            mock_settings.seed_puuids = ""
            result = jobs.collect_new_matches()

        assert result["collected"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0


class TestGetSeedPuuids:
    """Tests for _get_seed_puuids helper."""

    def test_parses_comma_separated_puuids(self) -> None:
        """Splits comma-separated PUUIDs into list."""
        with patch("app.match.jobs.settings") as mock_settings:
            mock_settings.seed_puuids = "uuid1,uuid2,uuid3"
            result = jobs._get_seed_puuids()

        assert result == ["uuid1", "uuid2", "uuid3"]

    def test_strips_whitespace(self) -> None:
        """Strips whitespace from PUUIDs."""
        with patch("app.match.jobs.settings") as mock_settings:
            mock_settings.seed_puuids = " uuid1 , uuid2 "
            result = jobs._get_seed_puuids()

        assert result == ["uuid1", "uuid2"]

    def test_returns_empty_list_when_not_configured(self) -> None:
        """Returns empty list when seed_puuids is empty."""
        with patch("app.match.jobs.settings") as mock_settings:
            mock_settings.seed_puuids = ""
            result = jobs._get_seed_puuids()

        assert result == []

    def test_ignores_empty_segments(self) -> None:
        """Ignores empty strings between commas."""
        with patch("app.match.jobs.settings") as mock_settings:
            mock_settings.seed_puuids = "uuid1,,uuid2,,uuid3"
            result = jobs._get_seed_puuids()

        assert result == ["uuid1", "uuid2", "uuid3"]


class TestCollectNewMatchesAsync:
    """Tests for _collect_new_matches async function."""

    @pytest.mark.asyncio
    async def test_logs_warning_when_no_seed_puuids(self) -> None:
        """Logs warning and returns zeros when no seed PUUIDs configured."""
        with patch("app.match.jobs._get_seed_puuids") as mock_get_seed:
            mock_get_seed.return_value = []
            with patch("app.match.jobs.log") as mock_log:
                result = await jobs._collect_new_matches()

        assert result["collected"] == 0
        assert result["skipped"] == 0
        assert result["errors"] == 0
        mock_log.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_collects_matches_for_seed_puuids(self) -> None:
        """Collects matches for each seed PUUID."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cm.__aexit__ = AsyncMock()

        mock_riot = MagicMock()
        mock_riot.get_match_ids = AsyncMock(return_value=["match1", "match2"])
        mock_riot.close = AsyncMock()

        mock_fetch = AsyncMock(side_effect=[True, True])
        mock_cache_delete = AsyncMock()

        with patch("app.match.jobs._get_seed_puuids", return_value=["test-puuid"]):
            with patch("app.match.jobs.RiotClient", return_value=mock_riot):
                with patch("app.match.jobs.async_session_factory", return_value=mock_session_cm):
                    with patch("app.match.jobs.service.fetch_and_store_match", mock_fetch):
                        with patch("app.match.jobs.cache.cache_delete", mock_cache_delete):
                            result = await jobs._collect_new_matches()

        assert result["collected"] == 2
        assert result["skipped"] == 0
        assert result["errors"] == 0

    @pytest.mark.asyncio
    async def test_skips_existing_matches(self) -> None:
        """Skips matches that already exist in DB."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cm.__aexit__ = AsyncMock()

        mock_riot = MagicMock()
        mock_riot.get_match_ids = AsyncMock(return_value=["match1"])
        mock_riot.close = AsyncMock()

        mock_fetch = AsyncMock(return_value=False)  # Already exists

        with patch("app.match.jobs._get_seed_puuids", return_value=["test-puuid"]):
            with patch("app.match.jobs.RiotClient", return_value=mock_riot):
                with patch("app.match.jobs.async_session_factory", return_value=mock_session_cm):
                    with patch("app.match.jobs.service.fetch_and_store_match", mock_fetch):
                        result = await jobs._collect_new_matches()

        assert result["collected"] == 0
        assert result["skipped"] == 1

    @pytest.mark.asyncio
    async def test_handles_errors_gracefully(self) -> None:
        """Increments error count when exception occurs during collection."""
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_cm.__aexit__ = AsyncMock()

        mock_riot = MagicMock()
        mock_riot.get_match_ids = AsyncMock(return_value=["match1"])
        mock_riot.close = AsyncMock()

        mock_fetch = AsyncMock(side_effect=Exception("API Error"))
        mock_log = MagicMock()

        with patch("app.match.jobs._get_seed_puuids", return_value=["test-puuid"]):
            with patch("app.match.jobs.RiotClient", return_value=mock_riot):
                with patch("app.match.jobs.async_session_factory", return_value=mock_session_cm):
                    with patch("app.match.jobs.service.fetch_and_store_match", mock_fetch):
                        with patch("app.match.jobs.cache.cache_delete", AsyncMock()):
                            with patch("app.match.jobs.log", mock_log):
                                result = await jobs._collect_new_matches()

        assert result["errors"] == 1
        mock_log.error.assert_called_once()
