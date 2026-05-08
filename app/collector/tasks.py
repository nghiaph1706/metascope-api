"""Celery app configuration and task definitions.

Celery Beat schedule và task registry cho background jobs.
"""

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
)

# TODO: add beat schedule when tasks are implemented
# celery_app.conf.beat_schedule = { ... }
