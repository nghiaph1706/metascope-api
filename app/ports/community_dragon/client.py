"""Community Dragon CDN client for complete TFT static data.

Community Dragon provides full game data including traits, abilities,
item recipes, and stats - data that DataDragon CDN omits.
"""

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class CommunityDragonClient:
    """Async client for Community Dragon's complete TFT dataset."""

    BASE_URL = "https://raw.communitydragon.org"

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, Any] | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(settings.data_dragon_timeout))
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _fetch_json(self, url: str) -> dict[str, Any]:
        """Fetch JSON from URL with retry on failure."""
        client = await self._get_client()
        for attempt in range(2):
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.json()  # type: ignore[no-any-return]
                if resp.status_code >= 500 and attempt == 0:
                    log.warning("cdragon_5xx_retry", url=url, status=resp.status_code)
                    continue
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                if attempt == 1:
                    raise
                log.warning("cdragon_fetch_error_retry", url=url, error=str(exc))
        return {}

    async def get_tft_data(self, use_pbe: bool = False) -> dict[str, Any]:
        """Fetch complete TFT dataset from Community Dragon.

        Contains champions, items, augments, traits for all sets.
        Includes full stats, abilities, item recipes, and trait breakpoints.
        """
        prefix = "pbe" if use_pbe else "latest"
        url = f"{self.BASE_URL}/{prefix}/cdragon/tft/en_us.json"
        return await self._fetch_json(url)

    async def get_latest_set_number(self, use_pbe: bool = False) -> int:
        """Return the latest active TFT set number."""
        data = await self.get_tft_data(use_pbe)
        sets = data.get("sets", {})
        if not sets:
            return 17  # fallback
        return max(int(k) for k in sets.keys())

    async def get_set_data_for_version(self, version: str, use_pbe: bool = False) -> dict[str, Any]:
        """Fetch TFT data for a specific version (e.g., '17.1')."""
        prefix = "pbe" if use_pbe else version
        url = f"{self.BASE_URL}/{prefix}/cdragon/tft/en_us.json"
        return await self._fetch_json(url)
