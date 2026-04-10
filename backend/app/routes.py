from __future__ import annotations

import asyncio
import json
import logging

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.observability import record_imaging_analysis, record_login, render_metrics
from backend.app.core.oidc import (
    federated_auth_enabled,
    fetch_federated_userinfo,
    get_auth_provider_catalog,
    get_oauth_client,
    get_oidc_client,
    oidc_enabled,
    provider_enabled,
    resolve_federated_identity,
    resolve_federated_role,
)
from backend.app.core.rate_limit import enforce_rate_limit
from backend.app.core.security import (
    authenticate_user,
    get_current_session_id,
    get_current_user,
    issue_access_token,
    issue_stream_token,
    require_roles,
    resolve_stream_user,
)
from backend.app.db.enterprise_repository import (
    acknowledge_alert,
    build_imaging_workbench,
    build_operations_live_snapshot,
    build_patient_timeline,
    create_care_task,
    create_handoff_note,
    create_imaging_study,
    create_invite_code,
    create_local_user,
    create_or_update_federated_user,
    create_user_session,
    get_analytics_overview,
    get_imaging_study_record,
    get_user_session_by_refresh_token,
    issue_refresh_token,
    list_alerts,
    list_audit_logs,
    list_handoff_notes,
    list_imaging_studies,
    list_invite_codes,
    list_notifications,
    list_patient_tasks,
    list_user_sessions,
    list_users,
    mark_notification_read,
    revoke_all_user_sessions,
    revoke_user_session,
    rotate_user_session,
    touch_user_session,
    update_user_active_state,
    update_imaging_study_review,
    update_user_role,
    update_patient_task,
    update_user_profile,
    user_to_profile,
)
from backend.app.db.repository import prune_audit_logs, prune_notifications, prune_report_jobs
from backend.app.db.session import SessionLocal, get_db
from backend.app.ml_utils import analyze_imaging, get_model_registry
from backend.app.models import (
    Alert,
    AnalyticsOverview,
    AuditLogEntry,
    AuthProviderCatalog,
    DiseaseRiskResponse,
    HandoffNote,
    HandoffNoteCreateRequest,
    IcuRiskResponse,
    ImagingAnalysisResponse,
    ImagingStudyRecord,
    ImagingStudyReviewRequest,
    ImagingWorkbench,
    InviteCodeCreateRequest,
    InviteCodeRecord,
    ModelRegistryEntry,
    Notification,
    OperationsLiveSnapshot,
    PatientRecord,
    PatientSummary,
    PatientTask,
    PatientTaskCreateRequest,
    PatientTaskUpdateRequest,
    PatientTimelineEvent,
    PopulationOperationsBoard,
    ReportJob,
    SessionRecord,
    StreamTokenResponse,
    TokenResponse,
    TreatmentRecommendation,
    UserDirectoryEntry,
    UserProfile,
    UserProfileUpdateRequest,
    UserRegistrationRequest,
    UserRoleUpdateRequest,
    UserStatusUpdateRequest,
)
from backend.app.services.notification_service import notify_imaging_triage
from backend.app.services.patient_service import (
    build_population_operations_board,
    get_disease_prediction,
    get_icu_prediction,
    get_patient_or_404,
    get_patient_summary,
    get_treatment_plan,
    list_patient_records,
)
from backend.app.services.storage import get_storage_service
from backend.app.services.upload_guard import validate_imaging_upload
from backend.app.tasks import dispatch_report_job, enqueue_report_job, fetch_report_job, list_recent_report_jobs, run_report_dispatch_cycle

_log = logging.getLogger("healthsphere.routes")

public_router = APIRouter()
secured_router = APIRouter()

CLINICAL_ACCESS = Depends(require_roles("admin", "clinician", "analyst", "service"))
REPORTING_ACCESS = Depends(require_roles("admin", "clinician", "service"))
MODEL_ACCESS = Depends(require_roles("admin", "analyst", "clinician", "service"))
ADMIN_ACCESS = Depends(require_roles("admin"))


