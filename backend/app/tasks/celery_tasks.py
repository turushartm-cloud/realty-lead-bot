"""Celery tasks for background processing."""
from celery import Celery
from celery.schedules import crontab
from ..config import settings
import structlog

logger = structlog.get_logger()

celery_app = Celery(
    "realty_bot",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
    include=["app.tasks.celery_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True
)

celery_app.conf.beat_schedule = {
    "daily-analytics": {
        "task": "app.tasks.celery_tasks.update_daily_analytics",
        "schedule": crontab(hour=0, minute=5)
    },
    "cleanup-old-leads": {
        "task": "app.tasks.celery_tasks.archive_old_leads",
        "schedule": crontab(hour=3, minute=0)
    },
    "reset-ai-counter": {
        "task": "app.tasks.celery_tasks.reset_ai_counter",
        "schedule": 60.0
    }
}


@celery_app.task(bind=True, max_retries=3)
def process_lead_async(self, lead_data: dict):
    try:
        logger.info("Processing lead async", lead_id=lead_data.get("id"))
        return {"status": "processed"}
    except Exception as exc:
        logger.error("Lead processing failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60)


@celery_app.task
def update_daily_analytics():
    logger.info("Running daily analytics update")
    return {"status": "updated"}


@celery_app.task
def archive_old_leads(days: int = 90):
    logger.info("Archiving old leads", days=days)
    return {"status": "archived"}


@celery_app.task
def reset_ai_counter():
    return {"status": "reset"}


@celery_app.task
def send_bulk_notification(user_ids: list, message: str):
    logger.info("Sending bulk notification", count=len(user_ids))
    return {"sent": len(user_ids)}
