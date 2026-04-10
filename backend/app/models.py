import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Severity = Literal["low", "medium", "high", "critical"]
JobStatus = Literal["queued", "running", "completed", "failed"]
RoleName = Literal["admin", "clinician", "analyst", "service"]
AuthProviderName = Literal["local", "oidc", "google", "facebook", "service"]
TaskStatus = Literal["open", "in_progress", "blocked", "completed"]
TaskPriority = Literal["low", "medium", "high", "critical"]
InviteRole = Literal["clinician", "analyst"]
InviteStatus = Literal["pending", "accepted", "expired", "revoked"]
TimelineCategory = Literal["lab", "imaging", "alert", "report", "notification", "task", "handoff"]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OrganizationSummary(APIModel):
    organization_id: int
    slug: str
    name: str
    status: Literal["active", "suspended"] = "active"


class VitalSnapshot(APIModel):
    heart_rate: int = Field(..., ge=20, le=250)
    respiratory_rate: int = Field(..., ge=5, le=80)
    systolic_bp: int = Field(..., ge=50, le=250)
    temperature_c: float = Field(..., ge=30.0, le=45.0)
    oxygen_saturation: int = Field(..., ge=50, le=100)
    pain_score: int = Field(..., ge=0, le=10)


class LabResult(APIModel):
    name: str
    value: float
    unit: str
    collected_at: datetime


class ImagingFinding(APIModel):
    modality: str
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    captured_at: datetime


class PatientRecord(APIModel):
    patient_id: int
    mrn: str
    name: str
    age: int = Field(..., ge=0, le=120)
    sex: str
    care_unit: str
    diagnosis: str
    vitals: VitalSnapshot
    labs: list[LabResult]
    medications: list[str]
    imaging_history: list[ImagingFinding]
    risk_flags: list[str]
    last_updated: datetime
    risk_band: str = "low"


class Alert(APIModel):
    alert_id: str
    patient_id: int
    severity: Severity
    title: str
    description: str
    created_at: datetime
    acknowledged: bool = False


class IcuRiskResponse(APIModel):
    patient_id: int
    icu_risk: float = Field(..., ge=0.0, le=1.0)
    risk_band: Severity
    drivers: list[str]


class DiseaseRiskResponse(APIModel):
    patient_id: int
    diabetes_risk: float = Field(..., ge=0.0, le=1.0)
    heart_disease_risk: float = Field(..., ge=0.0, le=1.0)
    sepsis_watch_risk: float = Field(..., ge=0.0, le=1.0)
    overall_risk_band: Severity


class TreatmentRecommendation(APIModel):
    patient_id: int
    priority: Severity
    actions: list[str]
    rationale: str
    recommended_follow_up_minutes: int


class ImagingAnalysisResponse(APIModel):
    result: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    suggested_next_step: str
    study_reference: str | None = None
    stored_uri: str | None = None


class ImagingStudyRecord(APIModel):
    study_id: str
    patient_id: int
    filename: str
    content_type: str
    storage_uri: str
    uploaded_by: str
    created_at: datetime
    analysis: ImagingAnalysisResponse | None = None


class PatientTask(APIModel):
    task_id: str
    patient_id: int
    title: str
    detail: str
    status: TaskStatus
    priority: TaskPriority
    assignee_username: str | None = None
    created_by: str
    due_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PatientTaskCreateRequest(APIModel):
    title: str = Field(..., min_length=3, max_length=140)
    detail: str = Field(..., min_length=3, max_length=1000)
    priority: TaskPriority = "medium"
    assignee_username: str | None = Field(default=None, max_length=64)
    due_at: datetime | None = None


class PatientTaskUpdateRequest(APIModel):
    title: str | None = Field(default=None, min_length=3, max_length=140)
    detail: str | None = Field(default=None, min_length=3, max_length=1000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_username: str | None = Field(default=None, max_length=64)
    due_at: datetime | None = None


class HandoffNote(APIModel):
    note_id: str
    patient_id: int
    author_username: str
    summary: str
    details: str
    created_at: datetime


class HandoffNoteCreateRequest(APIModel):
    summary: str = Field(..., min_length=3, max_length=200)
    details: str = Field(..., min_length=3, max_length=2000)


class PatientTimelineEvent(APIModel):
    event_id: str
    patient_id: int
    category: TimelineCategory
    label: str
    summary: str
    created_at: datetime
    detail: dict[str, Any] | None = None


class PatientSummary(APIModel):
    patient: PatientRecord
    icu_risk: IcuRiskResponse
    disease_risk: DiseaseRiskResponse
    treatment: TreatmentRecommendation
    open_alerts: list[Alert]
    tasks: list[PatientTask] = Field(default_factory=list)
    recent_handoffs: list[HandoffNote] = Field(default_factory=list)


class ReportArtifact(APIModel):
    patient_id: int
    generated_at: datetime
    summary: str
    clinical_actions: list[str]
    risk_snapshot: dict[str, float]
    artifact_uri: str | None = None


class ReportJob(APIModel):
    job_id: str
    patient_id: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    workflow_stage: str = "queued"
    progress_percent: int = Field(default=0, ge=0, le=100)
    attempt_count: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    next_attempt_at: datetime | None = None
    lease_expires_at: datetime | None = None
    worker_id: str | None = None
    error: str | None = None
    artifact: ReportArtifact | None = None
    artifact_uri: str | None = None
    task_id: str | None = None
    requested_by: str | None = None
    delivery_status: Literal["pending", "stored", "notified", "failed"] = "pending"


class ModelRegistryEntry(APIModel):
    name: str
    version: str
    artifact_path: str
    owner: str
    validation_status: Literal["approved", "shadow", "staging"]
    last_retrained: datetime
    monitoring_tags: list[str]
    artifact_available: bool = False
    serving_mode: Literal["artifact", "fallback"] = "fallback"
    notes: list[str] = Field(default_factory=list)


class UserPreferences(APIModel):
    dashboard_view: str = "operations"
    notification_preference: str = "critical"
    title: str | None = None
    department: str | None = None
    organization: str | None = None
    phone: str | None = None
    location: str | None = None
    bio: str | None = None
    last_selected_patient_id: int | None = None


class UserProfile(APIModel):
    username: str
    full_name: str
    role: RoleName
    is_active: bool
    email: str | None = None
    auth_provider: AuthProviderName = "local"
    last_login_at: datetime | None = None
    organization_id: int | None = None
    organization_name: str | None = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)


