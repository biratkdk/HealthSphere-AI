from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

import jwt


PBKDF2_ITERATIONS = 390000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${iterations}${salt}${hash}".format(
        iterations=PBKDF2_ITERATIONS,
        salt=base64.b64encode(salt).decode("ascii"),
        hash=base64.b64encode(derived).decode("ascii"),
    )


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, iterations, salt_b64, hash_b64 = encoded_password.split("$", maxsplit=3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64.encode("ascii"))
    expected = base64.b64decode(hash_b64.encode("ascii"))
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(derived, expected)


def create_signed_token(
    *,
    subject: str,
    role: str,
    secret_key: str,
    algorithm: str,
    expires_seconds: int,
    token_use: str = "access",
    extra_claims: dict | None = None,
) -> tuple[str, int]:
    expires_at = datetime.now(UTC) + timedelta(seconds=expires_seconds)
    payload = {
        "sub": subject,
        "role": role,
        "token_use": token_use,
        "exp": expires_at,
        "iat": datetime.now(UTC),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret_key, algorithm=algorithm), expires_seconds


def create_access_token(
    *,
    subject: str,
    role: str,
    secret_key: str,
    algorithm: str,
    expires_minutes: int,
    extra_claims: dict | None = None,
) -> tuple[str, int]:
    return create_signed_token(
        subject=subject,
        role=role,
        secret_key=secret_key,
        algorithm=algorithm,
        expires_seconds=expires_minutes * 60,
        token_use="access",
        extra_claims=extra_claims,
    )


def create_stream_token(
    *,
    subject: str,
    role: str,
    secret_key: str,
    algorithm: str,
    expires_minutes: int,
    extra_claims: dict | None = None,
) -> tuple[str, int]:
    return create_signed_token(
        subject=subject,
        role=role,
        secret_key=secret_key,
        algorithm=algorithm,
        expires_seconds=expires_minutes * 60,
        token_use="stream",
        extra_claims=extra_claims,
    )


def decode_access_token(token: str, *, secret_key: str, algorithm: str) -> dict[str, str]:
    return jwt.decode(token, secret_key, algorithms=[algorithm])


def create_refresh_token_value() -> str:
    return token_urlsafe(48)


def hash_session_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
