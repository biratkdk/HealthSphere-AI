from __future__ import annotations

from backend.app.core.observability import record_notification
from backend.app.db.enterprise_repository import create_notification
from backend.app.db.repository import mark_report_job_notified
from backend.app.models import ImagingAnalysisResponse, Notification, ReportArtifact
from sqlalchemy.orm import Session


def notify_report_ready(
    db: Session,
    *,
    username: str,
    organization_id: int,
    patient_id: int,
    job_id: str,
    artifact: ReportArtifact,
) -> Notification:
    notification = create_notification(
        db,
        organization_id=organization_id,
        recipient_username=username,
        severity="low",
        category="reports",
        title="Patient briefing is ready",
        body=f"Patient {patient_id} briefing {job_id} is ready for review.",
        patient_id=patient_id,
        detail={"job_id": job_id, "artifact_uri": artifact.artifact_uri},
    )
    mark_report_job_notified(db, job_id)
    record_notification("reports")
    return notification


def notify_imaging_triage(
    db: Session,
    *,
    username: str,
    organization_id: int,
    patient_id: int,
    study_id: str,
    analysis: ImagingAnalysisResponse,
) -> Notification:
    severity = "high" if analysis.anomaly_score >= 0.72 else "medium" if analysis.anomaly_score >= 0.45 else "low"
    notification = create_notification(
        db,
        organization_id=organization_id,
        recipient_username=username,
        severity=severity,
        category="imaging",
        title="Imaging triage completed",
        body=analysis.result,
        patient_id=patient_id,
        detail={
            "study_id": study_id,
            "confidence": analysis.confidence,
            "suggested_next_step": analysis.suggested_next_step,
        },
    )
    record_notification("imaging")
    return notification
