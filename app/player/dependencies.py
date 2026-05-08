"""Player dependencies."""

from app.ports.riot.client import RiotClient

_riot_client: RiotClient | None = None


async def get_riot_client() -> RiotClient:
    """Singleton RiotClient dependency."""
    global _riot_client
    if _riot_client is None:
        _riot_client = RiotClient()
    return _riot_client