class UserDirectoryEntry(APIModel):
    username: str
    full_name: str
    role: RoleName
    is_active: bool
    email: str | None = None
    auth_provider: AuthProviderName = "local"
    last_login_at: datetime | None = None
    organization_id: int | None = None
    organization_name: str | None = None


class UserRoleUpdateRequest(APIModel):
    role: Literal["admin", "clinician", "analyst"]


class UserStatusUpdateRequest(APIModel):
    is_active: bool


class UserRegistrationRequest(APIModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    full_name: str = Field(..., min_length=2, max_length=128)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=10, max_length=128)
    role: Literal["clinician", "analyst"] = "clinician"
    invite_code: str | None = Field(default=None, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = []
        if not re.search(r"[A-Z]", v):
            errors.append("at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("at least one lowercase letter")
        if not re.search(r"\d", v):
            errors.append("at least one digit")
        if not re.search(r"[^A-Za-z0-9]", v):
            errors.append("at least one special character")
        if errors:
            raise ValueError("Password must contain: " + ", ".join(errors) + ".")
        return v
    title: str | None = Field(default=None, max_length=96)
    department: str | None = Field(default=None, max_length=96)
    organization: str | None = Field(default=None, max_length=96)
    phone: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=96)
    bio: str | None = Field(default=None, max_length=400)


class UserProfileUpdateRequest(APIModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=128)
    email: str | None = Field(default=None, min_length=5, max_length=255)
    title: str | None = Field(default=None, max_length=96)
    department: str | None = Field(default=None, max_length=96)
    organization: str | None = Field(default=None, max_length=96)
    phone: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=96)
    bio: str | None = Field(default=None, max_length=400)
    dashboard_view: str | None = Field(default=None, max_length=64)
    notification_preference: str | None = Field(default=None, max_length=64)
    last_selected_patient_id: int | None = None
    current_password: str | None = Field(default=None, min_length=10, max_length=128)
    new_password: str | None = Field(default=None, min_length=10, max_length=128)


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile
    session_id: str | None = None


class StreamTokenResponse(APIModel):
    stream_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionRecord(APIModel):
    session_id: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    current: bool = False


class InviteCodeCreateRequest(APIModel):
    role: InviteRole = "clinician"
    email: str | None = Field(default=None, max_length=255)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InviteCodeRecord(APIModel):
    invite_id: str
    role: InviteRole
    email: str | None = None
    created_by: str
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    status: InviteStatus
    invite_code: str | None = None


class AuditLogEntry(APIModel):
    audit_id: int
    request_id: str
    actor_username: str
    actor_role: RoleName
    method: str
    path: str
    status_code: int
    entity_type: str | None = None
    entity_id: str | None = None
    detail: dict[str, Any] | None = None
    created_at: datetime


class AuthProviderDescriptor(APIModel):
    id: AuthProviderName | Literal["password"]
    label: str
    available: bool
    login_url: str | None = None
    description: str | None = None
    brand: str | None = None


class AuthProviderCatalog(APIModel):
    providers: list[AuthProviderDescriptor]


class Notification(APIModel):
    notification_id: str
    severity: Severity
    category: str
    title: str
    body: str
    recipient_username: str
    patient_id: int | None = None
    is_read: bool = False
    created_at: datetime
    read_at: datetime | None = None
    detail: dict[str, Any] | None = None


class CareUnitSummary(APIModel):
    care_unit: str
    patient_count: int
    open_alerts: int


class ReportQueueSummary(APIModel):
    queued: int
    running: int
    completed: int
    failed: int


class SystemCapability(APIModel):
    task_execution_mode: Literal["dispatcher", "inline", "celery"]
    storage_backend: str
    oidc_enabled: bool
    metrics_enabled: bool
    live_updates_enabled: bool = True


class AnalyticsOverview(APIModel):
    total_patients: int
    open_alerts: int
    critical_alerts: int
    unread_notifications: int
    report_queue: ReportQueueSummary
    care_units: list[CareUnitSummary]
    capabilities: SystemCapability


class OperationsLiveSnapshot(APIModel):
    generated_at: datetime
    unread_notifications: int
    open_alerts: int
    critical_alerts: int
    report_queue: ReportQueueSummary
    active_jobs: list[ReportJob]
    latest_alerts: list[Alert]
    latest_notifications: list[Notification]
