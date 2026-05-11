"""Tests for DataDragonClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ports.data_dragon.client import DataDragonClient


@pytest.fixture
def client() -> DataDragonClient:
    return DataDragonClient()


class TestDataDragonClient:
    """Tests for DataDragonClient methods."""

    @pytest.mark.asyncio
    async def test_get_versions_returns_list(self, client: DataDragonClient) -> None:
        """Returns a list of version strings."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = ["14.10.1", "14.9.2", "14.8.1"]

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            result = await client.get_versions()

            assert result == ["14.10.1", "14.9.2", "14.8.1"]
            mock_client.get.assert_called_once_with(
                "https://ddragon.leagueoflegends.com/api/versions.json"
            )

    @pytest.mark.asyncio
    async def test_get_latest_version_returns_first(self, client: DataDragonClient) -> None:
        """Returns the first (newest) version."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = ["14.10.1", "14.9.2"]

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            result = await client.get_latest_version()
            assert result == "14.10.1"

    @pytest.mark.asyncio
    async def test_get_latest_version_raises_on_empty(self, client: DataDragonClient) -> None:
        """Raises RuntimeError when versions list is empty."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            with pytest.raises(RuntimeError, match="empty"):
                await client.get_latest_version()

    @pytest.mark.asyncio
    async def test_get_set_data_builds_correct_url(self, client: DataDragonClient) -> None:
        """Builds correct URL with version."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"sets": {"set13": {"name": "Fortune"}}}

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            result = await client.get_set_data("14.10.1")

            mock_client.get.assert_called_once_with(
                "https://ddragon.leagueoflegends.com/cdn/14.10.1/data/en_US/tft-set.json"
            )
            assert result["sets"]["set13"]["name"] == "Fortune"

    @pytest.mark.asyncio
    async def test_get_champions_builds_correct_url(self, client: DataDragonClient) -> None:
        """Builds correct URL for champions endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {"TFT8_Ahri": {"name": "Ahri"}}}

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            result = await client.get_champions("14.10.1")

            mock_client.get.assert_called_once_with(
                "https://ddragon.leagueoflegends.com/cdn/14.10.1/data/en_US/tft-champion.json"
            )
            assert "TFT8_Ahri" in result["data"]

    @pytest.mark.asyncio
    async def test_get_items_builds_correct_url(self, client: DataDragonClient) -> None:
        """Builds correct URL for items endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {}}

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            await client.get_items("14.10.1")

            mock_client.get.assert_called_once_with(
                "https://ddragon.leagueoflegends.com/cdn/14.10.1/data/en_US/tft-item.json"
            )

    @pytest.mark.asyncio
    async def test_get_augments_builds_correct_url(self, client: DataDragonClient) -> None:
        """Builds correct URL for augments endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {}}

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            await client.get_augments("14.10.1")

            mock_client.get.assert_called_once_with(
                "https://ddragon.leagueoflegends.com/cdn/14.10.1/data/en_US/tft-augments.json"
            )

    @pytest.mark.asyncio
    async def test_get_traits_builds_correct_url(self, client: DataDragonClient) -> None:
        """Builds correct URL for traits endpoint."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": {}}

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_get.return_value = mock_client

            await client.get_traits("14.10.1")

            mock_client.get.assert_called_once_with(
                "https://ddragon.leagueoflegends.com/cdn/14.10.1/data/en_US/tft-trait.json"
            )

    @pytest.mark.asyncio
    async def test_fetch_json_retries_on_5xx(self, client: DataDragonClient) -> None:
        """Retries once on 5xx responses."""
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 503

        mock_resp_ok = MagicMock()
        mock_resp_ok.status_code = 200
        mock_resp_ok.json.return_value = {"data": {}}

        with patch.object(client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [mock_resp_fail, mock_resp_ok]
            mock_get.return_value = mock_client

            result = await client._fetch_json("https://example.com/test")

            assert result == {"data": {}}
            assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_close_safe_when_not_initialized(self, client: DataDragonClient) -> None:
        """close() does not raise when client was never initialized."""
        await client.close()
