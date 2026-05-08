"""Tests for RiotClient — rate limiting, retry, error handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import RiotAPIError, RiotAPIKeyInvalidError, RiotRateLimitError
from app.ports.riot.client import RiotClient


@pytest.fixture
def riot_client() -> RiotClient:
    """Fresh RiotClient instance."""
    return RiotClient()


def _mock_response(status_code: int, json_data: dict | list | None = None, headers: dict | None = None) -> MagicMock:
    """Helper to create mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    return resp


class TestRiotClientRateLimit:
    """Tests cho rate limiting behaviour."""

    @pytest.mark.asyncio
    async def test_rate_limit_retry_on_429(self, riot_client: RiotClient) -> None:
        """Client retries on 429 then succeeds."""
        responses = [
            _mock_response(429, headers={"Retry-After": "1"}),
            _mock_response(200, {"puuid": "test"}),
        ]

        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.side_effect = responses
            mock_get.return_value = mock_client

            result = await riot_client.get_account_by_puuid("test")

        assert result["puuid"] == "test"
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retry_raises_rate_limit_error(self, riot_client: RiotClient) -> None:
        """After max retries on 429, raises RiotRateLimitError."""
        responses = [
            _mock_response(429, headers={"Retry-After": "1"})
            for _ in range(riot_client._max_retries + 1)
        ]

        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.side_effect = responses
            mock_get.return_value = mock_client

            with pytest.raises(RiotRateLimitError):
                await riot_client.get_account_by_puuid("test")


class TestRiotClientErrors:
    """Tests cho error handling."""

    @pytest.mark.asyncio
    async def test_403_raises_invalid_key(self, riot_client: RiotClient) -> None:
        """403 raises RiotAPIKeyInvalidError."""
        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(403)
            mock_get.return_value = mock_client

            with pytest.raises(RiotAPIKeyInvalidError):
                await riot_client.get_account_by_riot_id("Test", "VN2")

    @pytest.mark.asyncio
    async def test_401_raises_invalid_key(self, riot_client: RiotClient) -> None:
        """401 also raises RiotAPIKeyInvalidError."""
        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(401)
            mock_get.return_value = mock_client

            with pytest.raises(RiotAPIKeyInvalidError):
                await riot_client.get_account_by_riot_id("Test", "VN2")

    @pytest.mark.asyncio
    async def test_404_returns_empty_dict(self, riot_client: RiotClient) -> None:
        """404 returns {} instead of raising."""
        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(404)
            mock_get.return_value = mock_client

            result = await riot_client.get_account_by_riot_id("Nobody", "XX1")

        assert result == {}

    @pytest.mark.asyncio
    async def test_500_raises_riot_api_error(self, riot_client: RiotClient) -> None:
        """5xx raises RiotAPIError."""
        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(500)
            mock_get.return_value = mock_client

            with pytest.raises(RiotAPIError):
                await riot_client.get_account_by_riot_id("Test", "VN2")


class TestRiotClientMethods:
    """Tests cho API methods."""

    @pytest.mark.asyncio
    async def test_get_account_by_riot_id_success(self, riot_client: RiotClient) -> None:
        """Returns account data on success."""
        data = {"puuid": "abc", "gameName": "Player", "tagLine": "VN2"}

        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200, data)
            mock_get.return_value = mock_client

            result = await riot_client.get_account_by_riot_id("Player", "VN2")

        assert result["puuid"] == "abc"

    @pytest.mark.asyncio
    async def test_get_match_ids_returns_list(self, riot_client: RiotClient) -> None:
        """Returns list of match IDs."""
        ids = ["VN2_1", "VN2_2", "VN2_3"]

        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200, ids)
            mock_get.return_value = mock_client

            result = await riot_client.get_match_ids("test-puuid", count=3)

        assert result == ids

    @pytest.mark.asyncio
    async def test_get_match_detail_success(self, riot_client: RiotClient, sample_match_response: dict) -> None:
        """Returns full match dict."""
        with patch.object(riot_client, "_get_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get.return_value = _mock_response(200, sample_match_response)
            mock_get.return_value = mock_client

            result = await riot_client.get_match_detail("VN2_123456789")

        assert result["metadata"]["match_id"] == "VN2_123456789"
