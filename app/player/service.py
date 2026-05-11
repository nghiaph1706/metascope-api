"""Player business logic."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.player.exceptions import PlayerNotFoundError
from app.player.models import Player
from app.ports.riot.client import RiotClient
from app.ports.riot.transformer import parse_account_to_player


async def lookup_player(
    db: AsyncSession,
    game_name: str,
    tag_line: str,
    riot_client: RiotClient,
    region: str = "vn2",
) -> Player:
    """Lookup player by Riot ID — fetch from API if not in DB or stale."""
    stmt = select(Player).where(
        Player.game_name == game_name,
        Player.tag_line == tag_line,
    )
    result = await db.execute(stmt)
    player = result.scalars().first()

    if player and _is_fresh(player):
        return player

    account = await riot_client.get_account_by_riot_id(game_name, tag_line)
    if not account:
        raise PlayerNotFoundError(game_name, tag_line)

    summoner = await riot_client.get_summoner_by_puuid(account["puuid"])
    player_data = parse_account_to_player(account, summoner or None)

    if player:
        for key, value in player_data.items():
            setattr(player, key, value)
        player.last_fetched_at = datetime.now(UTC)
    else:
        existing = await db.execute(select(Player).where(Player.puuid == player_data["puuid"]))
        player = existing.scalars().first()
        if player:
            for key, value in player_data.items():
                setattr(player, key, value)
            player.last_fetched_at = datetime.now(UTC)
        else:
            player = Player(
                **player_data,
                region=region,
                last_fetched_at=datetime.now(UTC),
            )
            db.add(player)
            return player

    return player


async def get_player_by_puuid(
    db: AsyncSession,
    puuid: str,
) -> Player | None:
    """Get player from DB by PUUID."""
    stmt = select(Player).where(Player.puuid == puuid)
    result = await db.execute(stmt)
    return result.scalars().first()


def _is_fresh(player: Player, max_age_seconds: int = 1800) -> bool:
    """Check if player data is recent enough (default 30 min)."""
    if not player.last_fetched_at:
        return False
    age = (datetime.now(UTC) - player.last_fetched_at.replace(tzinfo=UTC)).total_seconds()
    return age < max_age_seconds
