from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool

from backend.app.core.config import get_settings


settings = get_settings()
_db_url = settings.resolved_database_url
_is_sqlite = _db_url.startswith("sqlite")
_is_in_memory = _db_url in {"sqlite://", "sqlite:///:memory:"}

connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine_kwargs: dict = {
    "future": True,
    "connect_args": connect_args,
    "pool_pre_ping": True,
}

if _is_in_memory:
    engine_kwargs["poolclass"] = StaticPool
elif _is_sqlite:
    # File-based SQLite: use NullPool so each connection is independent
    engine_kwargs["poolclass"] = NullPool
else:
    # Production databases get an explicit connection pool
    engine_kwargs["pool_size"] = settings.db_pool_size
    engine_kwargs["max_overflow"] = settings.db_max_overflow
    engine_kwargs["pool_timeout"] = settings.db_pool_timeout
    engine_kwargs["pool_recycle"] = settings.db_pool_recycle

engine = create_engine(_db_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
