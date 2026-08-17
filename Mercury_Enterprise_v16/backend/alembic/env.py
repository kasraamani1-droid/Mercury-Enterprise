from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure `app` is importable when running from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.database import Base, import_orm_models  # noqa: E402

import_orm_models()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", settings.database_url)


def _configure_context(**kwargs) -> None:
    """SQLite needs batch mode for ALTER CONSTRAINT (e.g. create_foreign_key in 0005/0006).

    Production PostgreSQL uses native ALTER and does not require batch recreation.
    """
    url = kwargs.get("url") or (kwargs.get("connection").engine.url if kwargs.get("connection") else None)
    dialect = None
    if kwargs.get("connection") is not None:
        dialect = kwargs["connection"].dialect.name
    elif url is not None:
        dialect = str(url).split(":", 1)[0].split("+", 1)[0]
    render_as_batch = dialect == "sqlite"
    context.configure(
        target_metadata=target_metadata,
        render_as_batch=render_as_batch,
        **kwargs,
    )


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    _configure_context(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _configure_context(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
