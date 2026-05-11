"""DataDragon CDN async HTTP client — no auth, no rate limit.

Riot's DataDragon CDN provides static game data (champions, items, augments, traits)
for TFT. Unlike the live Riot API, it requires no API key and has no rate limits.
"""

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class DataDragonClient:
    """Lightweight async client for Riot's DataDragon CDN."""

    def __init__(self) -> None:
        self._base = settings.data_dragon_base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(settings.data_dragon_timeout))
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _fetch_json(self, url: str) -> dict[str, Any]:
        """Fetch JSON from URL with a single retry on 5xx."""
        client = await self._get_client()
        for attempt in range(2):
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()  # type: ignore[no-any-return]
                if resp.status_code >= 500 and attempt == 0:
                    log.warning("ddragon_5xx_retry", url=url, status=resp.status_code)
                    continue
                if resp.status_code == 403:
                    # tft-set.json is 403 on some versions - expected, not an error
                    return {}
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                if attempt == 1:
                    raise
                log.warning("ddragon_fetch_error_retry", url=url, error=str(exc))
        return {}

    # ── CDN endpoints ─────────────────────────────────────────────

    async def get_versions(self) -> list[str]:
        """Return list of DataDragon versions, newest first."""
        data = await self._fetch_json("https://ddragon.leagueoflegends.com/api/versions.json")
        return data if isinstance(data, list) else []

    async def get_latest_version(self) -> str:
        """Return the most recent DataDragon version string."""
        versions = await self.get_versions()
        if not versions:
            raise RuntimeError("DataDragon versions.json returned empty list")
        return versions[0]

    async def get_set_data(self, version: str) -> dict[str, Any]:
        """Return tft-set.json — used to determine active set number."""
        url = f"{self._base}/{version}/data/en_US/tft-set.json"
        return await self._fetch_json(url)

    async def get_champions(self, version: str) -> dict[str, Any]:
        url = f"{self._base}/{version}/data/en_US/tft-champion.json"
        return await self._fetch_json(url)

    async def get_items(self, version: str) -> dict[str, Any]:
        url = f"{self._base}/{version}/data/en_US/tft-item.json"
        return await self._fetch_json(url)

    async def get_augments(self, version: str) -> dict[str, Any]:
        url = f"{self._base}/{version}/data/en_US/tft-augments.json"
        return await self._fetch_json(url)

    async def get_traits(self, version: str) -> dict[str, Any]:
        url = f"{self._base}/{version}/data/en_US/tft-trait.json"
        return await self._fetch_json(url)
