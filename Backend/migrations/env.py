from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import your models' metadata
from Backend.database import SQLModel
from Backend import *  # ensures all models are imported
target_metadata = SQLModel.metadata
# ───────────────────────────────────────────────
# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import settings and swap driver to psycopg2 for Alembic
from Backend.config import settings
config = context.config
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("asyncpg", "psycopg2")
)

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
# ───────────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

# ───────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
