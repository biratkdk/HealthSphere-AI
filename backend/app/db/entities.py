from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class OrganizationORM(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    users: Mapped[list["UserORM"]] = relationship(back_populates="organization")
    patients: Mapped[list["PatientORM"]] = relationship(back_populates="organization")


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(32), index=True)
    auth_provider: Mapped[str] = mapped_column(String(32), default="local", index=True)
    external_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped[OrganizationORM] = relationship(back_populates="users")
    sessions: Mapped[list["UserSessionORM"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    created_invites: Mapped[list["InviteCodeORM"]] = relationship(back_populates="creator")


class PatientORM(Base):
    __tablename__ = "patients"

    patient_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    mrn: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(16))
    care_unit: Mapped[str] = mapped_column(String(64), index=True)
    diagnosis: Mapped[str] = mapped_column(String(256))
    heart_rate: Mapped[int] = mapped_column(Integer)
    respiratory_rate: Mapped[int] = mapped_column(Integer)
    systolic_bp: Mapped[int] = mapped_column(Integer)
    temperature_c: Mapped[float] = mapped_column(Float)
    oxygen_saturation: Mapped[int] = mapped_column(Integer)
    pain_score: Mapped[int] = mapped_column(Integer)
    medications: Mapped[list[str]] = mapped_column(JSON, default=list)
    risk_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    organization: Mapped[OrganizationORM] = relationship(back_populates="patients")
    labs: Mapped[list["LabResultORM"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    imaging_history: Mapped[list["ImagingFindingORM"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    alerts: Mapped[list["AlertORM"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    imaging_studies: Mapped[list["ImagingStudyORM"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tasks: Mapped[list["CareTaskORM"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    handoff_notes: Mapped[list["HandoffNoteORM"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class LabResultORM(Base):
    __tablename__ = "lab_results"
    __mapper_args__ = {"confirm_deleted_rows": False}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    name: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    patient: Mapped[PatientORM] = relationship(back_populates="labs")


class ImagingFindingORM(Base):
    __tablename__ = "imaging_findings"
    __mapper_args__ = {"confirm_deleted_rows": False}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    modality: Mapped[str] = mapped_column(String(64))
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    patient: Mapped[PatientORM] = relationship(back_populates="imaging_history")


class AlertORM(Base):
    __tablename__ = "alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    patient: Mapped[PatientORM] = relationship(back_populates="alerts")


class ReportJobORM(Base):
    __tablename__ = "report_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    workflow_stage: Mapped[str] = mapped_column(String(64), default="queued", index=True)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    artifact_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    delivery_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.organization_id"), nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_username: Mapped[str] = mapped_column(String(64), index=True)
    actor_role: Mapped[str] = mapped_column(String(32), index=True)
    method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(256), index=True)
    status_code: Mapped[int] = mapped_column(Integer, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class NotificationORM(Base):
    __tablename__ = "notifications"
    __mapper_args__ = {"confirm_deleted_rows": False}

    notification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.organization_id"), nullable=True, index=True)
    recipient_username: Mapped[str] = mapped_column(String(64), index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.patient_id"), nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text)
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImagingStudyORM(Base):
    __tablename__ = "imaging_studies"

    study_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    storage_uri: Mapped[str] = mapped_column(String(512))
    uploaded_by: Mapped[str] = mapped_column(String(64), index=True)
    priority: Mapped[str] = mapped_column(String(32), default="routine", index=True)
    review_status: Mapped[str] = mapped_column(String(32), default="pending_review", index=True)
    review_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    signed_off_by: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    signed_off_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    analysis_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    patient: Mapped[PatientORM] = relationship(back_populates="imaging_studies")


class UserSessionORM(Base):
    __tablename__ = "user_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    user: Mapped[UserORM] = relationship(back_populates="sessions")


class InviteCodeORM(Base):
    __tablename__ = "invite_codes"

    invite_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    created_by_username: Mapped[str] = mapped_column(ForeignKey("users.username"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped[UserORM] = relationship(back_populates="created_invites")


class CareTaskORM(Base):
    __tablename__ = "care_tasks"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    title: Mapped[str] = mapped_column(String(140))
    detail: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    assignee_username: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_by: Mapped[str] = mapped_column(String(64), index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    patient: Mapped[PatientORM] = relationship(back_populates="tasks")


class HandoffNoteORM(Base):
    __tablename__ = "handoff_notes"

    note_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.organization_id"), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.patient_id"), index=True)
    author_username: Mapped[str] = mapped_column(String(64), index=True)
    summary: Mapped[str] = mapped_column(String(200))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    patient: Mapped[PatientORM] = relationship(back_populates="handoff_notes")
