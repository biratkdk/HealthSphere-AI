from __future__ import annotations

from celery import Celery

from backend.app.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "healthsphere",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialisation — only accept JSON to prevent pickle deserialization attacks
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_accept_content=["json"],

    # Time zone
    timezone="UTC",
    enable_utc=True,

    # Visibility / state tracking
    task_always_eager=settings.celery_task_always_eager,
    task_track_started=True,
    task_send_sent_event=True,

    # Hard and soft task timeouts to prevent runaway jobs
    task_time_limit=600,        # 10 min hard kill
    task_soft_time_limit=540,   # 9 min SoftTimeLimitExceeded warning

    # Acknowledgement: ack after task execution so re-queuing works on worker crash
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result expiry — keep results for 24 h then purge
    result_expires=86400,

    # Worker prefetch: one task per worker to avoid starvation on long tasks
    worker_prefetch_multiplier=1,

    # Broker connection retry on startup
    broker_connection_retry_on_startup=True,
)
