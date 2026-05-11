"""Seed static data from CDN sources.

Usage:
    python -m app.scripts.seed                    # DataDragon (basic, always works)
    python -m app.scripts.seed --source=cdragon   # Community Dragon (complete data)
    python -m app.scripts.seed --source=all       # Both sources
    python -m app.scripts.seed --check-version    # Check for new version only
"""

import argparse
import asyncio
import sys

from app.core.database import async_session_factory
from app.core.logging import get_logger, setup_logging
from app.meta.seed_service import seed_all as seed_datadragon
from app.meta.seed_service_cdragon import seed_from_community_dragon
from app.ports.community_dragon.client import CommunityDragonClient
from app.ports.data_dragon.client import DataDragonClient

setup_logging()
log = get_logger(__name__)


async def check_version() -> None:
    """Check which versions are available from both sources."""
    print("=== Version Check ===\n")

    # DataDragon
    dd_client = DataDragonClient()
    try:
        dd_version = await dd_client.get_latest_version()
        print(f"DataDragon latest: {dd_version}")
    except Exception as e:
        print(f"DataDragon: ERROR - {e}")
    finally:
        await dd_client.close()

    # Community Dragon
    cd_client = CommunityDragonClient()
    try:
        cd_set = await cd_client.get_latest_set_number()
        print(f"Community Dragon latest set: {cd_set}")
    except Exception as e:
        print(f"Community Dragon: ERROR - {e}")
    finally:
        await cd_client.close()


async def seed_datadragon_cli() -> None:
    """Seed from DataDragon (basic, minimal data)."""
    log.info("seed_cli_start", source="datadragon")
    client = DataDragonClient()
    try:
        async with async_session_factory() as session:
            result = await seed_datadragon(client, session)
        log.info("seed_cli_complete", **result)
        print(
            f"Seeded from DataDragon: {result['champions']} champions, "
            f"{result['items']} items, {result['augments']} augments, "
            f"{result['traits']} traits"
        )
    except Exception as exc:
        log.error("seed_cli_failed", error=str(exc))
        print(f"Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


async def seed_cdragon_cli() -> None:
    """Seed from Community Dragon (complete data)."""
    log.info("seed_cli_start", source="communitydragon")
    client = CommunityDragonClient()
    try:
        async with async_session_factory() as session:
            result = await seed_from_community_dragon(client, session)
        log.info("seed_cli_complete", **result)
        print(
            f"Seeded from Community Dragon: {result['champions']} champions, "
            f"{result['items']} items, {result['augments']} augments, "
            f"{result['traits']} traits"
        )
    except Exception as exc:
        log.error("seed_cli_failed", error=str(exc))
        print(f"Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await client.close()


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed static TFT data from CDN")
    parser.add_argument(
        "--source",
        choices=["datadragon", "cdragon", "all"],
        default="cdragon",
        help="CDN source to use (default: cdragon)",
    )
    parser.add_argument(
        "--check-version",
        action="store_true",
        help="Check available versions and exit",
    )
    parser.add_argument(
        "--pbe",
        action="store_true",
        help="Use PBE (public beta environment) data",
    )
    args = parser.parse_args()

    if args.check_version:
        await check_version()
        sys.exit(0)

    if args.source == "datadragon":
        await seed_datadragon_cli()
    elif args.source == "cdragon":
        await seed_cdragon_cli()
    elif args.source == "all":
        await seed_datadragon_cli()
        print()
        await seed_cdragon_cli()


if __name__ == "__main__":
    asyncio.run(main())
