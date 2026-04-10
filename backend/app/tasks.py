from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import BackgroundTasks

_log = logging.getLogger("healthsphere.tasks")
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.observability import record_report_job
from backend.app.db.enterprise_repository import create_report_job, get_report_job, list_report_jobs
from backend.app.db.repository import (
    attach_report_job_task,
    claim_report_jobs,
    get_report_job_record,
    mark_report_job_completed,
    mark_report_job_failed,
    mark_report_job_notified,
    mark_report_job_running,
    reschedule_report_job,
    update_report_job_stage,
)
from backend.app.db.session import SessionLocal
from backend.app.models import ReportArtifact, ReportJob
from backend.app.services.notification_service import notify_report_ready
from backend.app.services.patient_service import get_patient_summary_for_organization
from backend.app.services.reporting_service import build_patient_report
from backend.app.services.storage import get_storage_service


def enqueue_report_job(
    db: Session,
    patient_id: int,
    *,
    organization_id: int,
    requested_by: str | None = None,
    idempotency_key: str | None = None,
) -> ReportJob:
    settings = get_settings()
    return create_report_job(
        db,
        organization_id=organization_id,
        patient_id=patient_id,
        requested_by=requested_by,
        max_attempts=settings.job_max_attempts,
        idempotency_key=idempotency_key,
    )


def fetch_report_job(db: Session, organization_id: int, job_id: str) -> ReportJob | None:
    return get_report_job(db, organization_id, job_id)


def list_recent_report_jobs(db: Session, organization_id: int, limit: int = 25) -> list[ReportJob]:
    return list_report_jobs(db, organization_id, limit=limit)


def dispatch_report_job(job_id: str, background_tasks: BackgroundTasks | None = None) -> str:
    settings = get_settings()

    if settings.task_execution_mode == "celery":
        from backend.app.workers.report_tasks import generate_patient_report_task

        result = generate_patient_report_task.delay(job_id)
        with SessionLocal() as db:
            attach_report_job_task(db, job_id, result.id)
        record_report_job("queued", "celery")
        return result.id

    if settings.task_execution_mode == "inline":
        task_id = f"inline-{job_id}"
        with SessionLocal() as db:
            attach_report_job_task(db, job_id, task_id)
        if background_tasks is not None and not settings.is_vercel:
            background_tasks.add_task(execute_report_job, job_id, task_id, task_id)
        else:
            execute_report_job(job_id, task_id, task_id)
        record_report_job("queued", "inline")
        return task_id

    worker_id = f"dispatcher-{uuid4().hex[:10]}"
    with SessionLocal() as db:
        attach_report_job_task(db, job_id, worker_id)
    if background_tasks is not None and not settings.is_vercel:
        background_tasks.add_task(run_report_dispatch_cycle, 1, worker_id)
    record_report_job("queued", "dispatcher")
    return worker_id


def run_report_dispatch_cycle(limit: int | None = None, worker_id: str | None = None) -> dict[str, int | str]:
    settings = get_settings()
    effective_worker_id = worker_id or f"dispatcher-{uuid4().hex[:10]}"
    effective_limit = limit or settings.dispatcher_batch_size

    with SessionLocal() as db:
        claimed_job_ids = claim_report_jobs(
            db,
            effective_worker_id,
            limit=effective_limit,
            lease_seconds=settings.job_lease_seconds,
        )

    completed = 0
    failed = 0
    retry_pending = 0

    for job_id in claimed_job_ids:
        outcome = execute_report_job(job_id, effective_worker_id, effective_worker_id)
        if outcome == "completed":
            completed += 1
        elif outcome == "retry_pending":
            retry_pending += 1
        elif outcome == "failed":
            failed += 1

    return {
        "worker_id": effective_worker_id,
        "claimed": len(claimed_job_ids),
        "completed": completed,
        "retry_pending": retry_pending,
        "failed": failed,
    }


def execute_report_job(job_id: str, task_id: str | None = None, worker_id: str | None = None) -> str:
    settings = get_settings()

    with SessionLocal() as db:
        job = get_report_job_record(db, job_id)
        if job is None:
            return "missing"

        organization_id = job.organization_id
        patient_id = job.patient_id
        requested_by = job.requested_by
        max_attempts = job.max_attempts
        current_attempt = max(job.attempt_count, 1)
        effective_task_id = task_id or job.task_id or f"{settings.task_execution_mode}-{job_id}"
        effective_worker_id = worker_id or job.worker_id or effective_task_id

    try:
        with SessionLocal() as db:
            mark_report_job_running(
                db,
                job_id,
                task_id=effective_task_id,
                worker_id=effective_worker_id,
                workflow_stage="assembling_summary",
                lease_seconds=settings.job_lease_seconds,
            )
            record_report_job("running", settings.task_execution_mode)
            summary = get_patient_summary_for_organization(db, organization_id, patient_id)

        artifact: ReportArtifact = build_patient_report(
            patient=summary.patient,
            icu_risk=summary.icu_risk,
            disease_risk=summary.disease_risk,
            treatment=summary.treatment,
        )

        with SessionLocal() as db:
            update_report_job_stage(
                db,
                job_id,
                "rendering_artifact",
                worker_id=effective_worker_id,
                task_id=effective_task_id,
                lease_seconds=settings.job_lease_seconds,
            )

        artifact_uri = get_storage_service().store_report_artifact(job_id, artifact)
        artifact.artifact_uri = artifact_uri

        with SessionLocal() as db:
            update_report_job_stage(
                db,
                job_id,
                "persisting_artifact",
                worker_id=effective_worker_id,
                task_id=effective_task_id,
                lease_seconds=settings.job_lease_seconds,
            )
            mark_report_job_completed(
                db,
                job_id,
                artifact,
                artifact_uri=artifact_uri,
                delivery_status="stored",
            )

            if requested_by:
                update_report_job_stage(
                    db,
                    job_id,
                    "notifying",
                    worker_id=effective_worker_id,
                    task_id=effective_task_id,
                    lease_seconds=settings.job_lease_seconds,
                )
                notify_report_ready(
                    db,
                    username=requested_by,
                    organization_id=organization_id,
                    patient_id=patient_id,
                    job_id=job_id,
                    artifact=artifact,
                )
                mark_report_job_notified(db, job_id)

        record_report_job("completed", settings.task_execution_mode)
        return "completed"
    except Exception as exc:  # pragma: no cover - defensive
        backoff_seconds = min(
            settings.job_retry_backoff_seconds * max(current_attempt, 1),
            settings.job_lease_seconds * 6,
        )
        with SessionLocal() as db:
            if current_attempt < max_attempts:
                _log.warning(
                    "report-job-retry-scheduled",
                    extra={
                        "job_id": job_id,
                        "attempt": current_attempt,
                        "max_attempts": max_attempts,
                        "backoff_seconds": backoff_seconds,
                        "error": str(exc),
                    },
                )
                reschedule_report_job(db, job_id, str(exc), backoff_seconds=backoff_seconds)
                record_report_job("queued", settings.task_execution_mode)
                return "retry_pending"

            _log.error(
                "report-job-permanently-failed",
                extra={
                    "job_id": job_id,
                    "attempt": current_attempt,
                    "error": str(exc),
                },
                exc_info=True,
            )
            mark_report_job_failed(db, job_id, str(exc), delivery_status="failed")
        record_report_job("failed", settings.task_execution_mode)
        return "failed"
