from __future__ import annotations

import logging
from collections import defaultdict, deque
from threading import Lock
from time import time
from uuid import uuid4

from fastapi import HTTPException, status

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - optional runtime dependency
    Redis = None
    RedisError = Exception

from backend.app.core.config import get_settings


_log = logging.getLogger("healthsphere.rate_limit")

_WINDOWS: dict[str, deque[float]] = defaultdict(deque)
_LOCK = Lock()
_REDIS_CLIENT: Redis | None = None
_REDIS_FAILURE_LOGGED = False
_REDIS_RATE_LIMIT_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call("ZREMRANGEBYSCORE", key, 0, now_ms - window_ms)
local count = redis.call("ZCARD", key)
if count >= limit then
  return count
end

redis.call("ZADD", key, now_ms, member)
redis.call("PEXPIRE", key, window_ms)
return -1
"""


def _log_redis_failure(exc: Exception) -> None:
    global _REDIS_FAILURE_LOGGED
    if _REDIS_FAILURE_LOGGED:
        return
    _log.warning("rate-limit-redis-unavailable", extra={"error": str(exc)})
    _REDIS_FAILURE_LOGGED = True


def _get_redis_client() -> Redis | None:
    global _REDIS_CLIENT
    settings = get_settings()
    if settings.resolved_rate_limit_backend != "redis":
        return None
    if Redis is None:
        return None
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT

    redis_url = settings.resolved_rate_limit_redis_url
    if not redis_url:
        return None

    try:
        _REDIS_CLIENT = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            health_check_interval=30,
        )
    except Exception as exc:  # pragma: no cover - defensive
        _log_redis_failure(exc)
        return None
    return _REDIS_CLIENT


def _enforce_rate_limit_memory(bucket: str, *, limit: int, window_seconds: int, detail: str) -> None:
    now = time()
    with _LOCK:
        window = _WINDOWS[bucket]
        while window and now - window[0] > window_seconds:
            window.popleft()
        if len(window) >= limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)
        window.append(now)


def _enforce_rate_limit_redis(bucket: str, *, limit: int, window_seconds: int, detail: str) -> bool:
    settings = get_settings()
    client = _get_redis_client()
    if client is None:
        return False

    now_ms = int(time() * 1000)
    key = f"{settings.rate_limit_key_prefix}:{bucket}"
    member = f"{now_ms}-{uuid4().hex}"

    try:
        result = int(
            client.eval(
                _REDIS_RATE_LIMIT_SCRIPT,
                1,
                key,
                now_ms,
                window_seconds * 1000,
                limit,
                member,
            )
        )
    except RedisError as exc:
        _log_redis_failure(exc)
        return False

    if result >= 0:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)
    return True


def enforce_rate_limit(bucket: str, *, limit: int, window_seconds: int, detail: str) -> None:
    if _enforce_rate_limit_redis(bucket, limit=limit, window_seconds=window_seconds, detail=detail):
        return
    _enforce_rate_limit_memory(bucket, limit=limit, window_seconds=window_seconds, detail=detail)
