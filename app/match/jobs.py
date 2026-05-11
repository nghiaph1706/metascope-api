"""Match collection Celery jobs."""

import asyncio
from typing import Any

from celery import Task  # noqa: F401

from app.core.celery import celery_app
from app.core.config import settings
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.match import service
from app.ports.riot.client import RiotClient

log = get_logger(__name__)


@celery_app.task(name="match.collect_new_matches")  # type: ignore[misc]
def collect_new_matches() -> dict[str, Any]:
    """Collect recent matches for seed players. Runs every 30 minutes."""
    return asyncio.run(_collect_new_matches())


async def _collect_new_matches() -> dict[str, Any]:
    """Async implementation of match collection."""
    seed_puuids = _get_seed_puuids()
    if not seed_puuids:
        log.warning("no_seed_puuids", msg="Set SEED_PUUIDS in .env")
        return {"collected": 0, "skipped": 0, "errors": 0}

    riot_client = RiotClient()
    collected = 0
    skipped = 0
    errors = 0

    try:
        async with async_session_factory() as db:
            for puuid in seed_puuids:
                try:
                    match_ids = await riot_client.get_match_ids(puuid, count=20)
                    for match_id in match_ids:
                        result = await service.fetch_and_store_match(db, match_id, riot_client)
                        if result:
                            collected += 1
                        else:
                            skipped += 1
                    await db.commit()
                except Exception as e:
                    log.error("collect_error", puuid=puuid[:10], error=str(e))
                    errors += 1
                    await db.rollback()
    finally:
        await riot_client.close()

    log.info("collection_complete", collected=collected, skipped=skipped, errors=errors)
    return {"collected": collected, "skipped": skipped, "errors": errors}


def _get_seed_puuids() -> list[str]:
    """Get seed PUUIDs from config or DB."""
    seed = getattr(settings, "seed_puuids", "")
    if seed:
        return [p.strip() for p in seed.split(",") if p.strip()]
    return []
