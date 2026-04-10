from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from backend.app.core.config import get_settings


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_alembic_config() -> Config:
    root = _project_root()
    settings = get_settings()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.resolved_migration_database_url)
    return config


def run_migrations() -> None:
    command.upgrade(get_alembic_config(), "head")
