"""
Alembic migration environment configuration script for the Brikli backend.

This script is invoked by Alembic to configure and run database migrations.
It sets up the database connection, specifies the target metadata for autogenerate,
and defines how migrations are executed in both 'offline' and 'online' modes.

Key Considerations:
- Transaction Handling: By default, migrations in 'online' mode are run within a
  database transaction (`context.begin_transaction()`). Individual migration scripts
  can use `transactional = False` as a hint for operations that might require
  non-transactional DDL, but the overall `env.py` execution maintains a
  transactional block for most operations.
- Row-Level Security (RLS) Policies: Certain database operations, particularly
  those involving RLS policies, may require non-transactional execution or manual
  steps outside of the standard Alembic transaction. For instance, RLS policies might
  need to be dropped before running `alembic upgrade head` and then reapplied.
- Model Imports: All SQLModel models must be imported into this script to ensure
  Alembic can detect them for autogeneration purposes.
- Database URL: The script dynamically sets the `sqlalchemy.url` for Alembic using
  the `DATABASE_URL` from application settings, converting `asyncpg` to `psycopg2`
  for compatibility with Alembic's synchronous operations.
"""
import logging
from Backend.config import settings
from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import your models' metadata
from sqlmodel import SQLModel

target_metadata = SQLModel.metadata

# ───────────────────────────────────────────────
# Ensure project root is in sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

# Import settings and swap driver to psycopg2 for Alembic

# This is the Alembic Config object
config = context.config

# Override sqlalchemy.url with our database URL from settings
# Replace asyncpg with psycopg2 for Alembic compatibility
database_url = settings.DATABASE_URL
if not database_url:
    raise ValueError("DATABASE_URL environment variable is not set")

config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("asyncpg", "psycopg2")
)

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Added logger instance if not already present globally in this script context
logger = logging.getLogger("alembic.env")

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
    """
    Runs Alembic migrations in online mode using a synchronous database connection.

    Establishes a connection to the database, configures the Alembic context
    with the current SQLModel metadata, and executes migrations within a
    transaction block. This approach ensures that all migrations are applied
    atomically, except for operations that require manual intervention (such as
    Row-Level Security policy changes).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # The transactional flag should be primarily controlled by the script file itself
        # if `context.begin_transaction()` is not unconditionally called.
        # For simplicity and to ensure `transactional = False` in scripts has a chance,
        # we will rely on the script's directive if the context is not already in a transaction.
        # However, the standard Alembic recipe usually wraps context.run_migrations()
        # in a transaction. The `transactional = False` in the script is more of a hint
        # for certain backends or operations.

        # Standard approach: Let individual scripts manage non-transactional DDL if needed by
        # using `op.execute` with appropriate session/connection handling or by ensuring
        # specific DDL commands are known to operate outside transactions on the target DB.
        # The previous attempt to make env.py dynamically switch based on script.transactional
        # was problematic. Let's revert to a more standard env.py transactional block and
        # rely on `transactional = False` in the script to influence specific op commands
        # if supported, or manual steps for problematic DDL like RLS policies.

        # The `transactional=False` in the script file is a directive to operations
        # within that script, not necessarily a switch for this env.py block itself
        # for all database backends in a simple way.
        # We will keep the transaction block here, as it's standard for most migrations.
        # The manual dropping of policies *before* this entire `alembic upgrade head`
        # is the key for the current RLS issue.
        logger.info("Configuring Alembic context to run migrations.")
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            logger.info("Executing migrations within a transaction.")
            context.run_migrations()


# ───────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
