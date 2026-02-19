"""Celery application configuration with 4-priority queues and Beat schedule."""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "sns_solution",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Seoul",
    enable_utc=True,
    task_routes={
        "app.tasks.publishing_tasks.*": {"queue": "critical"},
        "app.tasks.ai_tasks.*": {"queue": "high"},
        "app.tasks.data_collection_tasks.*": {"queue": "medium"},
        "app.tasks.report_tasks.*": {"queue": "low"},
    },
    task_default_retry_delay=60,
    task_max_retries=3,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
)

celery_app.conf.beat_schedule = {
    "scan-scheduled-posts": {
        "task": "app.tasks.publishing_tasks.scan_scheduled_posts",
        "schedule": 60.0,
    },
    "sync-comments": {
        "task": "app.tasks.data_collection_tasks.sync_comments",
        "schedule": 300.0,
    },
    "collect-analytics": {
        "task": "app.tasks.data_collection_tasks.collect_analytics",
        "schedule": 3600.0,
    },
    "refresh-expiring-tokens": {
        "task": "app.tasks.data_collection_tasks.refresh_expiring_tokens",
        "schedule": 3600.0,
    },
    "daily-report": {
        "task": "app.tasks.report_tasks.generate_daily_report",
        "schedule": crontab(hour=8, minute=0),
    },
}

celery_app.autodiscover_tasks([
    "app.tasks.publishing_tasks",
    "app.tasks.ai_tasks",
    "app.tasks.data_collection_tasks",
    "app.tasks.report_tasks",
])
