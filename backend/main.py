from __future__ import annotations

import logging
import json
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.core.observability import ACTIVE_REQUESTS, record_http_request, setup_observability
from backend.app.db.migrations import run_migrations
from backend.app.db.enterprise_repository import create_audit_log
from backend.app.db.repository import init_db, prune_audit_logs, prune_notifications, prune_report_jobs, seed_database
from backend.app.db.session import SessionLocal
from backend.app.routes import public_router, secured_router
from backend.app.services.storage import get_storage_service

_bootstrapped = False


def bootstrap_application() -> None:
    global _bootstrapped
    if _bootstrapped:
        return

    settings = get_settings()
    settings.validate_runtime_secrets()

    _db_url = settings.resolved_database_url
    _is_in_memory = _db_url in {"sqlite://", "sqlite:///:memory:"}

    if _is_in_memory:
        # Alembic uses NullPool which creates a separate in-memory connection —
        # tables would disappear. Use init_db() so the shared StaticPool engine is used.
        init_db()
    elif settings.should_auto_migrate:
        run_migrations()
    elif settings.is_local_like:
        init_db()

    with SessionLocal() as db:
        seed_database(db, settings)
        prune_notifications(db, settings.notification_retention_days)
        prune_report_jobs(db, settings.report_retention_days)
        prune_audit_logs(db, settings.audit_log_retention_days)

    get_storage_service().ensure_ready()
    _bootstrapped = True


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("healthsphere.api")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        bootstrap_application()
        yield

    app = FastAPI(
        title=settings.app_name,
        version="1.1.0",
        description="Clinical intelligence APIs for predictive risk, imaging triage, care coordination, and platform operations.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.allowed_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600,  # cache CORS preflight for 10 minutes to cut OPTIONS round-trips
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site=settings.cookie_same_site,
        https_only=settings.secure_cookies,
        max_age=settings.access_token_expire_minutes * 60,
        session_cookie="healthsphere_session",
    )

    setup_observability(app, settings)

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        request.state.actor_username = getattr(request.state, "actor_username", "anonymous")
        request.state.actor_role = getattr(request.state, "actor_role", "service")

        start = time.perf_counter()
        ACTIVE_REQUESTS.inc()
        response = None

        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            if settings.security_headers_enabled:
                response.headers["x-content-type-options"] = "nosniff"
                response.headers["x-frame-options"] = "DENY"
                response.headers["x-xss-protection"] = "1; mode=block"
                response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
                response.headers["permissions-policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
                response.headers["content-security-policy"] = (
                    "default-src 'none'; "
                    "connect-src 'self'; "
                    "frame-ancestors 'none'"
                )
                if settings.environment != "local":
                    response.headers["strict-transport-security"] = "max-age=63072000; includeSubDomains; preload"
            return response
        finally:
            duration = time.perf_counter() - start
            ACTIVE_REQUESTS.dec()

            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            status_code = response.status_code if response is not None else 500

            record_http_request(request.method, route_path, status_code, duration)
            logger.info(
                "request-complete",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "actor": getattr(request.state, "actor_username", "anonymous"),
                    "role": getattr(request.state, "actor_role", "service"),
                },
            )

            if route_path not in {"/health/live", "/health/ready", "/docs", "/openapi.json", "/redoc", "/metrics"}:
                path_params = getattr(request, "path_params", {}) or {}
                entity_id = next(
                    (str(value) for key, value in path_params.items() if key.endswith("_id") or key in {"job_id", "notification_id"}),
                    None,
                )
                entity_type = request.url.path.strip("/").split("/")[0] if request.url.path.strip("/") else None
                detail = getattr(request.state, "audit_detail", None)
                try:
                    with SessionLocal() as db:
                        create_audit_log(
                            db,
                            organization_id=getattr(request.state, "organization_id", None),
                            request_id=request_id,
                            actor_username=getattr(request.state, "actor_username", "anonymous"),
                            actor_role=getattr(request.state, "actor_role", "service"),
                            method=request.method,
                            path=request.url.path,
                            status_code=status_code,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            detail=detail,
                        )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception(
                        "audit-log-write-failed",
                        extra={
                            "request_id": request_id,
                            "path": request.url.path,
                            "status_code": status_code,
                            "actor": getattr(request.state, "actor_username", "anonymous"),
                            "role": getattr(request.state, "actor_role", "service"),
                            "detail": json.dumps({"error": str(exc)}),
                        },
                    )

    # Reject oversized JSON/form bodies before they reach route handlers.
    # File uploads are validated separately in upload_guard.py.
    _max_body_bytes = 1 * 1024 * 1024  # 1 MB for non-upload requests

    @app.middleware("http")
    async def limit_request_body(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > _max_body_bytes:
            return JSONResponse(status_code=413, content={"detail": "Request body too large."})
        return await call_next(request)

    app.include_router(public_router, prefix=settings.api_prefix)
    app.include_router(secured_router, prefix=settings.api_prefix)
    if settings.legacy_routes_enabled:
        # Legacy (un-prefixed) routes are deprecated — clients should migrate to /api/v1/...
        @app.middleware("http")
        async def deprecation_header(request: Request, call_next):
            response = await call_next(request)
            if not request.url.path.startswith(settings.api_prefix):
                response.headers["Deprecation"] = "true"
                response.headers["Link"] = (
                    f'<{settings.frontend_app_url}{settings.api_prefix}{request.url.path}>; rel="successor-version"'
                )
            return response

        app.include_router(public_router)
        app.include_router(secured_router)

    return app


app = create_app()
