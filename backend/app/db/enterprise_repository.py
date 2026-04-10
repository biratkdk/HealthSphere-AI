from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
import re
from secrets import token_urlsafe
from uuid import uuid4

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import Settings, get_settings
from backend.app.core.crypto import create_refresh_token_value, hash_password, hash_session_token, verify_password
from backend.app.core.oidc import federated_auth_enabled
from backend.app.db.entities import (
    AlertORM,
    AuditLogORM,
    CareTaskORM,
    HandoffNoteORM,
    ImagingStudyORM,
    InviteCodeORM,
    NotificationORM,
    OrganizationORM,
    PatientORM,
    ReportJobORM,
    UserORM,
    UserSessionORM,
)
from backend.app.db.repository import (
    REPORT_STAGE_PROGRESS,
    _alert_to_schema,
    _build_user_preferences,
    _coerce_preferences,
    _derive_imaging_priority,
    _derive_review_due_at,
    _ensure_unique_username,
    _ensure_utc,
    _imaging_study_to_schema,
    _normalize_optional_text,
    _notification_to_schema,
    _patient_to_schema,
    _report_job_to_schema,
    get_or_create_default_organization,
)
from backend.app.models import (
    Alert,
    AnalyticsOverview,
    AuditLogEntry,
    CareUnitSummary,
    HandoffNote,
    HandoffNoteCreateRequest,
    ImagingLinkedReportJob,
    ImagingStudyRecord,
    ImagingStudyReviewRequest,
    ImagingWorkbench,
    ImagingWorkbenchItem,
    ImagingWorkbenchSummary,
    InviteCodeCreateRequest,
    InviteCodeRecord,
    Notification,
    OperationsLiveSnapshot,
    OrganizationSummary,
    PatientRecord,
    PopulationAlertQueueItem,
    PopulationBoardTotals,
    PopulationCareUnitBoard,
    PopulationImagingQueueItem,
    PopulationOperationsBoard,
    PopulationPatientCard,
    PopulationTaskQueueItem,
    PatientTask,
    PatientTaskCreateRequest,
    PatientTaskUpdateRequest,
    PatientTimelineEvent,
    ReportJob,
    ReportQueueSummary,
    SessionRecord,
    SystemCapability,
    UserDirectoryEntry,
    UserProfile,
    UserProfileUpdateRequest,
    UserRegistrationRequest,
)


def _organization_to_summary(organization: OrganizationORM) -> OrganizationSummary:
    return OrganizationSummary(
        organization_id=organization.organization_id,
        slug=organization.slug,
        name=organization.name,
        status=organization.status,  # type: ignore[arg-type]
    )


def user_to_profile(user: UserORM) -> UserProfile:
    preferences = _coerce_preferences(user.preferences)
    organization_name = user.organization.name if getattr(user, "organization", None) is not None else preferences.organization
    preferences.organization = organization_name
    return UserProfile(
        username=user.username,
        full_name=user.full_name,
        role=user.role,  # type: ignore[arg-type]
        is_active=user.is_active,
        email=user.email,
        auth_provider=user.auth_provider,  # type: ignore[arg-type]
        last_login_at=_ensure_utc(user.last_login_at),
        organization_id=getattr(user, "organization_id", None),
        organization_name=organization_name,
        preferences=preferences,
    )


def _user_directory_entry(user: UserORM) -> UserDirectoryEntry:
    return UserDirectoryEntry(
        username=user.username,
        full_name=user.full_name,
        role=user.role,  # type: ignore[arg-type]
        is_active=user.is_active,
        email=user.email,
        auth_provider=user.auth_provider,  # type: ignore[arg-type]
        last_login_at=_ensure_utc(user.last_login_at),
        organization_id=getattr(user, "organization_id", None),
        organization_name=user.organization.name if getattr(user, "organization", None) is not None else None,
    )


def _session_to_schema(session: UserSessionORM, current_session_id: str | None = None) -> SessionRecord:
    return SessionRecord(
        session_id=session.session_id,
        created_at=_ensure_utc(session.created_at) or datetime.now(UTC),
        last_used_at=_ensure_utc(session.last_used_at) or datetime.now(UTC),
        expires_at=_ensure_utc(session.expires_at) or datetime.now(UTC),
        revoked_at=_ensure_utc(session.revoked_at),
        user_agent=session.user_agent,
        ip_address=session.ip_address,
        current=session.session_id == current_session_id,
    )


def _invite_to_schema(invite: InviteCodeORM, raw_code: str | None = None) -> InviteCodeRecord:
    now = datetime.now(UTC)
    expires_at = _ensure_utc(invite.expires_at) or now
    if invite.status == "revoked":
        status = "revoked"
    elif invite.accepted_at:
        status = "accepted"
    elif expires_at < now:
        status = "expired"
    else:
        status = "pending"

    return InviteCodeRecord(
        invite_id=invite.invite_id,
        role=invite.role,  # type: ignore[arg-type]
        email=invite.email,
        created_by=invite.created_by_username,
        created_at=_ensure_utc(invite.created_at) or now,
        expires_at=expires_at,
        accepted_at=_ensure_utc(invite.accepted_at),
        status=status,  # type: ignore[arg-type]
        invite_code=raw_code,
    )


