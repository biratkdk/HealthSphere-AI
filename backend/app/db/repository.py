from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import Settings
from backend.app.core.crypto import hash_password, verify_password
from backend.app.core.oidc import federated_auth_enabled
from backend.app.db.base import Base
from backend.app.db.entities import (
    AlertORM,
    AuditLogORM,
    OrganizationORM,
    ImagingFindingORM,
    ImagingStudyORM,
    LabResultORM,
    NotificationORM,
    PatientORM,
    ReportJobORM,
    UserORM,
)
from backend.app.db.seed_data import SEED_ALERTS, SEED_NOTIFICATIONS, SEED_PATIENTS
from backend.app.db.session import engine
from backend.app.models import (
    Alert,
    AnalyticsOverview,
    AuditLogEntry,
    CareUnitSummary,
    ImagingAnalysisResponse,
    ImagingFinding,
    ImagingStudyRecord,
    LabResult,
    Notification,
    PatientRecord,
    ReportArtifact,
    ReportJob,
    ReportQueueSummary,
    SystemCapability,
    OperationsLiveSnapshot,
    UserProfile,
    UserPreferences,
    UserProfileUpdateRequest,
    UserRegistrationRequest,
    VitalSnapshot,
)


REPORT_STAGE_PROGRESS = {
    "queued": 0,
    "claiming": 10,
    "assembling_summary": 30,
    "rendering_artifact": 58,
    "persisting_artifact": 82,
    "notifying": 94,
    "retry_pending": 12,
    "completed": 100,
    "failed": 100,
}

ROOT = Path(__file__).resolve().parents[3]
EXTERNAL_PATIENT_DATA = ROOT / "ml_pipeline" / "data" / "external" / "nepali_synthetic_patients.json"
DEFAULT_ORGANIZATION_SLUG = "healthsphere-medical"
DEFAULT_ORGANIZATION_NAME = "HealthSphere Medical"


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_or_create_default_organization(db: Session) -> OrganizationORM:
    organization = db.scalars(select(OrganizationORM).where(OrganizationORM.slug == DEFAULT_ORGANIZATION_SLUG)).first()
    if organization is not None:
        return organization

    now = datetime.now(UTC)
    organization = OrganizationORM(
        slug=DEFAULT_ORGANIZATION_SLUG,
        name=DEFAULT_ORGANIZATION_NAME,
        status="active",
        created_at=now,
        updated_at=now,
    )
    db.add(organization)
    db.flush()
    return organization


def seed_database(db: Session, settings: Settings) -> None:
    default_organization = get_or_create_default_organization(db)

    if settings.should_seed_demo_data:
        _seed_patients(db, default_organization.organization_id)
        db.flush()
        _seed_alerts(db, default_organization.organization_id)
        db.flush()

    if db.scalar(select(func.count()).select_from(UserORM)) == 0:
        _seed_users(db, settings, default_organization.organization_id, default_organization.name)
        db.flush()

    if settings.should_seed_demo_data:
        _seed_notifications(db, settings, default_organization.organization_id)

    db.commit()


def _seed_patients(db: Session, organization_id: int) -> None:
    for patient in SEED_PATIENTS:
        _upsert_patient_record(db, patient, organization_id)

    for patient in _load_external_seed_patients():
        _upsert_patient_record(db, patient, organization_id)


def _upsert_patient_record(db: Session, patient: dict, organization_id: int) -> None:
    record = db.get(PatientORM, patient["patient_id"])
    if record is None:
        record = PatientORM(patient_id=patient["patient_id"])

    record.organization_id = organization_id
    record.mrn = patient["mrn"]
    record.name = patient["name"]
    record.age = patient["age"]
    record.sex = patient["sex"]
    record.care_unit = patient["care_unit"]
    record.diagnosis = patient["diagnosis"]
    record.heart_rate = patient["vitals"]["heart_rate"]
    record.respiratory_rate = patient["vitals"]["respiratory_rate"]
    record.systolic_bp = patient["vitals"]["systolic_bp"]
    record.temperature_c = patient["vitals"]["temperature_c"]
    record.oxygen_saturation = patient["vitals"]["oxygen_saturation"]
    record.pain_score = patient["vitals"]["pain_score"]
    record.medications = patient["medications"]
    record.risk_flags = patient["risk_flags"]
    record.last_updated = patient["last_updated"]
    record.labs = [
        LabResultORM(
            name=lab["name"],
            value=lab["value"],
            unit=lab["unit"],
            collected_at=lab["collected_at"],
        )
        for lab in patient["labs"]
    ]
    record.imaging_history = [
        ImagingFindingORM(
            modality=item["modality"],
            summary=item["summary"],
            confidence=item["confidence"],
            captured_at=item["captured_at"],
        )
        for item in patient["imaging_history"]
    ]
    db.add(record)


