import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "automated_resume_analysis",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=["app.tasks"],
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "hourly_ml_continuous_retraining_check": {
            "task": "retrain_ml_model_task",
            "schedule": 3600.0,
            "args": (5, False),
        },
        "periodic_email_queue_drain": {
            "task": "process_outgoing_email_queue_task",
            "schedule": 60.0,
        },
        "periodic_cache_maintenance": {
            "task": "cleanup_expired_cache_task",
            "schedule": 1800.0,
        },
        "periodic_active_comparisons_refresh": {
            "task": "refresh_active_comparisons_task",
            "schedule": 1800.0,
        },
    },
)