def _elapsed_minutes(timestamp: datetime | None, *, now: datetime | None = None) -> int:
    if timestamp is None:
        return 0
    reference = now or datetime.now(UTC)
    return max(0, int((reference - timestamp).total_seconds() // 60))


def _task_due_label(*, status: str, due_at: datetime | None, due_in_minutes: int | None) -> str:
    if status == "completed":
        return "Completed"
    if due_at is None or due_in_minutes is None:
        return "No due time"
    if due_in_minutes < 0:
        return f"Overdue by {_format_duration(abs(due_in_minutes))}"
    if due_in_minutes == 0:
        return "Due now"
    return f"Due in {_format_duration(due_in_minutes)}"


def _format_duration(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes}m"
    hours, remainder = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {remainder}m" if remainder else f"{hours}h"
    days, rem_hours = divmod(hours, 24)
    return f"{days}d {rem_hours}h" if rem_hours else f"{days}d"


def _parse_handoff_details(details: str) -> tuple[list[str], list[str], list[str]]:
    section_map = {
        "what changed": "what_changed",
        "what changed since last shift": "what_changed",
        "pending": "pending_items",
        "pending items": "pending_items",
        "watch": "watch_items",
        "watch items": "watch_items",
    }
    structured: dict[str, list[str]] = {
        "what_changed": [],
        "pending_items": [],
        "watch_items": [],
    }
    current_section: str | None = None
    carryover: list[str] = []

    for raw_line in details.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = re.sub(r"[:\s-]+$", "", line.lower())
        section_key = section_map.get(normalized)
        if section_key is not None:
            current_section = section_key
            continue
        entry = re.sub(r"^[\-*•]\s*", "", line).strip()
        if not entry:
            continue
        if current_section is None:
            carryover.append(entry)
        else:
            structured[current_section].append(entry)

    if carryover and not any(structured.values()):
        structured["what_changed"] = carryover
    elif carryover:
        structured["what_changed"] = [*carryover, *structured["what_changed"]]

    return structured["what_changed"], structured["pending_items"], structured["watch_items"]


def _task_to_schema(task: CareTaskORM) -> PatientTask:
    now = datetime.now(UTC)
    created_at = _ensure_utc(task.created_at) or now
    updated_at = _ensure_utc(task.updated_at) or now
    due_at = _ensure_utc(task.due_at)
    due_in_minutes = int((due_at - now).total_seconds() // 60) if due_at is not None else None
    if task.status == "completed":
        sla_status = "completed"
    elif due_at is None:
        sla_status = "unscheduled"
    elif due_in_minutes is not None and due_in_minutes < 0:
        sla_status = "overdue"
    elif due_in_minutes is not None and due_in_minutes <= 120:
        sla_status = "due_soon"
    else:
        sla_status = "on_track"

    return PatientTask(
        task_id=task.task_id,
        patient_id=task.patient_id,
        title=task.title,
        detail=task.detail,
        status=task.status,  # type: ignore[arg-type]
        priority=task.priority,  # type: ignore[arg-type]
        assignee_username=task.assignee_username,
        created_by=task.created_by,
        due_at=due_at,
        created_at=created_at,
        updated_at=updated_at,
        age_minutes=_elapsed_minutes(created_at, now=now),
        due_in_minutes=due_in_minutes,
        due_label=_task_due_label(status=task.status, due_at=due_at, due_in_minutes=due_in_minutes),
        is_overdue=sla_status == "overdue",
        is_due_soon=sla_status == "due_soon",
        sla_status=sla_status,  # type: ignore[arg-type]
        ownership_status="assigned" if task.assignee_username else "unassigned",
    )


def _handoff_to_schema(note: HandoffNoteORM) -> HandoffNote:
    created_at = _ensure_utc(note.created_at) or datetime.now(UTC)
    what_changed, pending_items, watch_items = _parse_handoff_details(note.details)
    return HandoffNote(
        note_id=note.note_id,
        patient_id=note.patient_id,
        author_username=note.author_username,
        summary=note.summary,
        details=note.details,
        created_at=created_at,
        what_changed=what_changed,
        pending_items=pending_items,
        watch_items=watch_items,
        freshness_minutes=_elapsed_minutes(created_at),
    )


def _patient_query(organization_id: int):
    return (
        select(PatientORM)
        .where(PatientORM.organization_id == organization_id)
        .options(
            selectinload(PatientORM.organization),
            selectinload(PatientORM.labs),
            selectinload(PatientORM.imaging_history),
            selectinload(PatientORM.alerts),
            selectinload(PatientORM.imaging_studies),
            selectinload(PatientORM.tasks),
            selectinload(PatientORM.handoff_notes),
        )
    )


def get_user_by_username(db: Session, username: str) -> UserORM | None:
    return db.scalars(select(UserORM).options(selectinload(UserORM.organization)).where(UserORM.username == username)).first()


def get_user_by_email(db: Session, email: str) -> UserORM | None:
    return db.scalars(select(UserORM).options(selectinload(UserORM.organization)).where(UserORM.email == email)).first()


def get_user_by_external_subject(db: Session, external_subject: str) -> UserORM | None:
    return db.scalars(
        select(UserORM).options(selectinload(UserORM.organization)).where(UserORM.external_subject == external_subject)
    ).first()


def update_last_login(db: Session, user: UserORM) -> UserProfile:
    user.last_login_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_profile(user)


def _validate_invite_for_registration(
    db: Session,
    registration: UserRegistrationRequest,
) -> tuple[int, OrganizationORM]:
    default_organization = get_or_create_default_organization(db)
    requested_role = registration.role
    invite_code = _normalize_optional_text(registration.invite_code)

    if requested_role == "clinician" and not invite_code:
        return default_organization.organization_id, default_organization

    if not invite_code:
        raise ValueError("An invite code is required for this role.")

    invite = db.scalars(
        select(InviteCodeORM)
        .where(
            InviteCodeORM.code_hash == hash_session_token(invite_code),
            InviteCodeORM.status == "pending",
        )
        .limit(1)
    ).first()
    if invite is None or invite.expires_at < datetime.now(UTC):
        raise ValueError("That invite code is not valid.")
    if invite.role != requested_role:
        raise ValueError("That invite code does not grant the requested role.")

    email = registration.email.strip().lower()
    if invite.email and invite.email.lower() != email:
        raise ValueError("That invite code is restricted to a different email address.")

    organization = db.get(OrganizationORM, invite.organization_id)
    if organization is None:
        raise ValueError("That invite code does not point to an active organization.")

    invite.status = "accepted"
    invite.accepted_at = datetime.now(UTC)
    db.add(invite)
    db.flush()
    return organization.organization_id, organization


def create_local_user(db: Session, registration: UserRegistrationRequest) -> UserProfile:
    requested_username = _normalize_optional_text(registration.username)
    email = registration.email.strip().lower()

    if requested_username and get_user_by_username(db, requested_username) is not None:
        raise ValueError("That username is already in use.")
    if get_user_by_email(db, email) is not None:
        raise ValueError("That email address is already in use.")

    organization_id, organization = _validate_invite_for_registration(db, registration)
    username = _ensure_unique_username(
        db,
        requested_username or email.split("@", maxsplit=1)[0] or registration.full_name,
    )

    now = datetime.now(UTC)
    user = UserORM(
        organization_id=organization_id,
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
            organization=organization.name,
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
        organization = get_or_create_default_organization(db)
        username = _ensure_unique_username(db, preferred_username or email or f"oidc-{external_subject[-8:]}")
        user = UserORM(
            organization_id=organization.organization_id,
            username=username,
            email=email.lower() if email else None,
            full_name=full_name,
            role=role,
            auth_provider=auth_provider,
            external_subject=external_subject,
            password_hash=hash_password(uuid4().hex),
            is_active=True,
            preferences=_build_user_preferences(role=role, organization=organization.name),
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )
        db.add(user)
    else:
        user.full_name = full_name
        # Only overwrite an admin-assigned role when explicitly configured.
        # Default behaviour preserves the role set by an administrator so that
        # SSO logins cannot silently demote or promote a user.
        if get_settings().oidc_override_role_on_login:
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
    for field in ("title", "department", "phone", "location", "bio"):
        value = getattr(payload, field)
        if value is not None:
            preferences[field] = _normalize_optional_text(value) if isinstance(value, str) else value

    if getattr(user, "organization", None) is not None:
        preferences["organization"] = user.organization.name
    if payload.dashboard_view is not None:
        preferences["dashboard_view"] = payload.dashboard_view.strip() or current_preferences.dashboard_view
    if payload.notification_preference is not None:
        preferences["notification_preference"] = payload.notification_preference.strip() or current_preferences.notification_preference
    if payload.last_selected_patient_id is not None:
        preferences["last_selected_patient_id"] = payload.last_selected_patient_id

    user.preferences = preferences
    user.updated_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_profile(user)


def create_user_session(
    db: Session,
    *,
    user: UserProfile,
    refresh_token: str,
    user_agent: str | None,
    ip_address: str | None,
    expires_days: int,
) -> SessionRecord:
    orm_user = get_user_by_username(db, user.username)
    if orm_user is None:
        raise ValueError("That user is not available.")

    now = datetime.now(UTC)
    session = UserSessionORM(
        session_id=uuid4().hex,
        user_id=orm_user.id,
        refresh_token_hash=hash_session_token(refresh_token),
        user_agent=user_agent[:255] if user_agent else None,
        ip_address=ip_address[:64] if ip_address else None,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=expires_days),
        revoked_at=None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_schema(session, session.session_id)


def get_user_session_by_refresh_token(db: Session, refresh_token: str) -> tuple[UserSessionORM | None, UserORM | None]:
    hashed = hash_session_token(refresh_token)
    session = db.scalars(
        select(UserSessionORM)
        .options(selectinload(UserSessionORM.user).selectinload(UserORM.organization))
        .where(UserSessionORM.refresh_token_hash == hashed)
        .limit(1)
    ).first()
    if session is None:
        return None, None
    expires_at = _ensure_utc(session.expires_at) or datetime.now(UTC)
    if session.revoked_at is not None or expires_at < datetime.now(UTC):
        return session, None
    return session, session.user


def rotate_user_session(db: Session, session_id: str, refresh_token: str, expires_days: int) -> SessionRecord:
    session = db.get(UserSessionORM, session_id)
    if session is None:
        raise ValueError("That session is not available.")
    now = datetime.now(UTC)
    session.refresh_token_hash = hash_session_token(refresh_token)
    session.last_used_at = now
    session.expires_at = now + timedelta(days=expires_days)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_schema(session, session.session_id)


def touch_user_session(db: Session, session_id: str) -> None:
    session = db.get(UserSessionORM, session_id)
    if session is None or session.revoked_at is not None:
        return
    session.last_used_at = datetime.now(UTC)
    db.add(session)
    db.commit()


def list_user_sessions(db: Session, user: UserProfile, current_session_id: str | None = None) -> list[SessionRecord]:
    orm_user = get_user_by_username(db, user.username)
    if orm_user is None:
        return []
    sessions = db.scalars(
        select(UserSessionORM)
        .where(UserSessionORM.user_id == orm_user.id)
        .order_by(desc(UserSessionORM.last_used_at))
    ).all()
    return [_session_to_schema(session, current_session_id) for session in sessions]


def revoke_user_session(db: Session, user: UserProfile, session_id: str) -> None:
    orm_user = get_user_by_username(db, user.username)
    if orm_user is None:
        return
    session = db.scalars(
        select(UserSessionORM).where(UserSessionORM.user_id == orm_user.id, UserSessionORM.session_id == session_id)
    ).first()
    if session is None or session.revoked_at is not None:
        return
    session.revoked_at = datetime.now(UTC)
    db.add(session)
    db.commit()


def revoke_all_user_sessions(db: Session, user: UserProfile) -> None:
    orm_user = get_user_by_username(db, user.username)
    if orm_user is None:
        return
    sessions = db.scalars(
        select(UserSessionORM)
        .where(UserSessionORM.user_id == orm_user.id, UserSessionORM.revoked_at.is_(None))
    ).all()
    now = datetime.now(UTC)
    for session in sessions:
        session.revoked_at = now
        db.add(session)
    if sessions:
        db.commit()


def create_invite_code(db: Session, actor: UserProfile, payload: InviteCodeCreateRequest) -> InviteCodeRecord:
    if actor.organization_id is None:
        raise ValueError("Your account is not attached to an organization.")
    raw_code = token_urlsafe(18)
    now = datetime.now(UTC)
    invite = InviteCodeORM(
        invite_id=uuid4().hex,
        organization_id=actor.organization_id,
        role=payload.role,
        email=payload.email.strip().lower() if payload.email else None,
        code_hash=hash_session_token(raw_code),
        status="pending",
        created_by_username=actor.username,
        created_at=now,
        expires_at=now + timedelta(days=payload.expires_in_days),
        accepted_at=None,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return _invite_to_schema(invite, raw_code)


def list_invite_codes(db: Session, actor: UserProfile, limit: int = 50) -> list[InviteCodeRecord]:
    if actor.organization_id is None:
        return []
    invites = db.scalars(
        select(InviteCodeORM)
        .where(InviteCodeORM.organization_id == actor.organization_id)
        .order_by(desc(InviteCodeORM.created_at))
        .limit(limit)
    ).all()
    return [_invite_to_schema(invite) for invite in invites]


def list_users(db: Session, actor: UserProfile, limit: int = 100) -> list[UserDirectoryEntry]:
    if actor.organization_id is None:
        return []
    users = db.scalars(
        select(UserORM)
        .options(selectinload(UserORM.organization))
        .where(UserORM.organization_id == actor.organization_id)
        .order_by(UserORM.role, UserORM.full_name)
        .limit(limit)
    ).all()
    return [_user_directory_entry(user) for user in users]


def _count_active_admins(db: Session, organization_id: int) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(UserORM)
        .where(
            UserORM.organization_id == organization_id,
            UserORM.role == "admin",
            UserORM.is_active.is_(True),
        )
    )
    return int(count or 0)


def update_user_active_state(db: Session, actor: UserProfile, username: str, is_active: bool) -> UserDirectoryEntry:
    if actor.organization_id is None:
        raise ValueError("Your account is not attached to an organization.")

    user = db.scalars(
        select(UserORM)
        .options(selectinload(UserORM.organization))
        .where(
            UserORM.organization_id == actor.organization_id,
            UserORM.username == username,
        )
        .limit(1)
    ).first()
    if user is None:
        raise ValueError("That user is not available.")

    if user.username == actor.username and not is_active:
        raise ValueError("Use another admin account to deactivate your own access.")

    if user.role == "admin" and user.is_active and not is_active and _count_active_admins(db, actor.organization_id) <= 1:
        raise ValueError("At least one active admin must remain in the organization.")

    user.is_active = is_active
    user.updated_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_directory_entry(user)


def update_user_role(db: Session, actor: UserProfile, username: str, role: str) -> UserDirectoryEntry:
    if actor.organization_id is None:
        raise ValueError("Your account is not attached to an organization.")
    if role not in {"admin", "clinician", "analyst"}:
        raise ValueError("That role cannot be assigned through the admin console.")

    user = db.scalars(
        select(UserORM)
        .options(selectinload(UserORM.organization))
        .where(
            UserORM.organization_id == actor.organization_id,
            UserORM.username == username,
        )
        .limit(1)
    ).first()
    if user is None:
        raise ValueError("That user is not available.")

    if user.username == actor.username and role != "admin":
        raise ValueError("Use another admin account to change your own admin role.")

    if user.role == "admin" and role != "admin" and user.is_active and _count_active_admins(db, actor.organization_id) <= 1:
        raise ValueError("At least one active admin must remain in the organization.")

    user.role = role
    user.updated_at = datetime.now(UTC)
    current_preferences = _coerce_preferences(user.preferences)
    next_preferences = current_preferences.model_dump()
    if getattr(user, "organization", None) is not None:
        next_preferences["organization"] = user.organization.name
    user.preferences = next_preferences
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_directory_entry(user)


def list_patients(db: Session, organization_id: int, query: str | None = None, limit: int = 200) -> list[PatientRecord]:
    statement = _patient_query(organization_id)
    if query:
        term = f"%{query.strip().lower()}%"
        statement = statement.where(
            or_(
                func.lower(PatientORM.name).like(term),
                func.lower(PatientORM.mrn).like(term),
                func.lower(PatientORM.diagnosis).like(term),
                func.lower(PatientORM.care_unit).like(term),
            )
        )
    records = db.scalars(statement.order_by(PatientORM.patient_id).limit(limit)).all()
    return [_patient_to_schema(record) for record in records]


def get_patient(db: Session, organization_id: int, patient_id: int) -> PatientRecord | None:
    record = db.scalars(_patient_query(organization_id).where(PatientORM.patient_id == patient_id)).first()
    if record is None:
        return None
    return _patient_to_schema(record)


def get_patient_record(db: Session, organization_id: int, patient_id: int) -> PatientORM | None:
    return db.scalars(_patient_query(organization_id).where(PatientORM.patient_id == patient_id)).first()


def list_alerts(db: Session, organization_id: int) -> list[Alert]:
    alerts = db.scalars(
        select(AlertORM).where(AlertORM.organization_id == organization_id).order_by(desc(AlertORM.created_at))
    ).all()
    return [_alert_to_schema(alert) for alert in alerts]


def acknowledge_alert(db: Session, organization_id: int, alert_id: str, username: str) -> Alert | None:
    """Mark an alert as acknowledged. Returns the updated alert, or None if not found."""
    alert = db.scalars(
        select(AlertORM).where(
            AlertORM.alert_id == alert_id,
            AlertORM.organization_id == organization_id,
        )
    ).first()
    if alert is None:
        return None
    alert.acknowledged = True
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return _alert_to_schema(alert)


def alerts_for_patient(db: Session, organization_id: int, patient_id: int) -> list[Alert]:
    alerts = db.scalars(
        select(AlertORM)
        .where(
            AlertORM.organization_id == organization_id,
            AlertORM.patient_id == patient_id,
            AlertORM.acknowledged.is_(False),
        )
        .order_by(desc(AlertORM.created_at))
    ).all()
    return [_alert_to_schema(alert) for alert in alerts]


def create_notification(
    db: Session,
    *,
    organization_id: int,
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
        organization_id=organization_id,
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
    organization_id: int,
    recipient_username: str,
    *,
    limit: int = 25,
    unread_only: bool = False,
) -> list[Notification]:
    query = select(NotificationORM).where(
        NotificationORM.organization_id == organization_id,
        NotificationORM.recipient_username == recipient_username,
    )
    if unread_only:
        query = query.where(NotificationORM.is_read.is_(False))
    notifications = db.scalars(query.order_by(desc(NotificationORM.created_at)).limit(limit)).all()
    return [_notification_to_schema(item) for item in notifications]


def mark_notification_read(
    db: Session,
    organization_id: int,
    notification_id: str,
    recipient_username: str,
) -> Notification | None:
    notification = db.scalars(
        select(NotificationORM).where(
            NotificationORM.organization_id == organization_id,
            NotificationORM.notification_id == notification_id,
            NotificationORM.recipient_username == recipient_username,
        )
    ).first()
    if notification is None:
        return None
    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return _notification_to_schema(notification)


def create_imaging_study(
    db: Session,
    *,
    organization_id: int,
    patient_id: int,
    filename: str,
    content_type: str,
    storage_uri: str,
    uploaded_by: str,
    analysis_payload: dict | None,
) -> ImagingStudyRecord:
    priority = _derive_imaging_priority(analysis_payload)
    study = ImagingStudyORM(
        study_id=str(uuid4()),
        organization_id=organization_id,
        patient_id=patient_id,
        filename=filename,
        content_type=content_type,
        storage_uri=storage_uri,
        uploaded_by=uploaded_by,
        priority=priority,
        review_status="pending_review",
        review_due_at=_derive_review_due_at(priority),
        review_notes=None,
        escalation_reason=None,
        reviewed_by=None,
        reviewed_at=None,
        signed_off_by=None,
        signed_off_at=None,
        analysis_payload=analysis_payload,
        created_at=datetime.now(UTC),
    )
    db.add(study)
    db.commit()
    db.refresh(study)
    return _imaging_study_to_schema(study)


def list_imaging_studies(db: Session, organization_id: int, patient_id: int, limit: int = 10) -> list[ImagingStudyRecord]:
    studies = db.scalars(
        select(ImagingStudyORM)
        .where(ImagingStudyORM.organization_id == organization_id, ImagingStudyORM.patient_id == patient_id)
        .order_by(desc(ImagingStudyORM.created_at))
        .limit(limit)
    ).all()
    return [_imaging_study_to_schema(study) for study in studies]


def get_imaging_study_record(db: Session, organization_id: int, study_id: str) -> ImagingStudyORM | None:
    return db.scalars(
        select(ImagingStudyORM).where(
            ImagingStudyORM.organization_id == organization_id,
            ImagingStudyORM.study_id == study_id,
        )
    ).first()


def update_imaging_study_review(
    db: Session,
    *,
    organization_id: int,
    study_id: str,
    actor_username: str,
    payload: ImagingStudyReviewRequest,
) -> ImagingStudyRecord | None:
    study = get_imaging_study_record(db, organization_id, study_id)
    if study is None:
        return None

    now = datetime.now(UTC)
    if payload.priority is not None:
        study.priority = payload.priority
    priority = getattr(study, "priority", "routine")

    if payload.review_notes is not None:
        study.review_notes = _normalize_optional_text(payload.review_notes)

    study.review_status = payload.review_status

    if payload.review_status == "pending_review":
        study.review_due_at = _derive_review_due_at(priority, reference=now)
        study.signed_off_by = None
        study.signed_off_at = None
        if payload.escalation_reason is not None:
            study.escalation_reason = _normalize_optional_text(payload.escalation_reason)
    elif payload.review_status == "reviewed":
        study.reviewed_by = actor_username
        study.reviewed_at = now
        study.review_due_at = now
        study.signed_off_by = None
        study.signed_off_at = None
        study.escalation_reason = None
    elif payload.review_status == "escalated":
        study.reviewed_by = actor_username
        study.reviewed_at = now
        study.review_due_at = now + timedelta(minutes=15)
        study.signed_off_by = None
        study.signed_off_at = None
        study.escalation_reason = (
            _normalize_optional_text(payload.escalation_reason) or "Escalated for additional clinical review."
        )
    elif payload.review_status == "signed_off":
        study.reviewed_by = study.reviewed_by or actor_username
        study.reviewed_at = study.reviewed_at or now
        study.review_due_at = now
        study.signed_off_by = actor_username
        study.signed_off_at = now
        if payload.escalation_reason is not None:
            study.escalation_reason = _normalize_optional_text(payload.escalation_reason)

    db.add(study)
    db.commit()
    db.refresh(study)
    return _imaging_study_to_schema(study)


def _imaging_workbench_sort_key(study: ImagingStudyORM) -> tuple[int, int, datetime, float]:
    status_order = {
        "escalated": 0,
        "pending_review": 1,
        "reviewed": 2,
        "signed_off": 3,
    }
    priority_order = {
        "urgent": 0,
        "priority": 1,
        "routine": 2,
    }
    due_at = _ensure_utc(getattr(study, "review_due_at", None)) or datetime.max.replace(tzinfo=UTC)
    created_at = _ensure_utc(study.created_at) or datetime.now(UTC)
    return (
        status_order.get(getattr(study, "review_status", "pending_review"), 9),
        priority_order.get(getattr(study, "priority", "routine"), 9),
        due_at,
        -created_at.timestamp(),
    )


def _linked_report_jobs_for_patients(db: Session, organization_id: int, patient_ids: set[int]) -> dict[int, list[ReportJobORM]]:
    if not patient_ids:
        return {}

    jobs = db.scalars(
        select(ReportJobORM)
        .where(ReportJobORM.organization_id == organization_id, ReportJobORM.patient_id.in_(patient_ids))
        .order_by(desc(ReportJobORM.created_at))
    ).all()
    grouped: dict[int, list[ReportJobORM]] = {}
    for job in jobs:
        grouped.setdefault(job.patient_id, []).append(job)
    return grouped


def build_imaging_workbench(
    db: Session,
    *,
    organization_id: int,
    limit: int = 24,
    review_status: str | None = None,
) -> ImagingWorkbench:
    statement = (
        select(ImagingStudyORM)
        .where(ImagingStudyORM.organization_id == organization_id)
        .options(
            selectinload(ImagingStudyORM.patient).selectinload(PatientORM.alerts),
            selectinload(ImagingStudyORM.patient).selectinload(PatientORM.tasks),
            selectinload(ImagingStudyORM.patient).selectinload(PatientORM.handoff_notes),
        )
    )
    if review_status and review_status != "all":
        statement = statement.where(ImagingStudyORM.review_status == review_status)

    studies = db.scalars(statement.order_by(desc(ImagingStudyORM.created_at)).limit(max(limit * 3, limit))).all()
    studies = sorted(studies, key=_imaging_workbench_sort_key)[:limit]
    patient_ids = {study.patient_id for study in studies}
    report_jobs_by_patient = _linked_report_jobs_for_patients(db, organization_id, patient_ids)

    items: list[ImagingWorkbenchItem] = []
    for study in studies:
        patient = study.patient
        if patient is None:
            continue

        study_schema = _imaging_study_to_schema(study)
        unresolved_alerts = sum(not alert.acknowledged for alert in patient.alerts)
        overdue_tasks = sum(
            1 for task in (_task_to_schema(task) for task in patient.tasks) if task.status != "completed" and task.is_overdue
        )
        related_jobs = report_jobs_by_patient.get(patient.patient_id, [])[:2]
        linked_reports = [
            ImagingLinkedReportJob(
                job_id=job.job_id,
                status=job.status,  # type: ignore[arg-type]
                workflow_stage=job.workflow_stage,
                progress_percent=job.progress_percent,
                created_at=_ensure_utc(job.created_at) or datetime.now(UTC),
            )
            for job in related_jobs
        ]

        if study_schema.review_status == "escalated":
            next_action = study_schema.escalation_reason or "Resolve the escalation and either review or sign off the study."
        elif study_schema.review_status == "pending_review":
            next_action = (
                study_schema.analysis.suggested_next_step
                if study_schema.analysis is not None
                else "Review the study and record the triage outcome."
            )
        elif study_schema.review_status == "reviewed":
            next_action = "Sign off the study or escalate it if the report package needs more review."
        else:
            next_action = "Study signed off. Continue routine workflow monitoring."

        items.append(
            ImagingWorkbenchItem(
                study=study_schema,
                patient_name=patient.name,
                care_unit=patient.care_unit,
                diagnosis=patient.diagnosis,
                risk_band=_patient_to_schema(patient).risk_band,  # type: ignore[arg-type]
                unresolved_alerts=unresolved_alerts,
                overdue_tasks=overdue_tasks,
                next_action=next_action,
                linked_reports=linked_reports,
            )
        )

    return ImagingWorkbench(
        generated_at=datetime.now(UTC),
        summary=ImagingWorkbenchSummary(
            total=len(items),
            pending_review=sum(item.study.review_status == "pending_review" for item in items),
            reviewed=sum(item.study.review_status == "reviewed" for item in items),
            escalated=sum(item.study.review_status == "escalated" for item in items),
            signed_off=sum(item.study.review_status == "signed_off" for item in items),
            urgent=sum(item.study.priority == "urgent" for item in items),
            priority=sum(item.study.priority in {"urgent", "priority"} for item in items),
            overdue=sum(item.study.is_review_overdue for item in items),
        ),
        items=items,
    )


def create_report_job(
    db: Session,
    *,
    organization_id: int,
    patient_id: int,
    requested_by: str | None = None,
    max_attempts: int = 3,
    idempotency_key: str | None = None,
) -> ReportJob:
    if idempotency_key:
        existing = db.scalars(
            select(ReportJobORM)
            .where(
                ReportJobORM.organization_id == organization_id,
                ReportJobORM.idempotency_key == idempotency_key,
            )
            .order_by(desc(ReportJobORM.created_at))
            .limit(1)
        ).first()
        if existing is not None:
            return _report_job_to_schema(existing)

    now = datetime.now(UTC)
    job = ReportJobORM(
        job_id=str(uuid4()),
        organization_id=organization_id,
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
        idempotency_key=idempotency_key,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _report_job_to_schema(job)


def get_report_job(db: Session, organization_id: int, job_id: str) -> ReportJob | None:
    job = db.scalars(
        select(ReportJobORM).where(ReportJobORM.organization_id == organization_id, ReportJobORM.job_id == job_id)
    ).first()
    if job is None:
        return None
    return _report_job_to_schema(job)


def get_report_job_record(db: Session, organization_id: int, job_id: str) -> ReportJobORM | None:
    return db.scalars(
        select(ReportJobORM).where(ReportJobORM.organization_id == organization_id, ReportJobORM.job_id == job_id)
    ).first()


def list_report_jobs(db: Session, organization_id: int, limit: int = 25) -> list[ReportJob]:
    jobs = db.scalars(
        select(ReportJobORM)
        .where(ReportJobORM.organization_id == organization_id)
        .order_by(desc(ReportJobORM.created_at))
        .limit(limit)
    ).all()
    return [_report_job_to_schema(job) for job in jobs]


def create_care_task(
    db: Session,
    *,
    user: UserProfile,
    patient_id: int,
    payload: PatientTaskCreateRequest,
) -> PatientTask:
    if user.organization_id is None:
        raise ValueError("Your account is not attached to an organization.")
    patient = get_patient_record(db, user.organization_id, patient_id)
    if patient is None:
        raise ValueError("That patient is not available.")
    now = datetime.now(UTC)
    task = CareTaskORM(
        task_id=uuid4().hex,
        organization_id=user.organization_id,
        patient_id=patient_id,
        title=payload.title.strip(),
        detail=payload.detail.strip(),
        status="open",
        priority=payload.priority,
        assignee_username=_normalize_optional_text(payload.assignee_username),
        created_by=user.username,
        due_at=_ensure_utc(payload.due_at),
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_schema(task)


def list_patient_tasks(db: Session, organization_id: int, patient_id: int) -> list[PatientTask]:
    tasks = db.scalars(
        select(CareTaskORM)
        .where(CareTaskORM.organization_id == organization_id, CareTaskORM.patient_id == patient_id)
        .order_by(desc(CareTaskORM.updated_at))
    ).all()
    return [_task_to_schema(task) for task in tasks]


def update_patient_task(
    db: Session,
    *,
    user: UserProfile,
    patient_id: int,
    task_id: str,
    payload: PatientTaskUpdateRequest,
) -> PatientTask | None:
    if user.organization_id is None:
        return None
    task = db.scalars(
        select(CareTaskORM).where(
            CareTaskORM.organization_id == user.organization_id,
            CareTaskORM.patient_id == patient_id,
            CareTaskORM.task_id == task_id,
        )
    ).first()
    if task is None:
        return None
    for field in ("title", "detail"):
        value = getattr(payload, field)
        if value is not None:
            setattr(task, field, value.strip())
    if payload.status is not None:
        task.status = payload.status
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.assignee_username is not None:
        task.assignee_username = _normalize_optional_text(payload.assignee_username)
    if payload.due_at is not None:
        task.due_at = _ensure_utc(payload.due_at)
    task.updated_at = datetime.now(UTC)
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_schema(task)


def create_handoff_note(
    db: Session,
    *,
    user: UserProfile,
    patient_id: int,
    payload: HandoffNoteCreateRequest,
) -> HandoffNote:
    if user.organization_id is None:
        raise ValueError("Your account is not attached to an organization.")
    patient = get_patient_record(db, user.organization_id, patient_id)
    if patient is None:
        raise ValueError("That patient is not available.")
    note = HandoffNoteORM(
        note_id=uuid4().hex,
        organization_id=user.organization_id,
        patient_id=patient_id,
        author_username=user.username,
        summary=payload.summary.strip(),
        details=payload.details.strip(),
        created_at=datetime.now(UTC),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _handoff_to_schema(note)


def list_handoff_notes(db: Session, organization_id: int, patient_id: int, limit: int = 12) -> list[HandoffNote]:
    notes = db.scalars(
        select(HandoffNoteORM)
        .where(HandoffNoteORM.organization_id == organization_id, HandoffNoteORM.patient_id == patient_id)
        .order_by(desc(HandoffNoteORM.created_at))
        .limit(limit)
    ).all()
    return [_handoff_to_schema(note) for note in notes]


def build_patient_timeline(db: Session, organization_id: int, patient_id: int, limit: int = 40) -> list[PatientTimelineEvent]:
    patient = get_patient_record(db, organization_id, patient_id)
    if patient is None:
        return []

    timeline: list[PatientTimelineEvent] = []
    for lab in sorted(patient.labs, key=lambda item: item.collected_at, reverse=True):
        timeline.append(
            PatientTimelineEvent(
                event_id=f"lab-{lab.id}",
                patient_id=patient_id,
                category="lab",
                label=lab.name,
                summary=f"{lab.value} {lab.unit}",
                created_at=_ensure_utc(lab.collected_at) or datetime.now(UTC),
                detail={"unit": lab.unit, "value": lab.value},
            )
        )
    for imaging in sorted(patient.imaging_history, key=lambda item: item.captured_at, reverse=True):
        timeline.append(
            PatientTimelineEvent(
                event_id=f"finding-{imaging.id}",
                patient_id=patient_id,
                category="imaging",
                label=imaging.modality,
                summary=imaging.summary,
                created_at=_ensure_utc(imaging.captured_at) or datetime.now(UTC),
                detail={"confidence": imaging.confidence},
            )
        )
    alerts = db.scalars(
        select(AlertORM)
        .where(AlertORM.organization_id == organization_id, AlertORM.patient_id == patient_id)
        .order_by(desc(AlertORM.created_at))
        .limit(limit)
    ).all()
    for alert in alerts:
        timeline.append(
            PatientTimelineEvent(
                event_id=f"alert-{alert.alert_id}",
                patient_id=patient_id,
                category="alert",
                label=alert.title,
                summary=alert.description,
                created_at=_ensure_utc(alert.created_at) or datetime.now(UTC),
                detail={"severity": alert.severity, "acknowledged": alert.acknowledged},
            )
        )
    jobs = db.scalars(
        select(ReportJobORM)
        .where(ReportJobORM.organization_id == organization_id, ReportJobORM.patient_id == patient_id)
        .order_by(desc(ReportJobORM.created_at))
        .limit(limit)
    ).all()
    for job in jobs:
        timeline.append(
            PatientTimelineEvent(
                event_id=f"report-{job.job_id}",
                patient_id=patient_id,
                category="report",
                label="Patient briefing",
                summary=f"{job.workflow_stage.replace('_', ' ')} | {job.status}",
                created_at=_ensure_utc(job.created_at) or datetime.now(UTC),
                detail={"job_id": job.job_id, "status": job.status},
            )
        )
    notifications = db.scalars(
        select(NotificationORM)
        .where(NotificationORM.organization_id == organization_id, NotificationORM.patient_id == patient_id)
        .order_by(desc(NotificationORM.created_at))
        .limit(limit)
    ).all()
    for notification in notifications:
        timeline.append(
            PatientTimelineEvent(
                event_id=f"notification-{notification.notification_id}",
                patient_id=patient_id,
                category="notification",
                label=notification.title,
                summary=notification.body,
                created_at=_ensure_utc(notification.created_at) or datetime.now(UTC),
                detail=notification.detail,
            )
        )
    for task in list_patient_tasks(db, organization_id, patient_id):
        timeline.append(
            PatientTimelineEvent(
                event_id=f"task-{task.task_id}",
                patient_id=patient_id,
                category="task",
                label=task.title,
                summary=f"{task.status.replace('_', ' ')} | {task.priority}",
                created_at=task.updated_at,
                detail={"assignee": task.assignee_username, "detail": task.detail},
            )
        )
    for note in list_handoff_notes(db, organization_id, patient_id, limit=limit):
        timeline.append(
            PatientTimelineEvent(
                event_id=f"handoff-{note.note_id}",
                patient_id=patient_id,
                category="handoff",
                label=note.summary,
                summary=note.details,
                created_at=note.created_at,
                detail={"author": note.author_username},
            )
        )

    timeline.sort(key=lambda item: item.created_at, reverse=True)
    return timeline[:limit]


def get_analytics_overview(db: Session, user: UserProfile, settings: Settings) -> AnalyticsOverview:
    if user.organization_id is None:
        return AnalyticsOverview(
            total_patients=0,
            open_alerts=0,
            critical_alerts=0,
            unread_notifications=0,
            report_queue=ReportQueueSummary(queued=0, running=0, completed=0, failed=0),
            care_units=[],
            capabilities=SystemCapability(
                task_execution_mode=settings.task_execution_mode,
                storage_backend=settings.resolved_storage_backend,
                oidc_enabled=federated_auth_enabled(settings),
                metrics_enabled=settings.metrics_enabled,
                live_updates_enabled=True,
            ),
        )

    patients = db.scalars(
        select(PatientORM)
        .where(PatientORM.organization_id == user.organization_id)
        .order_by(PatientORM.care_unit, PatientORM.patient_id)
    ).all()
    alerts = db.scalars(
        select(AlertORM)
        .where(AlertORM.organization_id == user.organization_id, AlertORM.acknowledged.is_(False))
    ).all()
    jobs = db.scalars(select(ReportJobORM).where(ReportJobORM.organization_id == user.organization_id)).all()

    unread_notifications = db.scalar(
        select(func.count())
        .select_from(NotificationORM)
        .where(
            NotificationORM.organization_id == user.organization_id,
            NotificationORM.recipient_username == user.username,
            NotificationORM.is_read.is_(False),
        )
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
    active_jobs = list_report_jobs(db, current_user.organization_id or 0, limit=limit) if current_user.organization_id else []
    latest_alerts = list_alerts(db, current_user.organization_id or 0)[:limit] if current_user.organization_id else []
    latest_notifications = (
        list_notifications(db, current_user.organization_id or 0, recipient_username=current_user.username, limit=limit)
        if current_user.organization_id
        else []
    )
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


def list_audit_logs(db: Session, actor: UserProfile, limit: int = 50) -> list[AuditLogEntry]:
    if actor.organization_id is None:
        return []
    logs = db.scalars(
        select(AuditLogORM)
        .where(or_(AuditLogORM.organization_id == actor.organization_id, AuditLogORM.organization_id.is_(None)))
        .order_by(desc(AuditLogORM.created_at))
        .limit(limit)
    ).all()
    return [
        AuditLogEntry(
            audit_id=log.audit_id,
            request_id=log.request_id,
            actor_username=log.actor_username,
            actor_role=log.actor_role,  # type: ignore[arg-type]
            method=log.method,
            path=log.path,
            status_code=log.status_code,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            detail=log.detail,
            created_at=_ensure_utc(log.created_at) or datetime.now(UTC),
        )
        for log in logs
    ]


def create_audit_log(
    db: Session,
    *,
    organization_id: int | None,
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
            organization_id=organization_id,
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


def issue_refresh_token() -> str:
    return create_refresh_token_value()
