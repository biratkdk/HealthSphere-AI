from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from backend.app.core.config import Settings
from backend.app.db.session import engine


REQUEST_COUNT = Counter(
    "healthsphere_http_requests_total",
    "Total HTTP requests handled by the API.",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "healthsphere_http_request_duration_seconds",
    "Request latency for API calls.",
    ["method", "path"],
)
ACTIVE_REQUESTS = Gauge(
    "healthsphere_http_requests_inflight",
    "In-flight HTTP requests.",
)
REPORT_JOB_EVENTS = Counter(
    "healthsphere_report_jobs_total",
    "Report job lifecycle events.",
    ["status", "mode"],
)
IMAGING_ANALYSIS_EVENTS = Counter(
    "healthsphere_imaging_analyses_total",
    "Imaging analyses executed by severity bucket.",
    ["severity"],
)
AUTH_LOGIN_EVENTS = Counter(
    "healthsphere_auth_logins_total",
    "Interactive sign-in events.",
    ["provider"],
)
NOTIFICATION_EVENTS = Counter(
    "healthsphere_notifications_total",
    "Notifications created by category.",
    ["category"],
)

_sqlalchemy_instrumented = False


def setup_observability(app, settings: Settings) -> None:
    if not settings.otlp_endpoint:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    global _sqlalchemy_instrumented

    resource = Resource.create({"service.name": settings.service_name})
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otlp_endpoint)))
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)

    if not _sqlalchemy_instrumented:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        _sqlalchemy_instrumented = True


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    REQUEST_COUNT.labels(method=method, path=path, status=str(status_code)).inc()
    REQUEST_DURATION.labels(method=method, path=path).observe(duration_seconds)


def record_report_job(status: str, mode: str) -> None:
    REPORT_JOB_EVENTS.labels(status=status, mode=mode).inc()


def record_imaging_analysis(severity: str) -> None:
    IMAGING_ANALYSIS_EVENTS.labels(severity=severity).inc()


def record_login(provider: str) -> None:
    AUTH_LOGIN_EVENTS.labels(provider=provider).inc()


def record_notification(category: str) -> None:
    NOTIFICATION_EVENTS.labels(category=category).inc()


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