def _request_ip(request: Request) -> str:
    """Extract the originating client IP from the request.

    Prefers the leftmost address in X-Forwarded-For (set by trusted proxies),
    then X-Real-IP, then the direct connection address.  IPv6 addresses are
    returned as-is (e.g. ``::1``) without stripping ports.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first (leftmost) address — the original client
        candidate = forwarded_for.split(",")[0].strip()
        if candidate:
            # For IPv4 with port (1.2.3.4:12345) strip the port portion.
            # IPv6 literals may be "::1" or "[::1]:port" — handle both.
            if candidate.startswith("["):
                # "[::1]:port" format → extract the address inside brackets
                bracket_end = candidate.find("]")
                if bracket_end != -1:
                    return candidate[1:bracket_end]
            if "." in candidate and ":" in candidate:
                # IPv4 with port: "1.2.3.4:12345"
                return candidate.rsplit(":", 1)[0]
            return candidate

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    return request.client.host if request.client else "unknown"


def _set_auth_cookies(response: Response, token_response: TokenResponse, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.access_cookie_name,
        value=token_response.access_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_same_site,
        max_age=token_response.expires_in,
        path="/",
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_same_site,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.access_cookie_name, path="/")
    response.delete_cookie(settings.refresh_cookie_name, path="/")


def _issue_session_bundle(db: Session, request: Request, user: UserProfile) -> tuple[TokenResponse, str]:
    settings = get_settings()
    refresh_token = issue_refresh_token()
    session = create_user_session(
        db,
        user=user,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_request_ip(request),
        expires_days=settings.refresh_token_expire_days,
    )
    token_response = issue_access_token(user, session.session_id)
    return token_response, refresh_token


def _require_organization_id(current_user: UserProfile) -> int:
    if current_user.organization_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account is not attached to an organization.")
    return current_user.organization_id


def _authorize_internal_request(request: Request) -> None:
    settings = get_settings()
    token = request.headers.get("authorization", "")
    bearer = token.split(" ", maxsplit=1)[1].strip() if token.lower().startswith("bearer ") and " " in token else ""
    service_key = request.headers.get("x-api-key", "")

    if settings.cron_secret and len(settings.cron_secret) >= 16 and bearer == settings.cron_secret:
        return
    if service_key and service_key == settings.service_api_key and settings.service_api_key not in {"change-me-service-key"}:
        return
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Internal request authentication failed.")


async def _start_federated_login(provider: str, request: Request):
    normalized_provider = provider.strip().lower()
    if normalized_provider == "google":
        if not oidc_enabled():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google sign-in is not enabled.")
        client = get_oidc_client()
        redirect_uri = request.url_for("oidc_callback")
    else:
        if not provider_enabled(normalized_provider):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{normalized_provider.title()} sign-in is not enabled.")
        client = get_oauth_client(normalized_provider)
        redirect_uri = request.url_for("oauth_provider_callback", provider=normalized_provider)

    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Provider client is not available.")
    return await client.authorize_redirect(request, str(redirect_uri))


async def _complete_federated_login(provider: str, request: Request, db: Session):
    normalized_provider = provider.strip().lower()
    settings = get_settings()

    if normalized_provider == "google":
        client = get_oidc_client()
        unavailable_detail = "Google sign-in is not enabled."
    else:
        client = get_oauth_client(normalized_provider)
        unavailable_detail = f"{normalized_provider.title()} sign-in is not enabled."

    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=unavailable_detail)

    try:
        token = await client.authorize_access_token(request)
    except Exception as exc:  # pragma: no cover - external identity integration
        _log.warning(
            "federated-login-failed",
            extra={"provider": normalized_provider, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{normalized_provider.title()} sign-in failed. Please try again or contact support.",
        ) from exc

    userinfo = await fetch_federated_userinfo(normalized_provider, request, token, client)
    subject, email, preferred_username, full_name = resolve_federated_identity(normalized_provider, userinfo)
    role = resolve_federated_role(userinfo, settings)
    user = create_or_update_federated_user(
        db,
        external_subject=f"{normalized_provider}:{subject}",
        email=email,
        preferred_username=preferred_username,
        full_name=full_name,
        role=role,
        auth_provider=normalized_provider,
    )
    token_response, refresh_token = _issue_session_bundle(db, request, user)
    record_login(normalized_provider)

    request.state.actor_username = user.username
    request.state.actor_role = user.role
    request.state.organization_id = user.organization_id
    request.state.audit_detail = {"event": "login", "provider": normalized_provider}

    redirect_target = f"{settings.frontend_app_url.rstrip('/')}/auth/callback?provider={normalized_provider}"
    response = RedirectResponse(url=redirect_target, status_code=status.HTTP_302_FOUND)
    _set_auth_cookies(response, token_response, refresh_token)
    return response


@public_router.get("/auth/providers", response_model=AuthProviderCatalog, tags=["auth"])
def auth_providers(request: Request) -> AuthProviderCatalog:
    return get_auth_provider_catalog(request)


@public_router.post("/auth/token", response_model=TokenResponse, tags=["auth"])
def login_for_access_token(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    if not settings.is_local_like:
        enforce_rate_limit(
            f"auth:login:{_request_ip(request)}",
            limit=settings.rate_limit_login_attempts,
            window_seconds=settings.rate_limit_window_seconds,
            detail="Too many sign-in attempts. Please wait and try again.",
        )

    user = authenticate_user(db, form_data.username, form_data.password)
    if user is None:
        _log.warning(
            "login-failed",
            extra={"username": form_data.username, "ip": _request_ip(request)},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")

    token_response, refresh_token = _issue_session_bundle(db, request, user)
    _set_auth_cookies(response, token_response, refresh_token)

    request.state.actor_username = user.username
    request.state.actor_role = user.role
    request.state.organization_id = user.organization_id
    request.state.audit_detail = {"event": "login", "provider": "password"}
    record_login("password")
    return token_response


@public_router.post("/auth/signup", response_model=TokenResponse, tags=["auth"])
def signup(
    request: Request,
    response: Response,
    payload: UserRegistrationRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    if not settings.is_local_like:
        enforce_rate_limit(
            f"auth:signup:{_request_ip(request)}",
            limit=settings.rate_limit_signup_attempts,
            window_seconds=settings.rate_limit_window_seconds,
            detail="Too many account creation attempts. Please wait and try again.",
        )

    try:
        user = create_local_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    token_response, refresh_token = _issue_session_bundle(db, request, user)
    _set_auth_cookies(response, token_response, refresh_token)

    request.state.actor_username = user.username
    request.state.actor_role = user.role
    request.state.organization_id = user.organization_id
    request.state.audit_detail = {"event": "signup", "provider": "password"}
    record_login("password")
    return token_response


@public_router.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
def refresh_auth_session(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    if not raw_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh credentials were not provided.")

    session, user = get_user_session_by_refresh_token(db, raw_refresh)
    if session is None or user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh credentials are not valid.")

    new_refresh_token = issue_refresh_token()
    rotate_user_session(db, session.session_id, new_refresh_token, settings.refresh_token_expire_days)
    user_profile = user_to_profile(user)
    token_response = issue_access_token(user_profile, session.session_id)
    _set_auth_cookies(response, token_response, new_refresh_token)

    request.state.actor_username = user_profile.username
    request.state.actor_role = user_profile.role
    request.state.organization_id = user_profile.organization_id
    request.state.audit_detail = {"event": "token_refreshed"}
    return token_response


@public_router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    settings = get_settings()
    raw_refresh = request.cookies.get(settings.refresh_cookie_name)
    if raw_refresh:
        session, user = get_user_session_by_refresh_token(db, raw_refresh)
        if session is not None and user is not None:
            revoke_user_session(db, user_to_profile(user), session.session_id)
            request.state.actor_username = user.username
            request.state.actor_role = user.role
            request.state.organization_id = user.organization_id
            request.state.audit_detail = {"event": "logout", "session_id": session.session_id}
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@public_router.get("/auth/oidc/login", name="oidc_login", tags=["auth"])
async def oidc_login(request: Request):
    return await _start_federated_login("google", request)


@public_router.get("/auth/oidc/callback", name="oidc_callback", tags=["auth"])
async def oidc_callback(request: Request, db: Session = Depends(get_db)):
    return await _complete_federated_login("google", request, db)


@public_router.get("/auth/oauth/{provider}/login", name="oauth_provider_login", tags=["auth"])
async def oauth_provider_login(provider: str, request: Request):
    return await _start_federated_login(provider, request)


@public_router.get("/auth/oauth/{provider}/callback", name="oauth_provider_callback", tags=["auth"])
async def oauth_provider_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    return await _complete_federated_login(provider, request, db)


@secured_router.get("/auth/me", response_model=UserProfile, tags=["auth"])
def auth_me(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> UserProfile:
    session_id = get_current_session_id(request)
    if session_id:
        touch_user_session(db, session_id)
    return current_user


@secured_router.patch("/auth/me", response_model=UserProfile, tags=["auth"])
def update_auth_me(
    request: Request,
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> UserProfile:
    try:
        user = update_user_profile(db, username=current_user.username, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    request.state.actor_username = user.username
    request.state.actor_role = user.role
    request.state.organization_id = user.organization_id
    request.state.audit_detail = {"event": "profile_updated"}
    return user


@secured_router.get("/auth/sessions", response_model=list[SessionRecord], tags=["auth"])
def auth_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> list[SessionRecord]:
    return list_user_sessions(db, current_user, get_current_session_id(request))


@secured_router.post("/auth/sessions/{session_id}/revoke", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def revoke_auth_session(
    session_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> Response:
    revoke_user_session(db, current_user, session_id)
    if get_current_session_id(request) == session_id:
        _clear_auth_cookies(response)
    request.state.audit_detail = {"event": "session_revoked", "session_id": session_id}
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@secured_router.post("/auth/sessions/revoke-all", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
def revoke_all_auth_sessions(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> Response:
    revoke_all_user_sessions(db, current_user)
    _clear_auth_cookies(response)
    request.state.audit_detail = {"event": "all_sessions_revoked"}
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@secured_router.get("/events/stream-token", response_model=StreamTokenResponse, tags=["operations"])
def operations_stream_token(
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = Depends(get_current_user),
) -> StreamTokenResponse:
    settings = get_settings()
    # Rate-limit stream token generation to prevent token enumeration / spray
    enforce_rate_limit(
        f"stream-token:{current_user.username}:{_request_ip(request)}",
        limit=30,
        window_seconds=settings.rate_limit_window_seconds,
        detail="Too many stream token requests. Please wait and try again.",
    )
    session_id = get_current_session_id(request)
    if session_id:
        touch_user_session(db, session_id)
    return issue_stream_token(current_user, session_id)


@public_router.get("/health/live", tags=["health"])
def live_health() -> dict[str, str]:
    return {"status": "live"}


@public_router.get("/health/ready", tags=["health"])
def ready_health(db: Session = Depends(get_db)) -> dict[str, object]:
    settings = get_settings()
    db.execute(text("SELECT 1"))
    model_entries = get_model_registry()

    redis_status = "disabled"
    if settings.resolved_rate_limit_backend == "redis" or settings.task_execution_mode == "celery":
        try:
            from redis import Redis
            from redis.exceptions import RedisError
            redis_url = settings.resolved_rate_limit_redis_url or settings.celery_broker_url
            r = Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
            r.ping()
            redis_status = "ok"
        except Exception:  # noqa: BLE001
            redis_status = "unavailable"
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis is unavailable.",
            )

    return {
        "status": "ready",
        "database": "ok",
        "redis": redis_status,
        "models_loaded": sum(1 for item in model_entries if item.artifact_available),
        "models_total": len(model_entries),
        "task_execution_mode": settings.task_execution_mode,
        "storage_backend": settings.resolved_storage_backend,
        "oidc_enabled": federated_auth_enabled(settings),
        "metrics_enabled": settings.metrics_enabled,
        "live_updates_enabled": True,
    }


@public_router.get("/metrics", tags=["observability"])
def metrics() -> Response:
    settings = get_settings()
    if not settings.metrics_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrics are disabled.")
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)


@secured_router.get("/patients", response_model=list[PatientRecord], tags=["patients"])
def list_patients_endpoint(
    query: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> list[PatientRecord]:
    return list_patient_records(db, current_user, query=query, limit=limit)


@secured_router.get("/patients/{patient_id}", response_model=PatientRecord, tags=["patients"])
def get_patient_endpoint(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> PatientRecord:
    return get_patient_or_404(db, patient_id, current_user)


@secured_router.get("/patients/{patient_id}/summary", response_model=PatientSummary, tags=["patients"])
def get_patient_summary_endpoint(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> PatientSummary:
    return get_patient_summary(db, patient_id, current_user)


@secured_router.get("/patients/{patient_id}/timeline", response_model=list[PatientTimelineEvent], tags=["patients"])
def get_patient_timeline_endpoint(
    patient_id: int,
    limit: int = Query(default=40, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> list[PatientTimelineEvent]:
    organization_id = _require_organization_id(current_user)
    get_patient_or_404(db, patient_id, current_user)
    return build_patient_timeline(db, organization_id, patient_id, limit=limit)


@secured_router.get("/patients/{patient_id}/tasks", response_model=list[PatientTask], tags=["patients"])
def get_patient_tasks_endpoint(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> list[PatientTask]:
    organization_id = _require_organization_id(current_user)
    get_patient_or_404(db, patient_id, current_user)
    return list_patient_tasks(db, organization_id, patient_id)


@secured_router.post("/patients/{patient_id}/tasks", response_model=PatientTask, tags=["patients"])
def create_patient_task_endpoint(
    patient_id: int,
    payload: PatientTaskCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> PatientTask:
    try:
        task = create_care_task(db, user=current_user, patient_id=patient_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.state.audit_detail = {"event": "task_created", "patient_id": patient_id, "task_id": task.task_id}
    return task


@secured_router.patch("/patients/{patient_id}/tasks/{task_id}", response_model=PatientTask, tags=["patients"])
def update_patient_task_endpoint(
    patient_id: int,
    task_id: str,
    payload: PatientTaskUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> PatientTask:
    task = update_patient_task(db, user=current_user, patient_id=patient_id, task_id=task_id, payload=payload)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} was not found.")
    request.state.audit_detail = {"event": "task_updated", "patient_id": patient_id, "task_id": task_id}
    return task


@secured_router.get("/patients/{patient_id}/handoffs", response_model=list[HandoffNote], tags=["patients"])
def list_patient_handoffs_endpoint(
    patient_id: int,
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> list[HandoffNote]:
    organization_id = _require_organization_id(current_user)
    get_patient_or_404(db, patient_id, current_user)
    return list_handoff_notes(db, organization_id, patient_id, limit=limit)


@secured_router.post("/patients/{patient_id}/handoffs", response_model=HandoffNote, tags=["patients"])
def create_patient_handoff_endpoint(
    patient_id: int,
    payload: HandoffNoteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> HandoffNote:
    try:
        note = create_handoff_note(db, user=current_user, patient_id=patient_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.state.audit_detail = {"event": "handoff_created", "patient_id": patient_id, "note_id": note.note_id}
    return note


@secured_router.get("/patients/{patient_id}/imaging/studies", response_model=list[ImagingStudyRecord], tags=["imaging"])
def patient_imaging_studies(
    patient_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> list[ImagingStudyRecord]:
    organization_id = _require_organization_id(current_user)
    get_patient_or_404(db, patient_id, current_user)
    return list_imaging_studies(db, organization_id, patient_id=patient_id, limit=limit)


@secured_router.get("/imaging/workbench", response_model=ImagingWorkbench, tags=["imaging"])
def imaging_workbench(
    limit: int = Query(default=24, ge=1, le=100),
    review_status: str = Query(default="all"),
    db: Session = Depends(get_db),
    current_user: UserProfile = REPORTING_ACCESS,
) -> ImagingWorkbench:
    return build_imaging_workbench(
        db,
        organization_id=_require_organization_id(current_user),
        limit=limit,
        review_status=review_status,
    )


@secured_router.get("/predict/icu/{patient_id}", response_model=IcuRiskResponse, tags=["predictions"])
def icu_risk(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> IcuRiskResponse:
    return get_icu_prediction(db, patient_id, current_user)


@secured_router.get("/predict/disease/{patient_id}", response_model=DiseaseRiskResponse, tags=["predictions"])
def disease_risk(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> DiseaseRiskResponse:
    return get_disease_prediction(db, patient_id, current_user)


@secured_router.get("/predict/treatment/{patient_id}", response_model=TreatmentRecommendation, tags=["predictions"])
def treatment_plan(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> TreatmentRecommendation:
    return get_treatment_plan(db, patient_id, current_user)


@secured_router.post("/analyze/imaging", response_model=ImagingAnalysisResponse, tags=["imaging"])
async def imaging(
    request: Request,
    file: UploadFile = File(...),
    patient_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: UserProfile = REPORTING_ACCESS,
) -> ImagingAnalysisResponse:
    settings = get_settings()
    if not settings.is_local_like:
        enforce_rate_limit(
            f"upload:{current_user.username}:{_request_ip(request)}",
            limit=settings.rate_limit_upload_attempts,
            window_seconds=settings.rate_limit_window_seconds,
            detail="Too many imaging uploads. Please wait and try again.",
        )

    organization_id = _require_organization_id(current_user)
    resolved_patient_id = patient_id
    get_patient_or_404(db, resolved_patient_id, current_user)

    payload = await file.read()
    validate_imaging_upload(file.filename, file.content_type, payload)

    analysis = analyze_imaging(payload, filename=file.filename or "uploaded-image")
    severity = "high" if analysis.anomaly_score >= 0.72 else "medium" if analysis.anomaly_score >= 0.45 else "low"
    storage_uri = get_storage_service().store_imaging_upload(
        resolved_patient_id,
        file.filename or "uploaded-image",
        payload,
        content_type=file.content_type,
    )
    study = create_imaging_study(
        db,
        organization_id=organization_id,
        patient_id=resolved_patient_id,
        filename=file.filename or "uploaded-image",
        content_type=file.content_type or "application/octet-stream",
        storage_uri=storage_uri,
        uploaded_by=current_user.username,
        analysis_payload=analysis.model_dump(mode="json"),
    )

    analysis.study_reference = study.study_id
    analysis.stored_uri = storage_uri
    record_imaging_analysis(severity)

    notify_imaging_triage(
        db,
        username=current_user.username,
        organization_id=organization_id,
        patient_id=resolved_patient_id,
        study_id=study.study_id,
        analysis=analysis,
    )

    request.state.audit_detail = {
        "event": "imaging_analyzed",
        "study_id": study.study_id,
        "patient_id": resolved_patient_id,
        "severity": severity,
    }
    return analysis


@secured_router.get("/imaging/studies/{study_id}/content", tags=["imaging"])
def download_imaging_study(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> Response:
    study = get_imaging_study_record(db, _require_organization_id(current_user), study_id)
    if study is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Imaging study {study_id} was not found.")

    stored = get_storage_service().fetch_object(study.storage_uri)
    headers = {"Content-Disposition": f'attachment; filename="{study.filename}"'}
    return Response(content=stored.content, media_type=study.content_type or stored.content_type, headers=headers)


@secured_router.patch("/imaging/studies/{study_id}/review", response_model=ImagingStudyRecord, tags=["imaging"])
def update_imaging_study_review_endpoint(
    study_id: str,
    payload: ImagingStudyReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = REPORTING_ACCESS,
) -> ImagingStudyRecord:
    study = update_imaging_study_review(
        db,
        organization_id=_require_organization_id(current_user),
        study_id=study_id,
        actor_username=current_user.username,
        payload=payload,
    )
    if study is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Imaging study {study_id} was not found.")
    request.state.audit_detail = {"event": "imaging_review_updated", "study_id": study_id, "review_status": study.review_status}
    return study


@secured_router.get("/alerts", response_model=list[Alert], tags=["operations"])
def alerts(
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> list[Alert]:
    return list_alerts(db, _require_organization_id(current_user))


@secured_router.post("/alerts/{alert_id}/acknowledge", response_model=Alert, tags=["operations"])
def acknowledge_alert_endpoint(
    alert_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> Alert:
    alert = acknowledge_alert(db, _require_organization_id(current_user), alert_id, current_user.username)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert {alert_id} was not found.")
    request.state.audit_detail = {"event": "alert_acknowledged", "alert_id": alert_id}
    return alert


@secured_router.get("/analytics/overview", response_model=AnalyticsOverview, tags=["operations"])
def analytics_overview(
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> AnalyticsOverview:
    return get_analytics_overview(db, current_user, get_settings())


@secured_router.get("/operations/population-board", response_model=PopulationOperationsBoard, tags=["operations"])
def population_operations_board(
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> PopulationOperationsBoard:
    return build_population_operations_board(db, current_user)


@secured_router.get("/notifications", response_model=list[Notification], tags=["operations"])
def notifications(
    limit: int = Query(default=20, ge=1, le=100),
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> list[Notification]:
    return list_notifications(
        db,
        _require_organization_id(current_user),
        recipient_username=current_user.username,
        limit=limit,
        unread_only=unread_only,
    )


@secured_router.post("/notifications/{notification_id}/read", response_model=Notification, tags=["operations"])
def mark_notification_as_read(
    notification_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = CLINICAL_ACCESS,
) -> Notification:
    notification = mark_notification_read(db, _require_organization_id(current_user), notification_id, current_user.username)
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification {notification_id} was not found.")
    request.state.audit_detail = {"event": "notification_read", "notification_id": notification_id}
    return notification


@public_router.get("/events/operations", tags=["operations"])
async def operations_event_stream(
    request: Request,
    stream_token: str = Query(..., min_length=20),
    once: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    current_user = resolve_stream_user(db, stream_token)
    settings = get_settings()

    async def event_generator():
        previous_payload = ""
        while True:
            if await request.is_disconnected():
                break

            with SessionLocal() as stream_db:
                snapshot = build_operations_live_snapshot(
                    stream_db,
                    current_user=current_user,
                    settings=settings,
                )

            payload = snapshot.model_dump_json()
            if payload != previous_payload:
                yield f"event: operations\ndata: {payload}\n\n"
                previous_payload = payload
                if once:
                    break
            else:
                heartbeat = json.dumps({"generated_at": snapshot.generated_at.isoformat()})
                yield f"event: heartbeat\ndata: {heartbeat}\n\n"
                if once:
                    break

            await asyncio.sleep(settings.realtime_stream_interval_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@secured_router.post("/reports/patient/{patient_id}", response_model=ReportJob, tags=["reports"])
def create_patient_report(
    request: Request,
    patient_id: int,
    background_tasks: BackgroundTasks,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: UserProfile = REPORTING_ACCESS,
) -> ReportJob:
    settings = get_settings()
    enforce_rate_limit(
        f"reports:create:{current_user.username}",
        limit=10,
        window_seconds=settings.rate_limit_window_seconds,
        detail="Too many report requests. Please wait before creating another report.",
    )
    organization_id = _require_organization_id(current_user)
    get_patient_or_404(db, patient_id, current_user)
    job = enqueue_report_job(
        db,
        patient_id,
        organization_id=organization_id,
        requested_by=current_user.username,
        idempotency_key=idempotency_key,
    )
    task_id = dispatch_report_job(job.job_id, background_tasks)
    request.state.audit_detail = {"event": "report_enqueued", "job_id": job.job_id, "task_id": task_id}
    db.expire_all()
    refreshed = fetch_report_job(db, organization_id, job.job_id)
    return refreshed or job


@public_router.post("/internal/jobs/dispatch", tags=["internal"])
def dispatch_report_jobs(request: Request) -> dict[str, int | str]:
    _authorize_internal_request(request)
    return run_report_dispatch_cycle()


@public_router.post("/internal/maintenance/retention", tags=["internal"])
def retention_maintenance(request: Request) -> dict[str, int]:
    _authorize_internal_request(request)
    settings = get_settings()
    with SessionLocal() as db:
        notifications_removed = prune_notifications(db, settings.notification_retention_days)
        reports_removed = prune_report_jobs(db, settings.report_retention_days)
        audit_removed = prune_audit_logs(db, settings.audit_log_retention_days)
    return {
        "notifications_removed": notifications_removed,
        "reports_removed": reports_removed,
        "audit_removed": audit_removed,
    }


@secured_router.get("/reports/jobs", response_model=list[ReportJob], tags=["reports"])
def report_jobs(
    limit: int = Query(default=25, ge=1, le=100),
    current_user: UserProfile = REPORTING_ACCESS,
    db: Session = Depends(get_db),
) -> list[ReportJob]:
    return list_recent_report_jobs(db, _require_organization_id(current_user), limit=limit)


@secured_router.get("/reports/jobs/{job_id}", response_model=ReportJob, tags=["reports"])
def report_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = REPORTING_ACCESS,
) -> ReportJob:
    job = fetch_report_job(db, _require_organization_id(current_user), job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report job {job_id} was not found.")
    return job


@secured_router.get("/reports/jobs/{job_id}/artifact", tags=["reports"])
def download_report_artifact(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: UserProfile = REPORTING_ACCESS,
) -> Response:
    job = fetch_report_job(db, _require_organization_id(current_user), job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report job {job_id} was not found.")
    if job.artifact_uri:
        stored = get_storage_service().fetch_object(job.artifact_uri)
        headers = {"Content-Disposition": f'attachment; filename="{job_id}.json"'}
        return Response(content=stored.content, media_type="application/json", headers=headers)
    if job.artifact:
        headers = {"Content-Disposition": f'attachment; filename="{job_id}.json"'}
        payload = job.artifact.model_dump_json(indent=2)
        return Response(content=payload, media_type="application/json", headers=headers)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Report artifact for job {job_id} is not available.")


@secured_router.get("/models/registry", response_model=list[ModelRegistryEntry], tags=["models"])
def model_registry(_: UserProfile = MODEL_ACCESS) -> list[ModelRegistryEntry]:
    return get_model_registry()


@secured_router.get("/admin/audit-logs", response_model=list[AuditLogEntry], tags=["admin"])
def audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserProfile = ADMIN_ACCESS,
) -> list[AuditLogEntry]:
    return list_audit_logs(db, current_user, limit=limit)


@secured_router.get("/admin/users", response_model=list[UserDirectoryEntry], tags=["admin"])
def admin_users(
    limit: int = Query(default=100, ge=1, le=300),
    db: Session = Depends(get_db),
    current_user: UserProfile = ADMIN_ACCESS,
) -> list[UserDirectoryEntry]:
    return list_users(db, current_user, limit=limit)


@secured_router.patch("/admin/users/{username}/status", response_model=UserDirectoryEntry, tags=["admin"])
def admin_update_user_status(
    username: str,
    payload: UserStatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = ADMIN_ACCESS,
) -> UserDirectoryEntry:
    try:
        user = update_user_active_state(db, current_user, username, payload.is_active)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.state.audit_detail = {"event": "user_status_updated", "username": username, "is_active": payload.is_active}
    return user


@secured_router.patch("/admin/users/{username}/role", response_model=UserDirectoryEntry, tags=["admin"])
def admin_update_user_role(
    username: str,
    payload: UserRoleUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserProfile = ADMIN_ACCESS,
) -> UserDirectoryEntry:
    try:
        user = update_user_role(db, current_user, username, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.state.audit_detail = {"event": "user_role_updated", "username": username, "role": payload.role}
    return user


@secured_router.post("/admin/invites", response_model=InviteCodeRecord, tags=["admin"])
def admin_create_invite(
    request: Request,
    payload: InviteCodeCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserProfile = ADMIN_ACCESS,
) -> InviteCodeRecord:
    try:
        invite = create_invite_code(db, current_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    request.state.audit_detail = {"event": "invite_created", "invite_id": invite.invite_id, "role": invite.role}
    return invite


@secured_router.get("/admin/invites", response_model=list[InviteCodeRecord], tags=["admin"])
def admin_invites(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserProfile = ADMIN_ACCESS,
) -> list[InviteCodeRecord]:
    return list_invite_codes(db, current_user, limit=limit)
