"""Static data refresh Celery tasks with auto-version detection."""

from typing import Any

from celery import Task

from app.core import cache
from app.core.celery import celery_app
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.core.redis import redis_client
from app.meta.seed_service import seed_all
from app.meta.seed_service_cdragon import seed_from_community_dragon
from app.ports.community_dragon.client import CommunityDragonClient
from app.ports.data_dragon.client import DataDragonClient

log = get_logger(__name__)

REDIS_KEY_DDRAGON_VERSION = "metascope:datadragon_version"
REDIS_KEY_CDRAGON_SET = "metascope:cdragon_set_number"


@celery_app.task(name="meta.check_and_refresh_static_data", bind=True)  # type: ignore[misc]
def check_and_refresh_static_data(self: Task) -> dict[str, Any]:
    """Check for new TFT versions and refresh static data if needed.

    Compares current cached version with DataDragon/Community Dragon.
    Triggers seed if a new patch/set is detected.
    """
    import asyncio

    return asyncio.run(_check_and_refresh())


async def _check_and_refresh() -> dict[str, Any]:
    """Async version check and refresh logic."""
    results = {}

    # ── DataDragon version check ───────────────────────────────
    try:
        dd_client = DataDragonClient()
        latest_dd_version = await dd_client.get_latest_version()
        await dd_client.close()

        cached_dd = await redis_client.get(REDIS_KEY_DDRAGON_VERSION)
        if cached_dd != latest_dd_version:
            log.info("new_datadragon_version_detected", cached=cached_dd, latest=latest_dd_version)
            result = await _refresh_datadragon(latest_dd_version)
            results["datadragon"] = result
            await redis_client.set(REDIS_KEY_DDRAGON_VERSION, latest_dd_version)
        else:
            log.info("datadragon_version_unchanged", version=latest_dd_version)
            results["datadragon"] = {"status": "unchanged", "version": latest_dd_version}
    except Exception as exc:
        log.error("datadragon_version_check_failed", error=str(exc))
        results["datadragon"] = {"status": "error", "error": str(exc)}

    # ── Community Dragon set check ────────────────────────────
    try:
        cd_client = CommunityDragonClient()
        latest_cd_set = await cd_client.get_latest_set_number()
        await cd_client.close()

        cached_cd = await redis_client.get(REDIS_KEY_CDRAGON_SET)
        cached_cd_int = int(cached_cd) if cached_cd else 0
        if latest_cd_set > cached_cd_int:
            log.info("new_cdragon_set_detected", cached=cached_cd_int, latest=latest_cd_set)
            result = await _refresh_cdragon(latest_cd_set)
            results["community_dragon"] = result
            await redis_client.set(REDIS_KEY_CDRAGON_SET, str(latest_cd_set))
        else:
            log.info("cdragon_set_unchanged", set_number=latest_cd_set)
            results["community_dragon"] = {"status": "unchanged", "set": latest_cd_set}
    except Exception as exc:
        log.error("cdragon_version_check_failed", error=str(exc))
        results["community_dragon"] = {"status": "error", "error": str(exc)}

    return results


async def _refresh_datadragon(version: str) -> dict[str, Any]:
    """Refresh DataDragon static data."""
    client = DataDragonClient()
    try:
        async with async_session_factory() as session:
            result = await seed_all(client, session)
        await cache.cache_delete_pattern("metascope:game:*")
        log.info("celery_datadragon_refresh_complete", **result)
        return {"status": "refreshed", "version": version, **result}
    except Exception as exc:
        log.error("celery_datadragon_refresh_failed", error=str(exc))
        raise
    finally:
        await client.close()


async def _refresh_cdragon(set_number: int) -> dict[str, Any]:
    """Refresh Community Dragon static data."""
    client = CommunityDragonClient()
    try:
        async with async_session_factory() as session:
            result = await seed_from_community_dragon(client, session)
        await cache.cache_delete_pattern("metascope:game:*")
        log.info("celery_cdragon_refresh_complete", **result)
        return {"status": "refreshed", "set": set_number, **result}
    except Exception as exc:
        log.error("celery_cdragon_refresh_failed", error=str(exc))
        raise
    finally:
        await client.close()


# Legacy task name for backwards compatibility
@celery_app.task(name="meta.refresh_static_data", bind=True)  # type: ignore[misc]
def refresh_static_data(self: Task) -> dict[str, Any]:
    """Refresh static data from DataDragon (legacy task).

    Use meta.check_and_refresh_static_data for version-aware auto-refresh.
    """
    import asyncio

    return asyncio.run(_refresh_datadragon("unknown"))


async def _refresh_static_data() -> dict[str, Any]:
    """Async implementation of legacy static data refresh."""
    client = DataDragonClient()
    try:
        async with async_session_factory() as session:
            result = await seed_all(client, session)
        log.info("celery_datadragon_refresh_complete", **result)
        return result
    except Exception as exc:
        log.error("celery_datadragon_refresh_failed", error=str(exc))
        raise
    finally:
        await client.close()
