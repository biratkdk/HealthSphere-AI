from __future__ import annotations

import pytest
from fastapi import HTTPException
from redis.exceptions import ConnectionError

from backend.app.core import rate_limit
from backend.app.core.config import Settings


class FakeRedis:
    def __init__(self, result: int = -1, exc: Exception | None = None) -> None:
        self.result = result
        self.exc = exc
        self.calls = 0

    def eval(self, *_args, **_kwargs) -> int:
        self.calls += 1
        if self.exc is not None:
            raise self.exc
        return self.result


def _reset_rate_limit_state() -> None:
    rate_limit._WINDOWS.clear()
    rate_limit._REDIS_CLIENT = None
    rate_limit._REDIS_FAILURE_LOGGED = False


def test_redis_rate_limit_is_used_when_available(monkeypatch) -> None:
    _reset_rate_limit_state()
    fake = FakeRedis(result=-1)

    monkeypatch.setattr(
        rate_limit,
        "get_settings",
        lambda: Settings(environment="production", rate_limit_backend="redis", rate_limit_redis_url="redis://cache:6379/2"),
    )
    monkeypatch.setattr(rate_limit, "_REDIS_CLIENT", fake)

    rate_limit.enforce_rate_limit("auth:login:127.0.0.1", limit=4, window_seconds=60, detail="blocked")
    assert fake.calls == 1


def test_redis_rate_limit_blocks_when_window_is_full(monkeypatch) -> None:
    _reset_rate_limit_state()
    fake = FakeRedis(result=4)

    monkeypatch.setattr(
        rate_limit,
        "get_settings",
        lambda: Settings(environment="production", rate_limit_backend="redis", rate_limit_redis_url="redis://cache:6379/2"),
    )
    monkeypatch.setattr(rate_limit, "_REDIS_CLIENT", fake)

    with pytest.raises(HTTPException) as exc:
        rate_limit.enforce_rate_limit("auth:signup:127.0.0.1", limit=4, window_seconds=60, detail="blocked")

    assert exc.value.status_code == 429


def test_rate_limit_falls_back_to_memory_when_redis_is_unavailable(monkeypatch) -> None:
    _reset_rate_limit_state()
    fake = FakeRedis(exc=ConnectionError("unavailable"))

    monkeypatch.setattr(
        rate_limit,
        "get_settings",
        lambda: Settings(environment="production", rate_limit_backend="redis", rate_limit_redis_url="redis://cache:6379/2"),
    )
    monkeypatch.setattr(rate_limit, "_REDIS_CLIENT", fake)

    rate_limit.enforce_rate_limit("upload:clinician:127.0.0.1", limit=1, window_seconds=60, detail="blocked")
    with pytest.raises(HTTPException) as exc:
        rate_limit.enforce_rate_limit("upload:clinician:127.0.0.1", limit=1, window_seconds=60, detail="blocked")

    assert exc.value.status_code == 429
