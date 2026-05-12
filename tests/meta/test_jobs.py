"""Tests for meta jobs (Celery tasks)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.meta import jobs


class TestRefreshCdragon:
    """Tests for _refresh_cdragon helper."""

    @pytest.mark.asyncio
    async def test_seeds_and_clears_cache(self) -> None:
        """Seeds data and clears game cache on refresh."""
        mock_session_cm = MagicMock()
        mock_session = AsyncMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock()

        mock_client = MagicMock()
        mock_client.close = AsyncMock()

        async def mock_seed(client, session):
            return {"traits": 5}

        async def mock_cache_delete(pattern):
            pass

        with patch("app.meta.jobs.CommunityDragonClient", return_value=mock_client):
            with patch("app.meta.jobs.seed_from_community_dragon", side_effect=mock_seed):
                with patch("app.meta.jobs.async_session_factory", return_value=mock_session_cm):
                    with patch(
                        "app.meta.jobs.cache.cache_delete_pattern", side_effect=mock_cache_delete
                    ):
                        result = await jobs._refresh_cdragon(13)

        assert result["status"] == "refreshed"
        assert result["set"] == 13


class TestCheckAndRefreshAsync:
    """Tests for _check_and_refresh async function."""

    @pytest.mark.asyncio
    async def test_detects_new_datadragon_version(self) -> None:
        """Detects and refreshes when DataDragon version changes."""
        mock_dd = MagicMock()
        mock_dd.get_latest_version = AsyncMock(return_value="14.2.0")
        mock_dd.close = AsyncMock()

        async def mock_refresh_datadragon(version):
            return {"status": "refreshed", "version": version}

        with patch("app.meta.jobs.DataDragonClient", return_value=mock_dd):
            with patch("app.meta.jobs.redis_client") as mock_redis:
                mock_redis.get = AsyncMock(side_effect=["14.1.0", None])
                mock_redis.set = AsyncMock()

                with patch(
                    "app.meta.jobs._refresh_datadragon", side_effect=mock_refresh_datadragon
                ):
                    result = await jobs._check_and_refresh()

        assert result["datadragon"]["status"] == "refreshed"
        assert result["datadragon"]["version"] == "14.2.0"

    @pytest.mark.asyncio
    async def test_reports_unchanged_when_version_same(self) -> None:
        """Reports unchanged when cached version matches latest."""
        mock_dd = MagicMock()
        mock_dd.get_latest_version = AsyncMock(return_value="14.1.0")
        mock_dd.close = AsyncMock()

        with patch("app.meta.jobs.DataDragonClient", return_value=mock_dd):
            with patch("app.meta.jobs.redis_client") as mock_redis:
                mock_redis.get = AsyncMock(return_value="14.1.0")

                with patch("app.meta.jobs._refresh_datadragon") as mock_refresh:
                    result = await jobs._check_and_refresh()

        assert result["datadragon"]["status"] == "unchanged"
        mock_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_datadragon_error(self) -> None:
        """Handles DataDragon version check errors gracefully."""
        mock_dd = MagicMock()
        mock_dd.get_latest_version = AsyncMock(side_effect=Exception("Network error"))
        mock_dd.close = AsyncMock()

        with patch("app.meta.jobs.DataDragonClient", return_value=mock_dd):
            with patch("app.meta.jobs.redis_client"):
                with patch("app.meta.jobs._refresh_datadragon"):
                    result = await jobs._check_and_refresh()

        assert result["datadragon"]["status"] == "error"
        assert "Network error" in result["datadragon"]["error"]

    @pytest.mark.asyncio
    async def test_detects_new_cdragon_set(self) -> None:
        """Detects and refreshes when Community Dragon set number increases."""
        mock_cd = MagicMock()
        mock_cd.get_latest_set_number = AsyncMock(return_value=14)
        mock_cd.close = AsyncMock()

        async def mock_refresh_cdragon(set_number):
            return {"status": "refreshed", "set": set_number}

        with patch("app.meta.jobs.CommunityDragonClient", return_value=mock_cd):
            with patch("app.meta.jobs.redis_client") as mock_redis:
                mock_redis.get = AsyncMock(side_effect=[None, "13"])
                mock_redis.set = AsyncMock()

                with patch("app.meta.jobs._refresh_cdragon", side_effect=mock_refresh_cdragon):
                    result = await jobs._check_and_refresh()

        assert result["community_dragon"]["status"] == "refreshed"
        assert result["community_dragon"]["set"] == 14

    @pytest.mark.asyncio
    async def test_handles_cdragon_error(self) -> None:
        """Handles Community Dragon set check errors gracefully."""
        mock_cd = MagicMock()
        mock_cd.get_latest_set_number = AsyncMock(side_effect=Exception("CDragon error"))
        mock_cd.close = AsyncMock()

        with patch("app.meta.jobs.CommunityDragonClient", return_value=mock_cd):
            with patch("app.meta.jobs.redis_client"):
                with patch("app.meta.jobs._refresh_datadragon"):
                    result = await jobs._check_and_refresh()

        assert result["community_dragon"]["status"] == "error"
        assert "CDragon error" in result["community_dragon"]["error"]
