from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status

from backend.app.core.config import Settings, get_settings
from backend.app.models import AuthProviderCatalog, AuthProviderDescriptor, RoleName


ALLOWED_ROLES = {"admin", "clinician", "analyst"}
OAuthProviderId = Literal["google", "facebook"]
FEDERATED_PROVIDERS: tuple[OAuthProviderId, ...] = ("google", "facebook")


@dataclass(frozen=True, slots=True)
class FederatedProviderConfig:
    id: OAuthProviderId
    label: str
    description: str
    brand: str
    enabled: bool
    protocol: Literal["oidc", "oauth2"]
    client_id: str
    client_secret: str
    server_metadata_url: str | None = None
    authorize_url: str | None = None
    access_token_url: str | None = None
    userinfo_url: str | None = None
    scope: str = "openid profile email"


def _provider_definitions(settings: Settings | None = None) -> dict[OAuthProviderId, FederatedProviderConfig]:
    active_settings = settings or get_settings()
    google_client_id = active_settings.resolved_google_client_id
    google_client_secret = active_settings.resolved_google_client_secret
    google_metadata_url = active_settings.resolved_google_server_metadata_url

    providers: dict[OAuthProviderId, FederatedProviderConfig] = {
        "google": FederatedProviderConfig(
            id="google",
            label=active_settings.resolved_google_provider_label,
            description=active_settings.resolved_google_provider_description,
            brand="google",
            enabled=bool(
                active_settings.resolved_google_oauth_enabled
                and google_client_id
                and google_client_secret
                and google_metadata_url
            ),
            protocol="oidc",
            client_id=google_client_id,
            client_secret=google_client_secret,
            server_metadata_url=google_metadata_url,
        ),
        "facebook": FederatedProviderConfig(
            id="facebook",
            label=active_settings.facebook_provider_label or "Facebook",
            description=(
                active_settings.facebook_provider_description
                or "Use Facebook to create or access your workspace."
            ),
            brand="facebook",
            enabled=bool(
                active_settings.facebook_oauth_enabled
                and active_settings.facebook_client_id
                and active_settings.facebook_client_secret
            ),
            protocol="oauth2",
            client_id=active_settings.facebook_client_id.strip(),
            client_secret=active_settings.facebook_client_secret.strip(),
            authorize_url=active_settings.facebook_authorize_url.strip(),
            access_token_url=active_settings.facebook_access_token_url.strip(),
            userinfo_url=active_settings.facebook_userinfo_url.strip(),
            scope="email public_profile",
        ),
    }
    return providers


def _get_provider_config(provider: str, settings: Settings | None = None) -> FederatedProviderConfig:
    provider_id = provider.strip().lower()
    if provider_id not in FEDERATED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Provider {provider} is not available.")
    return _provider_definitions(settings)[provider_id]  # type: ignore[index]


def provider_enabled(provider: str, settings: Settings | None = None) -> bool:
    return _get_provider_config(provider, settings).enabled


def federated_auth_enabled(settings: Settings | None = None) -> bool:
    active_settings = settings or get_settings()
    return any(config.enabled for config in _provider_definitions(active_settings).values())


def oidc_enabled(settings: Settings | None = None) -> bool:
    return provider_enabled("google", settings)


@lru_cache(maxsize=1)
def _oauth_registry() -> OAuth:
    settings = get_settings()
    oauth = OAuth()

    for provider in FEDERATED_PROVIDERS:
        config = _get_provider_config(provider, settings)
        if not config.enabled:
            continue

        if config.protocol == "oidc":
            oauth.register(
                name=config.id,
                client_id=config.client_id,
                client_secret=config.client_secret,
                server_metadata_url=config.server_metadata_url,
                client_kwargs={"scope": config.scope},
            )
            continue

        oauth.register(
            name=config.id,
            client_id=config.client_id,
            client_secret=config.client_secret,
            authorize_url=config.authorize_url,
            access_token_url=config.access_token_url,
            client_kwargs={"scope": config.scope},
        )

    return oauth


def get_oauth_client(provider: str):
    config = _get_provider_config(provider)
    if not config.enabled:
        return None
    return _oauth_registry().create_client(config.id)


def get_oidc_client():
    return get_oauth_client("google")


def _provider_login_url(provider: OAuthProviderId, request: Request) -> str:
    if provider == "google":
        return str(request.url_for("oidc_login"))
    return str(request.url_for("oauth_provider_login", provider=provider))


def get_auth_provider_catalog(request: Request) -> AuthProviderCatalog:
    providers = [
        AuthProviderDescriptor(
            id="password",
            label="Email and password",
            available=True,
            description="Create a local account or continue with an existing workspace login.",
            brand="local",
        )
    ]

    for provider in FEDERATED_PROVIDERS:
        config = _get_provider_config(provider)
        providers.append(
            AuthProviderDescriptor(
                id=config.id,
                label=config.label,
                available=config.enabled,
                login_url=_provider_login_url(config.id, request) if config.enabled else None,
                description=config.description,
                brand=config.brand,
            )
        )

    return AuthProviderCatalog(providers=providers)


async def fetch_federated_userinfo(provider: str, request: Request, token: dict, client) -> dict:
    provider_id = _get_provider_config(provider).id

    if provider_id == "google":
        userinfo = token.get("userinfo")
        if not userinfo:
            try:
                userinfo = await client.userinfo(token=token)
            except Exception:
                userinfo = await client.parse_id_token(request, token)
        return dict(userinfo) if not isinstance(userinfo, dict) else userinfo

    response = await client.get(_get_provider_config(provider_id).userinfo_url, token=token)
    payload = response.json()
    return dict(payload) if not isinstance(payload, dict) else payload


def resolve_federated_identity(provider: str, userinfo: dict) -> tuple[str, str | None, str | None, str]:
    provider_id = _get_provider_config(provider).id

    if provider_id == "facebook":
        subject = str(userinfo.get("id") or "").strip()
        email = userinfo.get("email")
        if isinstance(email, str):
            email = email.strip().lower() or None
        preferred_username = email
        full_name = userinfo.get("name") or preferred_username or "Facebook User"
    else:
        subject = str(userinfo.get("sub") or "").strip()
        email = userinfo.get("email")
        if isinstance(email, str):
            email = email.strip().lower() or None
        preferred_username = userinfo.get("preferred_username") or userinfo.get("upn") or email
        full_name = userinfo.get("name") or preferred_username or email or "Federated User"

    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Federated user profile did not include a subject.")

    return subject, email, preferred_username, str(full_name).strip()


def resolve_oidc_identity(userinfo: dict) -> tuple[str, str | None, str | None, str]:
    return resolve_federated_identity("google", userinfo)


def resolve_federated_role(userinfo: dict, settings: Settings) -> RoleName:
    email = str(userinfo.get("email") or "").strip().lower()
    if email and email in settings.auth_admin_email_list:
        return "admin"

    raw_role = userinfo.get(settings.resolved_auth_role_claim)
    if isinstance(raw_role, list):
        for item in raw_role:
            if item in ALLOWED_ROLES:
                return item
    elif isinstance(raw_role, str) and raw_role in ALLOWED_ROLES:
        return raw_role

    default_role = settings.resolved_auth_default_role if settings.resolved_auth_default_role in ALLOWED_ROLES else "clinician"
    return default_role  # type: ignore[return-value]


def resolve_oidc_role(userinfo: dict, settings: Settings) -> RoleName:
    return resolve_federated_role(userinfo, settings)
