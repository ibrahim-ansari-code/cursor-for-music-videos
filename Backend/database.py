import logging
import ssl  # Import the ssl module
from typing import AsyncGenerator
from urllib.parse import (parse_qs, urlencode,  # For URL manipulation
                          urlparse, urlunparse)
import os

from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)

from Backend.config import settings

# Configure logging
logger = logging.getLogger(__name__)


def _mask_database_url(url: str) -> str:
    """
    Mask sensitive credentials in database URL for safe logging.

    Args:
        url: Database URL that may contain credentials

    Returns:
        Masked URL with credentials hidden
    """
    if '@' in url:
        # Split on @ to separate credentials from host
        parts = url.split('@')
        if len(parts) >= 2:
            # Take everything after the last @ (host/db part)
            host_part = '@'.join(parts[1:])
            # Get the scheme part before credentials
            scheme_part = parts[0].split('://')[0] if '://' in parts[0] else ''
            # Only include scheme if it's non-empty to avoid malformed URLs
            if scheme_part:
                return f"{scheme_part}://***:***@{host_part}"
            else:
                return f"***:***@{host_part}"
    return url


# Create async database engine
# Ensure settings.DATABASE_URL is loaded correctly by config.py
if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable not set/loaded correctly.")

# Convert standard postgresql:// URLs to postgresql+asyncpg:// for async support
database_url = settings.DATABASE_URL
if database_url.startswith("postgresql://"):
    database_url = database_url.replace(
        "postgresql://", "postgresql+asyncpg://", 1)
    logger.info(
        "Converted standard PostgreSQL URL to asyncpg format for async support")
elif not database_url.startswith("postgresql+asyncpg://"):
    masked_url = _mask_database_url(settings.DATABASE_URL)
    logger.error("DATABASE_URL environment variable invalid: %s", masked_url)
    raise RuntimeError(
        "DATABASE_URL environment variable not set/loaded correctly or missing supported scheme.")

# Prepare database URL and SSL connect_args
db_url_to_use = database_url
ssl_connect_args = {}

# Parse the URL to handle sslmode
parsed_url = urlparse(database_url)
query_params = parse_qs(parsed_url.query)

if 'sslmode' in query_params:
    logger.info(
        f"Found 'sslmode' in DATABASE_URL: {query_params['sslmode']}. Removing it from URL string and using connect_args for SSL.")
    # For Azure PostgreSQL, 'sslmode=require' is common.
    # We will enforce SSL via connect_args instead of the URL query parameter.
    del query_params['sslmode']
    # Reconstruct the query string without sslmode
    new_query_string = urlencode(query_params, doseq=True)
    # Reconstruct the URL without sslmode in the query part
    db_url_to_use = urlunparse(parsed_url._replace(query=new_query_string))

    # Regardless of original sslmode, if it was present, we ensure SSL is used via connect_args.
    # For 'require', 'prefer', or 'allow' that results in an SSL connection:
    ssl_context = ssl.create_default_context()
    # For Azure, it might be necessary to specify CA certs if default ones don't work.
    # Example: ssl_context.load_verify_locations(cafile='/path/to/azure/ca.pem')
    # For now, using create_default_context() is standard for 'sslmode=require'.
    ssl_connect_args = {"ssl": ssl_context}
    logger.info("Configuring SSL for asyncpg using connect_args.")
else:
    # If connecting to Azure and SSL is implicitly required even without sslmode in URL,
    # you might still need to set ssl_connect_args here.
    # For Azure PostgreSQL Flexible Server, SSL is typically enforced by the server.
    # If DATABASE_URL is for Azure and doesn't have sslmode, assume SSL is needed.
    # This is a common scenario for managed cloud PostgreSQL services.
    if "azure.com" in parsed_url.netloc:  # Heuristic for Azure DBs
        logger.info(
            "DATABASE_URL appears to be for Azure, ensuring SSL is enabled via connect_args.")
        ssl_context = ssl.create_default_context()
        ssl_connect_args = {"ssl": ssl_context}
    else:
        logger.info(
            "No 'sslmode' in DATABASE_URL and not identified as Azure, SSL not explicitly configured via connect_args.")

# Log masked URL that will be used
masked_db_url_to_use = db_url_to_use.split(
    '@')[-1] if '@' in db_url_to_use else db_url_to_use
logger.info(
    f"Preparing to create async engine. Effective URL (masked): ...@{masked_db_url_to_use}")
# Log parsed hostname
logger.info(f"Parsed hostname for connection: {parsed_url.hostname}")
# Log parsed port
logger.info(f"Parsed port for connection: {parsed_url.port}")
logger.info(f"SSL connect_args to be used: {ssl_connect_args}")

# Determine if SQL queries should be logged
# Only enable SQL echoing when explicitly requested via SQL_DEBUG environment variable
sql_echo = os.getenv('SQL_DEBUG', '').lower() in ('true', '1', 'yes')
if sql_echo:
    logger.info("🔍 SQL query logging enabled via SQL_DEBUG environment variable")

engine = create_async_engine(
    db_url_to_use,
    echo=sql_echo,  # Only log SQL when SQL_DEBUG is set
    future=True,
    connect_args=ssl_connect_args  # Pass SSL context here
)

# Create async session
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    This is a FastAPI dependency that can be used in route handlers.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            await session.close()
