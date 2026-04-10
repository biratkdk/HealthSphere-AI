from backend.app.core.config import Settings


def test_postgresql_urls_are_normalized_for_psycopg() -> None:
    settings = Settings(environment="vercel", database_url="postgresql://user:pass@db.example.com/app")
    assert settings.resolved_database_url == "postgresql+psycopg://user:pass@db.example.com/app"


def test_postgres_alias_and_unpooled_url_are_supported() -> None:
    settings = Settings(
        environment="vercel",
        database_url="postgres://user:pass@pool.example.com/app",
        database_url_unpooled="postgresql://user:pass@direct.example.com/app",
    )

    assert settings.resolved_database_url == "postgresql+psycopg://user:pass@pool.example.com/app"
    assert settings.resolved_migration_database_url == "postgresql+psycopg://user:pass@direct.example.com/app"


def test_auto_migrate_requires_explicit_opt_in_outside_local() -> None:
    settings = Settings(environment="production", auto_migrate=False)
    assert settings.should_auto_migrate is False


def test_rate_limit_defaults_to_memory_in_local_like_environments() -> None:
    settings = Settings(environment="test", rate_limit_backend="auto", rate_limit_redis_url="redis://cache:6379/2")
    assert settings.resolved_rate_limit_backend == "memory"


def test_rate_limit_uses_redis_in_shared_environments_when_configured() -> None:
    settings = Settings(environment="production", rate_limit_backend="auto", rate_limit_redis_url="redis://cache:6379/2")
    assert settings.resolved_rate_limit_backend == "redis"


def test_wrapped_quotes_are_removed_from_environment_values() -> None:
    settings = Settings(environment='"vercel"', task_execution_mode='"inline"', storage_backend='"auto"')
    assert settings.environment == "vercel"
    assert settings.task_execution_mode == "inline"
    assert settings.storage_backend == "auto"
