"""Riot Games API async HTTP client with rate limiting and retry."""

import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import (
    RiotAPIError,
    RiotAPIKeyInvalidError,
    RiotRateLimitError,
)
from app.core.logging import get_logger
from app.ports.riot.rate_limiter import TokenBucketRateLimiter

log = get_logger(__name__)


class RiotClient:
    """Async client for Riot Games TFT APIs."""

    def __init__(self) -> None:
        self._headers = {"X-Riot-Token": settings.riot_api_key}
        self._rate_limiter = TokenBucketRateLimiter(
            per_second=settings.rate_limit_per_second,
            per_2min=settings.rate_limit_per_2min,
            max_concurrent=settings.rate_limit_max_concurrent,
        )
        self._max_retries = settings.rate_limit_retry_max
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, url: str) -> dict[str, Any]:
        """Make a rate-limited request with retry on 429."""
        client = await self._get_client()

        for attempt in range(self._max_retries + 1):
            await self._rate_limiter.acquire()
            try:
                response = await client.get(url)

                if response.status_code == 200:
                    return response.json()  # type: ignore[no-any-return]

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 1))
                    log.warning("riot_rate_limited", retry_after=retry_after, attempt=attempt)
                    if attempt < self._max_retries:
                        await asyncio.sleep(retry_after)
                        continue
                    raise RiotRateLimitError(retry_after=retry_after)

                if response.status_code == 403:
                    raise RiotAPIKeyInvalidError()

                if response.status_code == 401:
                    raise RiotAPIKeyInvalidError()

                if response.status_code == 404:
                    return {}

                raise RiotAPIError(
                    f"Riot API returned {response.status_code}",
                    status_code=response.status_code,
                )
            finally:
                self._rate_limiter.release()

        raise RiotAPIError("Max retries exceeded")

    # ── Account V1 (regional) ────────────────────────────────────

    async def get_account_by_riot_id(
        self,
        game_name: str,
        tag_line: str,
    ) -> dict[str, Any]:
        """Lookup account by Riot ID. Returns {} if not found."""
        url = (
            f"{settings.riot_regional_url}"
            f"/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        )
        return await self._request(url)

    async def get_account_by_puuid(self, puuid: str) -> dict[str, Any]:
        """Lookup account by PUUID. Returns {} if not found."""
        url = f"{settings.riot_regional_url}" f"/riot/account/v1/accounts/by-puuid/{puuid}"
        return await self._request(url)

    # ── TFT Summoner V1 (platform) ──────────────────────────────

    async def get_summoner_by_puuid(self, puuid: str) -> dict[str, Any]:
        """Get summoner profile (level, icon). Returns {} if not found."""
        url = f"{settings.riot_platform_url}" f"/tft/summoner/v1/summoners/by-puuid/{puuid}"
        return await self._request(url)

    # ── TFT Match V1 (regional) ─────────────────────────────────

    async def get_match_ids(
        self,
        puuid: str,
        count: int = 20,
        start: int = 0,
    ) -> list[str]:
        """Get list of match IDs for a player."""
        url = (
            f"{settings.riot_regional_url}"
            f"/tft/match/v1/matches/by-puuid/{puuid}/ids"
            f"?count={count}&start={start}"
        )
        result = await self._request(url)
        return result if isinstance(result, list) else []

    async def get_match_detail(self, match_id: str) -> dict[str, Any]:
        """Get full match details. Returns {} if not found."""
        url = f"{settings.riot_regional_url}" f"/tft/match/v1/matches/{match_id}"
        return await self._request(url)
