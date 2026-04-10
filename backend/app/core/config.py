import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PLACEHOLDER_SECRETS = {
    "change-me-service-key",
    "replace-this-in-real-environments",
    "replace-this-session-secret",
    "AdminPass123!",
    "ClinicianPass123!",
    "AnalystPass123!",
}


class Settings(BaseSettings):
    app_name: str = "HealthSphere AI Backend"
    environment: str = "local"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite://"
    database_url_unpooled: str = ""
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_pool_timeout: int = Field(default=30, ge=5, le=120)
    db_pool_recycle: int = Field(default=1800, ge=60, le=7200)
    service_api_key: str = "change-me-service-key"
    enforce_auth: bool = True
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    allowed_origin_regex: str = ""
    frontend_app_url: str = "http://localhost:3000"
    log_level: str = "INFO"
    default_patient_id: int = 1001
    report_retention_days: int = Field(default=30, ge=1, le=365)
    audit_log_retention_days: int = Field(default=365, ge=7, le=3650)
    jwt_secret_key: str = "replace-this-in-real-environments"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    refresh_token_expire_days: int = Field(default=14, ge=1, le=90)
    session_secret_key: str = "replace-this-session-secret"
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_password: str = "AdminPass123!"
    bootstrap_clinician_username: str = "clinician"
    bootstrap_clinician_password: str = "ClinicianPass123!"
    bootstrap_analyst_username: str = "analyst"
    bootstrap_analyst_password: str = "AnalystPass123!"
    seed_demo_data: bool = False
    auto_migrate: bool = False
    task_execution_mode: Literal["dispatcher", "inline", "celery"] = "dispatcher"
    dispatcher_batch_size: int = Field(default=4, ge=1, le=50)
    job_lease_seconds: int = Field(default=90, ge=15, le=1800)
    job_max_attempts: int = Field(default=3, ge=1, le=10)
    job_retry_backoff_seconds: int = Field(default=20, ge=5, le=3600)
    cron_secret: str = ""
    cron_secret_min_length: int = 32
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    celery_task_always_eager: bool = False
    storage_backend: Literal["auto", "local", "vercel_blob"] = "auto"
    storage_root: str = "./storage"
    blob_access: Literal["private", "public"] = "private"
    blob_prefix: str = "healthsphere"
    blob_add_random_suffix: bool = True
    google_oauth_enabled: bool = False
    google_client_id: str = ""
    google_client_secret: str = ""
    google_server_metadata_url: str = "https://accounts.google.com/.well-known/openid-configuration"
    google_provider_label: str = "Google"
    google_provider_description: str = "Use Google to create or access your workspace."
    facebook_oauth_enabled: bool = False
    facebook_client_id: str = ""
    facebook_client_secret: str = ""
    facebook_authorize_url: str = "https://www.facebook.com/dialog/oauth"
    facebook_access_token_url: str = "https://graph.facebook.com/oauth/access_token"
    facebook_userinfo_url: str = "https://graph.facebook.com/me?fields=id,name,email"
    facebook_provider_label: str = "Facebook"
    facebook_provider_description: str = "Use Facebook to create or access your workspace."
    oidc_enabled: bool = False
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_server_metadata_url: str = ""
    oidc_provider_label: str = "Google Workspace"
    oidc_provider_description: str = "Use your organization's identity provider for a managed sign-in experience."
    oidc_provider_brand: str = "google"
    auth_default_role: str = ""
    auth_role_claim: str = ""
    auth_admin_emails: str = ""
    oidc_default_role: str = "clinician"
    oidc_role_claim: str = "role"
    oidc_admin_emails: str = ""
    oidc_override_role_on_login: bool = False
    metrics_enabled: bool = True
    otlp_endpoint: str = ""
    service_name: str = "healthsphere-api"
    notification_retention_days: int = Field(default=30, ge=1, le=365)
    stream_token_expire_minutes: int = Field(default=15, ge=1, le=240)
    realtime_stream_interval_seconds: int = Field(default=4, ge=1, le=30)
    security_headers_enabled: bool = True
    legacy_routes_enabled: bool = True
    max_upload_size_mb: int = Field(default=8, ge=1, le=32)
    allowed_imaging_content_types: str = "image/png,image/jpeg,application/dicom"
    rate_limit_window_seconds: int = Field(default=60, ge=10, le=3600)
    rate_limit_login_attempts: int = Field(default=8, ge=1, le=100)
    rate_limit_signup_attempts: int = Field(default=4, ge=1, le=100)
    rate_limit_upload_attempts: int = Field(default=15, ge=1, le=100)
    rate_limit_backend: Literal["auto", "memory", "redis"] = "auto"
    rate_limit_redis_url: str = ""
    rate_limit_key_prefix: str = "healthsphere:ratelimit"
    access_cookie_name: str = "healthsphere_access"
    refresh_cookie_name: str = "healthsphere_refresh"
    secure_cookies_override: bool | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_quoted_environment_values(cls, values: object) -> object:
        if not isinstance(values, dict):
            return values

        normalized: dict[str, object] = {}
        for key, value in values.items():
            if isinstance(value, str):
                stripped = value.strip()
                if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
                    stripped = stripped[1:-1]
                normalized[key] = stripped
            else:
                normalized[key] = value
        return normalized

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def oidc_admin_email_list(self) -> list[str]:
        return self.auth_admin_email_list

    @property
    def auth_admin_email_list(self) -> list[str]:
        raw_value = self.auth_admin_emails or self.oidc_admin_emails
        return [email.strip().lower() for email in raw_value.split(",") if email.strip()]

    @property
    def resolved_auth_default_role(self) -> str:
        return (self.auth_default_role or self.oidc_default_role or "clinician").strip().lower()

    @property
    def resolved_auth_role_claim(self) -> str:
        return (self.auth_role_claim or self.oidc_role_claim or "role").strip()

    @property
    def resolved_google_oauth_enabled(self) -> bool:
        return self.google_oauth_enabled or self.oidc_enabled

    @property
    def resolved_google_client_id(self) -> str:
        return (self.google_client_id or self.oidc_client_id).strip()

    @property
    def resolved_google_client_secret(self) -> str:
        return (self.google_client_secret or self.oidc_client_secret).strip()

    @property
    def resolved_google_server_metadata_url(self) -> str:
        return (self.google_server_metadata_url or self.oidc_server_metadata_url).strip()

    @property
    def resolved_google_provider_label(self) -> str:
        return (self.google_provider_label or self.oidc_provider_label or "Google").strip()

    @property
    def resolved_google_provider_description(self) -> str:
        return (
            self.google_provider_description
            or self.oidc_provider_description
            or "Use Google to create or access your workspace."
        ).strip()

    @property
    def is_vercel(self) -> bool:
        return self.environment.lower() == "vercel" or os.getenv("VERCEL") == "1"

    @property
    def is_local_like(self) -> bool:
        return self.environment.lower() in {"local", "development", "dev", "test"}

    @property
    def should_seed_demo_data(self) -> bool:
        return self.seed_demo_data or self.is_local_like

    @property
    def should_auto_migrate(self) -> bool:
        return self.auto_migrate

    @property
    def secure_cookies(self) -> bool:
        if self.secure_cookies_override is not None:
            return self.secure_cookies_override
        return not self.is_local_like

    @property
    def cookie_same_site(self) -> Literal["lax", "none"]:
        return "lax" if self.is_local_like else "none"

    @property
    def resolved_database_url(self) -> str:
        return self._normalize_database_url(self.database_url)

    @property
    def resolved_migration_database_url(self) -> str:
        return self._normalize_database_url(self.database_url_unpooled or self.database_url)

    @property
    def resolved_storage_root(self) -> str:
        if not self.is_vercel:
            return self.storage_root

        root = Path(self.storage_root)
        if root.is_absolute():
            return str(root)

        normalized = str(root).replace("\\", "/").lstrip("./") or "storage"
        return str(Path("/tmp") / normalized)

    @property
    def resolved_storage_backend(self) -> Literal["local", "vercel_blob"]:
        if self.storage_backend == "auto":
            return "vercel_blob" if os.getenv("BLOB_READ_WRITE_TOKEN") else "local"
        return "vercel_blob" if self.storage_backend == "vercel_blob" else "local"

    @property
    def resolved_rate_limit_redis_url(self) -> str:
        return (self.rate_limit_redis_url or self.celery_broker_url).strip()

    @property
    def resolved_rate_limit_backend(self) -> Literal["memory", "redis"]:
        if self.rate_limit_backend == "memory":
            return "memory"
        if self.rate_limit_backend == "redis":
            return "redis"
        if self.is_local_like:
            return "memory"
        return "redis" if self.resolved_rate_limit_redis_url.startswith(("redis://", "rediss://")) else "memory"

    @property
    def imaging_content_types(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_imaging_content_types.split(",") if item.strip()}

    def validate_runtime_secrets(self) -> None:
        if self.is_local_like:
            return

        sensitive_values = {
            self.service_api_key,
            self.jwt_secret_key,
            self.session_secret_key,
        }
        if sensitive_values & PLACEHOLDER_SECRETS:
            raise RuntimeError("Refusing to start with placeholder runtime secrets in a shared environment.")

        bootstrap_passwords = {
            self.bootstrap_admin_password,
            self.bootstrap_clinician_password,
            self.bootstrap_analyst_password,
        }
        if bootstrap_passwords & PLACEHOLDER_SECRETS:
            raise RuntimeError("Refusing to start with default bootstrap passwords in a shared environment.")

        cron_secret_valid = bool(self.cron_secret and len(self.cron_secret) >= self.cron_secret_min_length)
        service_key_valid = self.service_api_key not in PLACEHOLDER_SECRETS and len(self.service_api_key) >= 24
        if not cron_secret_valid and not service_key_valid:
            raise RuntimeError(
                "Set CRON_SECRET to the required length or provide a strong non-placeholder SERVICE_API_KEY in non-local environments."
            )

    def _normalize_database_url(self, value: str) -> str:
        url = value.strip()
        if self.is_vercel and url.startswith("sqlite:///./"):
            filename = url.removeprefix("sqlite:///./")
            return f"sqlite:////tmp/{filename}"
        if url.startswith("postgres://"):
            return f"postgresql+psycopg://{url.removeprefix('postgres://')}"
        if url.startswith("postgresql://"):
            return f"postgresql+psycopg://{url.removeprefix('postgresql://')}"
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
