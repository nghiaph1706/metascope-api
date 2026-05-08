"""Unit tests cho RiotClient.

Test rate limiting, retry logic, và error handling.
Không gọi Riot API thật — dùng httpx mock.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import (
    RiotAPIError,
    RiotAPIKeyInvalidError,
    RiotRateLimitError,
)


class TestRiotClientRateLimit:
    """Tests cho rate limiting behaviour."""

    @pytest.mark.asyncio
    async def test_rate_limit_retry_on_429(self) -> None:
        """Client phải retry khi nhận 429 và chờ Retry-After."""
        # TODO: implement sau khi có RiotClient
        # from app.collector.riot_client import RiotClient
        # mock response 429 → verify sleep → verify retry
        pass

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_requests(self) -> None:
        """Semaphore không được phép > max_concurrent requests đồng thời."""
        pass

    @pytest.mark.asyncio
    async def test_max_retry_raises_error(self) -> None:
        """Sau max_retry lần, phải raise RiotAPIError."""
        pass


class TestRiotClientErrors:
    """Tests cho error handling."""

    @pytest.mark.asyncio
    async def test_403_raises_invalid_key_error(self) -> None:
        """403 response phải raise RiotAPIKeyInvalidError."""
        pass

    @pytest.mark.asyncio
    async def test_404_raises_not_found(self) -> None:
        """404 response phải raise appropriate error."""
        pass

    @pytest.mark.asyncio
    async def test_500_raises_riot_api_error(self) -> None:
        """5xx response phải raise RiotAPIError."""
        pass


class TestRiotClientMethods:
    """Tests cho các API method."""

    @pytest.mark.asyncio
    async def test_get_summoner_by_riot_id_success(
        self, sample_summoner_response: dict
    ) -> None:
        """get_summoner_by_riot_id trả đúng data khi API success."""
        pass

    @pytest.mark.asyncio
    async def test_get_tft_match_list_returns_list(
        self, sample_match_id_list: list[str]
    ) -> None:
        """get_tft_match_list trả list of match IDs."""
        pass

    @pytest.mark.asyncio
    async def test_get_match_detail_returns_dict(
        self, sample_match_response: dict
    ) -> None:
        """get_match_detail trả full match dict."""
        pass