def _load_external_seed_patients() -> list[dict]:
    if not EXTERNAL_PATIENT_DATA.exists():
        return []

    try:
        payload = json.loads(EXTERNAL_PATIENT_DATA.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    external_patients: list[dict] = []
    for patient in payload.get("patients", []):
        try:
            external_patients.append(
                {
                    "patient_id": int(patient["patient_id"]),
                    "mrn": patient["mrn"],
                    "name": patient["name"],
                    "age": int(patient["age"]),
                    "sex": patient["sex"],
                    "care_unit": patient["care_unit"],
                    "diagnosis": patient["diagnosis"],
                    "vitals": patient["vitals"],
                    "medications": list(patient.get("medications", [])),
                    "risk_flags": list(patient.get("risk_flags", [])),
                    "last_updated": _parse_seed_datetime(patient["last_updated"]),
                    "labs": [
                        {
                            "name": lab["name"],
                            "value": float(lab["value"]),
                            "unit": lab["unit"],
                            "collected_at": _parse_seed_datetime(lab["collected_at"]),
                        }
                        for lab in patient.get("labs", [])
                    ],
                    "imaging_history": [
                        {
                            "modality": item["modality"],
                            "summary": item["summary"],
                            "confidence": float(item["confidence"]),
                            "captured_at": _parse_seed_datetime(item["captured_at"]),
                        }
                        for item in patient.get("imaging_history", [])
                    ],
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    return external_patients


def _parse_seed_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return _ensure_utc(parsed) or datetime.now(UTC)


def _seed_alerts(db: Session, organization_id: int) -> None:
    for alert in SEED_ALERTS:
        record = db.get(AlertORM, alert["alert_id"])
        if record is None:
            record = AlertORM(alert_id=alert["alert_id"])
        record.organization_id = organization_id
        record.patient_id = alert["patient_id"]
        record.severity = alert["severity"]
        record.title = alert["title"]
        record.description = alert["description"]
        record.created_at = alert["created_at"]
        record.acknowledged = alert["acknowledged"]
        db.add(record)


def _seed_users(db: Session, settings: Settings, organization_id: int, organization_name: str) -> None:
    now = datetime.now(UTC)
    users = [
        UserORM(
            organization_id=organization_id,
            username=settings.bootstrap_admin_username,
            email="admin@healthsphere.local",
            full_name="Platform Administrator",
            role="admin",
            auth_provider="local",
            password_hash=hash_password(settings.bootstrap_admin_password),
            is_active=True,
            preferences=_build_user_preferences(role="admin", dashboard_view="operations", notification_preference="all"),
            created_at=now,
            updated_at=now,
        ),
        UserORM(
            organization_id=organization_id,
            username=settings.bootstrap_clinician_username,
            email="clinician@healthsphere.local",
            full_name="Lead Clinician",
            role="clinician",
            auth_provider="local",
            password_hash=hash_password(settings.bootstrap_clinician_password),
            is_active=True,
            preferences=_build_user_preferences(
                role="clinician",
                dashboard_view="patient-command",
                notification_preference="critical",
                title="Lead Clinician",
                department="Critical Care",
                organization=organization_name,
            ),
            created_at=now,
            updated_at=now,
        ),
        UserORM(
            organization_id=organization_id,
            username=settings.bootstrap_analyst_username,
            email="analyst@healthsphere.local",
            full_name="Clinical Analyst",
            role="analyst",
            auth_provider="local",
            password_hash=hash_password(settings.bootstrap_analyst_password),
            is_active=True,
            preferences=_build_user_preferences(
                role="analyst",
                dashboard_view="analytics",
                notification_preference="operations",
                title="Clinical Analyst",
                department="Care Intelligence",
                organization=organization_name,
            ),
            created_at=now,
            updated_at=now,
        ),
    ]
    db.add_all(users)


def _seed_notifications(db: Session, settings: Settings, organization_id: int) -> None:
    username_map = {
        "clinician": settings.bootstrap_clinician_username,
        "analyst": settings.bootstrap_analyst_username,
        "admin": settings.bootstrap_admin_username,
    }

    for notification in SEED_NOTIFICATIONS:
        record = db.get(NotificationORM, notification["notification_id"])
        if record is None:
            record = NotificationORM(notification_id=notification["notification_id"])
        record.organization_id = organization_id
        record.recipient_username = username_map.get(notification["recipient_username"], notification["recipient_username"])
        record.patient_id = notification["patient_id"]
        record.severity = notification["severity"]
        record.category = notification["category"]
        record.title = notification["title"]
        record.body = notification["body"]
        record.detail = notification["detail"]
        record.is_read = notification["is_read"]
        record.created_at = notification["created_at"]
        record.read_at = notification["read_at"]
        db.add(record)


def _patient_select():
    return select(PatientORM).options(
        selectinload(PatientORM.labs),
        selectinload(PatientORM.imaging_history),
        selectinload(PatientORM.alerts),
        selectinload(PatientORM.imaging_studies),
    )


def list_patients(db: Session) -> list[PatientRecord]:
    records = db.scalars(_patient_select().order_by(PatientORM.patient_id)).all()
    return [_patient_to_schema(record) for record in records]


def get_patient(db: Session, patient_id: int) -> PatientRecord | None:
    record = db.scalars(_patient_select().where(PatientORM.patient_id == patient_id)).first()
    if record is None:
        return None
    return _patient_to_schema(record)


def get_patient_record(db: Session, patient_id: int) -> PatientORM | None:
    return db.scalars(_patient_select().where(PatientORM.patient_id == patient_id)).first()


def list_alerts(db: Session) -> list[Alert]:
    alerts = db.scalars(select(AlertORM).order_by(desc(AlertORM.created_at))).all()
    return [_alert_to_schema(alert) for alert in alerts]


def alerts_for_patient(db: Session, patient_id: int) -> list[Alert]:
    alerts = db.scalars(
        select(AlertORM)
        .where(AlertORM.patient_id == patient_id, AlertORM.acknowledged.is_(False))
        .order_by(desc(AlertORM.created_at))
    ).all()
    return [_alert_to_schema(alert) for alert in alerts]


def get_user_by_username(db: Session, username: str) -> UserORM | None:
    return db.scalars(select(UserORM).where(UserORM.username == username)).first()


def get_user_by_email(db: Session, email: str) -> UserORM | None:
    return db.scalars(select(UserORM).where(UserORM.email == email)).first()


def get_user_by_external_subject(db: Session, external_subject: str) -> UserORM | None:
    return db.scalars(select(UserORM).where(UserORM.external_subject == external_subject)).first()


def create_or_update_federated_user(
    db: Session,
    *,
    external_subject: str,
    email: str | None,
    preferred_username: str | None,
    full_name: str,
    role: str,
    auth_provider: str = "oidc",
) -> UserProfile:
    user = get_user_by_external_subject(db, external_subject)
    if user is None and email:
        user = get_user_by_email(db, email.lower())
    if user is None and preferred_username:
        user = get_user_by_username(db, preferred_username)

    now = datetime.now(UTC)
    if user is None:
        username = _ensure_unique_username(db, preferred_username or email or f"oidc-{external_subject[-8:]}")
        user = UserORM(
            username=username,
            email=email.lower() if email else None,
            full_name=full_name,
            role=role,
            auth_provider=auth_provider,
            external_subject=external_subject,
            password_hash=hash_password(uuid4().hex),
            is_active=True,
            preferences=_build_user_preferences(role=role),
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )
        db.add(user)
    else:
        user.full_name = full_name
        user.role = role
        user.auth_provider = auth_provider
        user.external_subject = external_subject
        if email:
            user.email = email.lower()
        user.updated_at = now
        user.last_login_at = now
        db.add(user)

    db.commit()
    db.refresh(user)
    return user_to_profile(user)


def create_local_user(db: Session, registration: UserRegistrationRequest) -> UserProfile:
    requested_username = _normalize_optional_text(registration.username)
    email = registration.email.strip().lower()

    if requested_username and get_user_by_username(db, requested_username) is not None:
        raise ValueError("That username is already in use.")
    if get_user_by_email(db, email) is not None:
        raise ValueError("That email address is already in use.")

    username = _ensure_unique_username(
        db,
        requested_username or email.split("@", maxsplit=1)[0] or registration.full_name,
    )

    now = datetime.now(UTC)
    user = UserORM(
        username=username,
        email=email,
        full_name=registration.full_name.strip(),
        role=registration.role,
        auth_provider="local",
        password_hash=hash_password(registration.password),
        is_active=True,
        preferences=_build_user_preferences(
            role=registration.role,
            title=_normalize_optional_text(registration.title),
            department=_normalize_optional_text(registration.department),
            organization=_normalize_optional_text(registration.organization),
            phone=_normalize_optional_text(registration.phone),
            location=_normalize_optional_text(registration.location),
            bio=_normalize_optional_text(registration.bio),
        ),
        created_at=now,
        updated_at=now,
        last_login_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_profile(user)


def update_user_profile(
    db: Session,
    *,
    username: str,
    payload: UserProfileUpdateRequest,
) -> UserProfile:
    user = get_user_by_username(db, username)
    if user is None:
        raise ValueError("That user is not available.")

    if payload.new_password:
        if user.auth_provider != "local":
            raise ValueError("Password changes are only available for local accounts.")
        if not payload.current_password:
            raise ValueError("Current password is required to set a new password.")
        if not verify_password(payload.current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")
        user.password_hash = hash_password(payload.new_password)

    if payload.email is not None:
        normalized_email = payload.email.strip().lower() or None
        existing = get_user_by_email(db, normalized_email) if normalized_email else None
        if normalized_email and existing is not None and existing.username != user.username:
            raise ValueError("That email address is already in use.")
        user.email = normalized_email

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()

    current_preferences = _coerce_preferences(user.preferences)
    preferences = current_preferences.model_dump()

    for field in ("title", "department", "organization", "phone", "location", "bio"):
        value = getattr(payload, field)
        if value is not None:
            preferences[field] = _normalize_optional_text(value) if isinstance(value, str) else value

    if payload.dashboard_view is not None:
        preferences["dashboard_view"] = payload.dashboard_view.strip() or current_preferences.dashboard_view
    if payload.notification_preference is not None:
        preferences["notification_preference"] = payload.notification_preference.strip() or current_preferences.notification_preference

    user.preferences = preferences
    user.updated_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_profile(user)


def update_last_login(db: Session, user: UserORM) -> UserProfile:
    user.last_login_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_profile(user)


def user_to_profile(user: UserORM) -> UserProfile:
    preferences = _coerce_preferences(user.preferences)
    return UserProfile(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        email=user.email,
        auth_provider=user.auth_provider,
        last_login_at=_ensure_utc(user.last_login_at),
        preferences=preferences,
    )


def create_report_job(
    db: Session,
    patient_id: int,
    requested_by: str | None = None,
    *,
    max_attempts: int = 3,
) -> ReportJob:
    now = datetime.now(UTC)
    job = ReportJobORM(
        job_id=str(uuid4()),
        patient_id=patient_id,
        status="queued",
        created_at=now,
        updated_at=now,
        workflow_stage="queued",
        progress_percent=REPORT_STAGE_PROGRESS["queued"],
        attempt_count=0,
        max_attempts=max_attempts,
        next_attempt_at=now,
        lease_expires_at=None,
        worker_id=None,
        error=None,
        artifact_payload=None,
        artifact_uri=None,
        task_id=None,
        requested_by=requested_by,
        delivery_status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _report_job_to_schema(job)


def get_report_job(db: Session, job_id: str) -> ReportJob | None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return None
    return _report_job_to_schema(job)


def get_report_job_record(db: Session, job_id: str) -> ReportJobORM | None:
    return db.get(ReportJobORM, job_id)


def list_report_jobs(db: Session, limit: int = 25) -> list[ReportJob]:
    jobs = db.scalars(select(ReportJobORM).order_by(desc(ReportJobORM.created_at)).limit(limit)).all()
    return [_report_job_to_schema(job) for job in jobs]


def attach_report_job_task(db: Session, job_id: str, task_id: str) -> None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return
    job.task_id = task_id
    job.updated_at = datetime.now(UTC)
    db.add(job)
    db.commit()


def claim_report_jobs(
    db: Session,
    worker_id: str,
    *,
    limit: int,
    lease_seconds: int,
) -> list[str]:
    now = datetime.now(UTC)
    lease_expires_at = now + timedelta(seconds=lease_seconds)
    candidates = db.scalars(
        select(ReportJobORM)
        .where(
            ReportJobORM.status.in_(("queued", "running")),
            or_(ReportJobORM.next_attempt_at.is_(None), ReportJobORM.next_attempt_at <= now),
            or_(ReportJobORM.status == "queued", ReportJobORM.lease_expires_at.is_(None), ReportJobORM.lease_expires_at < now),
        )
        .order_by(asc(ReportJobORM.next_attempt_at), asc(ReportJobORM.created_at))
        .limit(limit)
    ).all()

    claimed: list[str] = []
    for job in candidates:
        lease_expires_at = _ensure_utc(job.lease_expires_at)
        if job.status == "running" and lease_expires_at and lease_expires_at >= now:
            continue
        job.status = "running"
        job.workflow_stage = "claiming"
        job.progress_percent = REPORT_STAGE_PROGRESS["claiming"]
        job.attempt_count += 1
        job.next_attempt_at = now
        job.lease_expires_at = lease_expires_at
        job.worker_id = worker_id
        job.task_id = worker_id
        job.updated_at = now
        db.add(job)
        claimed.append(job.job_id)

    if claimed:
        db.commit()
    return claimed


def mark_report_job_running(
    db: Session,
    job_id: str,
    *,
    task_id: str | None = None,
    worker_id: str | None = None,
    workflow_stage: str = "assembling_summary",
    lease_seconds: int | None = None,
) -> None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return
    job.status = "running"
    now = datetime.now(UTC)
    if task_id:
        job.task_id = task_id
    if worker_id:
        job.worker_id = worker_id
    job.workflow_stage = workflow_stage
    job.progress_percent = REPORT_STAGE_PROGRESS.get(workflow_stage, job.progress_percent or REPORT_STAGE_PROGRESS["claiming"])
    if lease_seconds:
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
    job.updated_at = now
    db.add(job)
    db.commit()


def update_report_job_stage(
    db: Session,
    job_id: str,
    workflow_stage: str,
    *,
    worker_id: str | None = None,
    task_id: str | None = None,
    lease_seconds: int | None = None,
) -> None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return
    now = datetime.now(UTC)
    job.status = "running"
    job.workflow_stage = workflow_stage
    job.progress_percent = REPORT_STAGE_PROGRESS.get(workflow_stage, job.progress_percent)
    job.updated_at = now
    if worker_id:
        job.worker_id = worker_id
    if task_id:
        job.task_id = task_id
    if lease_seconds:
        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
    db.add(job)
    db.commit()


def mark_report_job_completed(
    db: Session,
    job_id: str,
    artifact: ReportArtifact,
    *,
    artifact_uri: str | None = None,
    delivery_status: str = "stored",
) -> None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return
    job.status = "completed"
    job.updated_at = datetime.now(UTC)
    job.workflow_stage = "completed"
    job.progress_percent = REPORT_STAGE_PROGRESS["completed"]
    job.error = None
    job.artifact_payload = artifact.model_dump(mode="json")
    job.artifact_uri = artifact_uri
    job.delivery_status = delivery_status
    job.next_attempt_at = None
    job.lease_expires_at = None
    db.add(job)
    db.commit()


def mark_report_job_notified(db: Session, job_id: str) -> None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return
    job.status = "completed"
    job.delivery_status = "notified"
    job.workflow_stage = "completed"
    job.progress_percent = REPORT_STAGE_PROGRESS["completed"]
    job.next_attempt_at = None
    job.lease_expires_at = None
    job.updated_at = datetime.now(UTC)
    db.add(job)
    db.commit()


def reschedule_report_job(db: Session, job_id: str, error: str, *, backoff_seconds: int) -> None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return
    now = datetime.now(UTC)
    job.status = "queued"
    job.workflow_stage = "retry_pending"
    job.progress_percent = REPORT_STAGE_PROGRESS["retry_pending"]
    job.updated_at = now
    job.error = error
    job.next_attempt_at = now + timedelta(seconds=backoff_seconds)
    job.lease_expires_at = None
    db.add(job)
    db.commit()


def mark_report_job_failed(db: Session, job_id: str, error: str, delivery_status: str = "failed") -> None:
    job = db.get(ReportJobORM, job_id)
    if job is None:
        return
    job.status = "failed"
    job.updated_at = datetime.now(UTC)
    job.workflow_stage = "failed"
    job.progress_percent = REPORT_STAGE_PROGRESS["failed"]
    job.error = error
    job.delivery_status = delivery_status
    job.next_attempt_at = None
    job.lease_expires_at = None
    db.add(job)
    db.commit()


def create_notification(
    db: Session,
    *,
    recipient_username: str,
    severity: str,
    category: str,
    title: str,
    body: str,
    patient_id: int | None = None,
    detail: dict | None = None,
) -> Notification:
    notification = NotificationORM(
        notification_id=str(uuid4()),
        recipient_username=recipient_username,
        patient_id=patient_id,
        severity=severity,
        category=category,
        title=title,
        body=body,
        detail=detail,
        is_read=False,
        created_at=datetime.now(UTC),
        read_at=None,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return _notification_to_schema(notification)


def list_notifications(
    db: Session,
    recipient_username: str,
    *,
    limit: int = 25,
    unread_only: bool = False,
) -> list[Notification]:
    query = select(NotificationORM).where(NotificationORM.recipient_username == recipient_username)
    if unread_only:
        query = query.where(NotificationORM.is_read.is_(False))
    notifications = db.scalars(query.order_by(desc(NotificationORM.created_at)).limit(limit)).all()
    return [_notification_to_schema(item) for item in notifications]


def mark_notification_read(db: Session, notification_id: str, recipient_username: str) -> Notification | None:
    notification = db.get(NotificationORM, notification_id)
    if notification is None or notification.recipient_username != recipient_username:
        return None
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return _notification_to_schema(notification)


def prune_notifications(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    notifications = db.scalars(select(NotificationORM).where(NotificationORM.created_at < cutoff)).all()
    removed = len(notifications)
    for notification in notifications:
        db.delete(notification)
    if removed:
        db.commit()
    return removed


def prune_report_jobs(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    jobs = db.scalars(
        select(ReportJobORM).where(
            ReportJobORM.updated_at < cutoff,
            ReportJobORM.status.in_(("completed", "failed")),
        )
    ).all()
    removed = len(jobs)
    for job in jobs:
        db.delete(job)
    if removed:
        db.commit()
    return removed


def prune_audit_logs(db: Session, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    logs = db.scalars(select(AuditLogORM).where(AuditLogORM.created_at < cutoff)).all()
    removed = len(logs)
    for log in logs:
        db.delete(log)
    if removed:
        db.commit()
    return removed


def create_imaging_study(
    db: Session,
    *,
    patient_id: int,
    filename: str,
    content_type: str,
    storage_uri: str,
    uploaded_by: str,
    analysis_payload: dict | None,
) -> ImagingStudyRecord:
    study = ImagingStudyORM(
        study_id=str(uuid4()),
        patient_id=patient_id,
        filename=filename,
        content_type=content_type,
        storage_uri=storage_uri,
        uploaded_by=uploaded_by,
        analysis_payload=analysis_payload,
        created_at=datetime.now(UTC),
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return _imaging_study_to_schema(study)


def list_imaging_studies(db: Session, patient_id: int, limit: int = 10) -> list[ImagingStudyRecord]:
    studies = db.scalars(
        select(ImagingStudyORM)
        .where(ImagingStudyORM.patient_id == patient_id)
        .order_by(desc(ImagingStudyORM.created_at))
        .limit(limit)
    ).all()
    return [_imaging_study_to_schema(study) for study in studies]


def get_imaging_study_record(db: Session, study_id: str) -> ImagingStudyORM | None:
    return db.get(ImagingStudyORM, study_id)


def get_analytics_overview(db: Session, user: UserProfile, settings: Settings) -> AnalyticsOverview:
    patients = db.scalars(select(PatientORM).order_by(PatientORM.care_unit, PatientORM.patient_id)).all()
    alerts = db.scalars(select(AlertORM).where(AlertORM.acknowledged.is_(False))).all()
    jobs = db.scalars(select(ReportJobORM)).all()

    unread_notifications = db.scalar(
        select(func.count())
        .select_from(NotificationORM)
        .where(NotificationORM.recipient_username == user.username, NotificationORM.is_read.is_(False))
    )
    unread_notifications = int(unread_notifications or 0)

    open_alerts_by_patient = Counter(alert.patient_id for alert in alerts)
    patients_by_unit = Counter(patient.care_unit for patient in patients)
    alerts_by_unit = Counter()

    for patient in patients:
        alerts_by_unit[patient.care_unit] += open_alerts_by_patient.get(patient.patient_id, 0)

    care_units = [
        CareUnitSummary(
            care_unit=care_unit,
            patient_count=patient_count,
            open_alerts=alerts_by_unit.get(care_unit, 0),
        )
        for care_unit, patient_count in sorted(patients_by_unit.items())
    ]

    queue_counts = Counter(job.status for job in jobs)

    return AnalyticsOverview(
        total_patients=len(patients),
        open_alerts=len(alerts),
        critical_alerts=sum(1 for alert in alerts if alert.severity == "critical"),
        unread_notifications=unread_notifications,
        report_queue=ReportQueueSummary(
            queued=queue_counts.get("queued", 0),
            running=queue_counts.get("running", 0),
            completed=queue_counts.get("completed", 0),
            failed=queue_counts.get("failed", 0),
        ),
        care_units=care_units,
        capabilities=SystemCapability(
            task_execution_mode=settings.task_execution_mode,
            storage_backend=settings.resolved_storage_backend,
            oidc_enabled=federated_auth_enabled(settings),
            metrics_enabled=settings.metrics_enabled,
            live_updates_enabled=True,
        ),
    )


def build_operations_live_snapshot(
    db: Session,
    *,
    current_user: UserProfile,
    settings: Settings,
    limit: int = 6,
) -> OperationsLiveSnapshot:
    analytics = get_analytics_overview(db, current_user, settings)
    active_jobs = list_report_jobs(db, limit=limit)
    latest_alerts = list_alerts(db)[:limit]
    latest_notifications = list_notifications(db, recipient_username=current_user.username, limit=limit)
    return OperationsLiveSnapshot(
        generated_at=datetime.now(UTC),
        unread_notifications=analytics.unread_notifications,
        open_alerts=analytics.open_alerts,
        critical_alerts=analytics.critical_alerts,
        report_queue=analytics.report_queue,
        active_jobs=active_jobs,
        latest_alerts=latest_alerts,
        latest_notifications=latest_notifications,
    )


def list_audit_logs(db: Session, limit: int = 50) -> list[AuditLogEntry]:
    logs = db.scalars(select(AuditLogORM).order_by(desc(AuditLogORM.created_at)).limit(limit)).all()
    return [_audit_log_to_schema(log) for log in logs]


def create_audit_log(
    db: Session,
    *,
    request_id: str,
    actor_username: str,
    actor_role: str,
    method: str,
    path: str,
    status_code: int,
    entity_type: str | None = None,
    entity_id: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        AuditLogORM(
            request_id=request_id,
            actor_username=actor_username,
            actor_role=actor_role,
            method=method,
            path=path,
            status_code=status_code,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()


def _risk_band_from_flags(risk_flags: list) -> str:
    n = len(risk_flags) if risk_flags else 0
    if n >= 4:
        return "critical"
    if n >= 3:
        return "high"
    if n >= 1:
        return "medium"
    return "low"


def _patient_to_schema(patient: PatientORM) -> PatientRecord:
    sorted_labs = sorted(patient.labs, key=lambda item: item.collected_at)
    sorted_imaging = sorted(patient.imaging_history, key=lambda item: item.captured_at, reverse=True)
    return PatientRecord(
        patient_id=patient.patient_id,
        mrn=patient.mrn,
        name=patient.name,
        age=patient.age,
        sex=patient.sex,
        care_unit=patient.care_unit,
        diagnosis=patient.diagnosis,
        vitals=VitalSnapshot(
            heart_rate=patient.heart_rate,
            respiratory_rate=patient.respiratory_rate,
            systolic_bp=patient.systolic_bp,
            temperature_c=patient.temperature_c,
            oxygen_saturation=patient.oxygen_saturation,
            pain_score=patient.pain_score,
        ),
        labs=[_lab_result_to_schema(item) for item in sorted_labs],
        medications=patient.medications,
        imaging_history=[_imaging_finding_to_schema(item) for item in sorted_imaging],
        risk_flags=patient.risk_flags,
        last_updated=_ensure_utc(patient.last_updated),
        risk_band=_risk_band_from_flags(patient.risk_flags),
    )


def _report_job_to_schema(job: ReportJobORM) -> ReportJob:
    artifact = ReportArtifact.model_validate(job.artifact_payload) if job.artifact_payload else None
    return ReportJob(
        job_id=job.job_id,
        patient_id=job.patient_id,
        status=job.status,
        created_at=_ensure_utc(job.created_at),
        updated_at=_ensure_utc(job.updated_at),
        workflow_stage=job.workflow_stage,
        progress_percent=job.progress_percent,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        next_attempt_at=_ensure_utc(job.next_attempt_at),
        lease_expires_at=_ensure_utc(job.lease_expires_at),
        worker_id=job.worker_id,
        error=job.error,
        artifact=artifact,
        artifact_uri=job.artifact_uri,
        task_id=job.task_id,
        requested_by=job.requested_by,
        delivery_status=job.delivery_status,
    )


def _notification_to_schema(notification: NotificationORM) -> Notification:
    return Notification(
        notification_id=notification.notification_id,
        severity=notification.severity,
        category=notification.category,
        title=notification.title,
        body=notification.body,
        recipient_username=notification.recipient_username,
        patient_id=notification.patient_id,
        is_read=notification.is_read,
        created_at=_ensure_utc(notification.created_at),
        read_at=_ensure_utc(notification.read_at),
        detail=notification.detail,
    )


def _imaging_study_to_schema(study: ImagingStudyORM) -> ImagingStudyRecord:
    analysis = ImagingAnalysisResponse.model_validate(study.analysis_payload) if study.analysis_payload else None
    return ImagingStudyRecord(
        study_id=study.study_id,
        patient_id=study.patient_id,
        filename=study.filename,
        content_type=study.content_type,
        storage_uri=study.storage_uri,
        uploaded_by=study.uploaded_by,
        created_at=_ensure_utc(study.created_at),
        analysis=analysis,
    )


def _lab_result_to_schema(item: LabResultORM) -> LabResult:
    return LabResult(
        name=item.name,
        value=item.value,
        unit=item.unit,
        collected_at=_ensure_utc(item.collected_at),
    )


def _imaging_finding_to_schema(item: ImagingFindingORM) -> ImagingFinding:
    return ImagingFinding(
        modality=item.modality,
        summary=item.summary,
        confidence=item.confidence,
        captured_at=_ensure_utc(item.captured_at),
    )


def _alert_to_schema(alert: AlertORM) -> Alert:
    return Alert(
        alert_id=alert.alert_id,
        patient_id=alert.patient_id,
        severity=alert.severity,
        title=alert.title,
        description=alert.description,
        created_at=_ensure_utc(alert.created_at),
        acknowledged=alert.acknowledged,
    )


def _audit_log_to_schema(log: AuditLogORM) -> AuditLogEntry:
    return AuditLogEntry(
        audit_id=log.audit_id,
        request_id=log.request_id,
        actor_username=log.actor_username,
        actor_role=log.actor_role,
        method=log.method,
        path=log.path,
        status_code=log.status_code,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        detail=log.detail,
        created_at=_ensure_utc(log.created_at),
    )


def _ensure_unique_username(db: Session, raw_username: str) -> str:
    base = re.sub(r"[^a-z0-9._-]+", "-", raw_username.lower()).strip("-") or "oidc-user"
    candidate = base[:64]
    suffix = 1
    while get_user_by_username(db, candidate) is not None:
        truncated = base[: max(1, 60 - len(str(suffix)))]
        candidate = f"{truncated}-{suffix}"
        suffix += 1
    return candidate


def _build_user_preferences(
    *,
    role: str,
    dashboard_view: str | None = None,
    notification_preference: str | None = None,
    title: str | None = None,
    department: str | None = None,
    organization: str | None = None,
    phone: str | None = None,
    location: str | None = None,
    bio: str | None = None,
) -> dict:
    default_dashboard = "analytics" if role == "analyst" else "operations"
    default_notifications = "operations" if role == "analyst" else "critical"
    return UserPreferences(
        dashboard_view=dashboard_view or default_dashboard,
        notification_preference=notification_preference or default_notifications,
        title=title,
        department=department,
        organization=organization,
        phone=phone,
        location=location,
        bio=bio,
    ).model_dump()


def _coerce_preferences(raw_preferences: dict | None) -> UserPreferences:
    payload = raw_preferences or {}
    if "dashboard" in payload and "dashboard_view" not in payload:
        payload["dashboard_view"] = payload.get("dashboard")
    if "notifications" in payload and "notification_preference" not in payload:
        payload["notification_preference"] = payload.get("notifications")
    return UserPreferences.model_validate(payload)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
