from __future__ import annotations

import logging

from celery.exceptions import SoftTimeLimitExceeded

from backend.app.tasks import execute_report_job
from backend.app.workers.celery_app import celery_app

_log = logging.getLogger("healthsphere.worker.reports")


@celery_app.task(
    name="healthsphere.reports.generate",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    time_limit=600,
    soft_time_limit=540,
)
def generate_patient_report_task(self, job_id: str) -> str:
    try:
        execute_report_job(job_id, self.request.id, self.request.id)
    except SoftTimeLimitExceeded:
        _log.error("report-task-soft-timeout", extra={"job_id": job_id, "task_id": self.request.id})
        raise
    except Exception as exc:
        _log.exception("report-task-failed", extra={"job_id": job_id, "task_id": self.request.id, "error": str(exc)})
        raise self.retry(exc=exc)
    return job_id
