from __future__ import annotations

from typing import Callable

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.crypto import create_access_token, create_stream_token, decode_access_token, verify_password
from backend.app.db.enterprise_repository import (
    get_user_by_email,
    get_user_by_username,
    update_last_login,
    user_to_profile,
)
from backend.app.db.session import get_db
from backend.app.models import RoleName, StreamTokenResponse, TokenResponse, UserProfile


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def authenticate_user(db: Session, username: str, password: str) -> UserProfile | None:
    user = get_user_by_username(db, username)
    if user is None and "@" in username:
        user = get_user_by_email(db, username.lower())
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return update_last_login(db, user)


def issue_access_token(user: UserProfile, session_id: str | None = None) -> TokenResponse:
    settings = get_settings()
    token, expires_in = create_access_token(
        subject=user.username,
        role=user.role,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_expire_minutes,
        extra_claims={"sid": session_id} if session_id else None,
    )
    return TokenResponse(access_token=token, expires_in=expires_in, user=user, session_id=session_id)


def issue_stream_token(user: UserProfile, session_id: str | None = None) -> StreamTokenResponse:
    settings = get_settings()
    token, expires_in = create_stream_token(
        subject=user.username,
        role=user.role,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.stream_token_expire_minutes,
        extra_claims={"sid": session_id} if session_id else None,
    )
    return StreamTokenResponse(stream_token=token, expires_in=expires_in)


def _set_actor_context(request: Request, user: UserProfile, session_id: str | None = None) -> UserProfile:
    request.state.actor_username = user.username
    request.state.actor_role = user.role
    request.state.organization_id = user.organization_id
    request.state.session_id = session_id
    return user


def _decode_bearer_or_cookie_token(settings, token: str | None, cookie_token: str | None) -> tuple[dict, str]:
    candidate = token or cookie_token
    if not candidate:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication credentials were not provided.")
    try:
        payload = decode_access_token(candidate, secret_key=settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    except jwt.PyJWTError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.") from exc
    return payload, candidate


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> UserProfile:
    settings = get_settings()
    cookie_token = request.cookies.get(settings.access_cookie_name)

    if not settings.enforce_auth:
        user = get_user_by_username(db, settings.bootstrap_clinician_username)
        if user is not None:
            return _set_actor_context(request, user_to_profile(user))
        return _set_actor_context(
            request,
            UserProfile(
                username="local-dev",
                full_name="Local Developer",
                role="admin",
                is_active=True,
                auth_provider="local",
                organization_id=1,
                organization_name="Local Workspace",
            ),
        )

    if token or cookie_token:
        payload, _ = _decode_bearer_or_cookie_token(settings, token, cookie_token)
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token subject.")

        user = get_user_by_username(db, username)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not available.")

        return _set_actor_context(request, user_to_profile(user), session_id=payload.get("sid"))

    if x_api_key and x_api_key == settings.service_api_key:
        return _set_actor_context(
            request,
            UserProfile(
                username="service-gateway",
                full_name="Service Gateway",
                role="service",
                is_active=True,
                auth_provider="service",
            ),
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication credentials were not provided.")


def resolve_stream_user(db: Session, stream_token: str) -> UserProfile:
    settings = get_settings()
    try:
        payload = decode_access_token(stream_token, secret_key=settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid stream token.") from exc

    if payload.get("token_use") != "stream":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid stream token.")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid stream token subject.")

    user = get_user_by_username(db, username)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is not available.")
    return user_to_profile(user)


def get_current_session_id(request: Request) -> str | None:
    return getattr(request.state, "session_id", None)


def require_roles(*roles: RoleName | str) -> Callable[[UserProfile], UserProfile]:
    allowed_roles = set(roles)

    def dependency(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions.")
        return current_user

    return dependency
