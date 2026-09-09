from celery import Celery

from app.core.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "literag",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["app.tasks.relations"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)
