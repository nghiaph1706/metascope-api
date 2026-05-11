"""Celery app instance with autodiscovery."""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "metascope",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "check-and-refresh-static-data-every-hour": {
            "task": "meta.check_and_refresh_static_data",
            "schedule": 3600.0,  # every hour
        },
        "check-and-refresh-static-data-every-30-min": {
            "task": "meta.check_and_refresh_static_data",
            "schedule": 1800.0,  # every 30 min during active patches
        },
    },
)

celery_app.autodiscover_tasks(
    [
        "app.player",
        "app.match",
        "app.meta",
        "app.composition",
        "app.analysis",
        "app.leaderboard",
        "app.patch_notes",
    ]
)
