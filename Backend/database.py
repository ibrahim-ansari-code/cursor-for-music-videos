import logging
import ssl # Import the ssl module
import Backend.models
from typing import AsyncGenerator
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode # For URL manipulation
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from Backend.config import settings
from Backend.models.user import User
from Backend.utils.supabase import get_supabase_client

# Configure logging
logger = logging.getLogger(__name__)

# Create async database engine
# Ensure settings.DATABASE_URL is loaded correctly by config.py
if not settings.DATABASE_URL or not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
    # Log the actual value for debugging if it exists but is wrong
    logger.error(f"DATABASE_URL environment variable invalid: {settings.DATABASE_URL}") 
    raise RuntimeError("DATABASE_URL environment variable not set/loaded correctly or missing asyncpg scheme.")

# Prepare database URL and SSL connect_args
db_url_to_use = settings.DATABASE_URL
ssl_connect_args = {}

# Parse the URL to handle sslmode
parsed_url = urlparse(settings.DATABASE_URL)
query_params = parse_qs(parsed_url.query)

if 'sslmode' in query_params:
    logger.info(f"Found 'sslmode' in DATABASE_URL: {query_params['sslmode']}. Removing it from URL string and using connect_args for SSL.")
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
    if "azure.com" in parsed_url.netloc: # Heuristic for Azure DBs
        logger.info("DATABASE_URL appears to be for Azure, ensuring SSL is enabled via connect_args.")
        ssl_context = ssl.create_default_context()
        ssl_connect_args = {"ssl": ssl_context}
    else:
        logger.info("No 'sslmode' in DATABASE_URL and not identified as Azure, SSL not explicitly configured via connect_args.")

# Log masked URL that will be used
masked_db_url_to_use = db_url_to_use.split('@')[-1] if '@' in db_url_to_use else db_url_to_use
logger.info(f"Preparing to create async engine. Effective URL (masked): ...@{masked_db_url_to_use}")
logger.info(f"Parsed hostname for connection: {parsed_url.hostname}") # Log parsed hostname
logger.info(f"Parsed port for connection: {parsed_url.port}") # Log parsed port
logger.info(f"SSL connect_args to be used: {ssl_connect_args}")

engine = create_async_engine(
    db_url_to_use, 
    echo=settings.DEBUG,    
    future=True,
    connect_args=ssl_connect_args # Pass SSL context here
)

# Create async session
async_session = sessionmaker(
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

async def init_db():
    """
    Initialize the database and create all tables.
    This should be called during application startup.
    """
    try:
        logger.info("Initializing database")
        async with engine.begin() as conn:
            # Uncomment for dropping all tables (development only)
            # await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
        
        # Create admin user if no users exist
        async with async_session() as session:
            result = await session.execute(select(User))
            if not result.scalar_one_or_none():
                # Get Supabase client
                supabase = get_supabase_client()
                
                # Create admin user in Supabase Auth
                auth_response = supabase.auth.admin.create_user({
                    "email": "admin@brikli.com",
                    "password": "admin123",  # This should be changed immediately
                    "email_confirm": True
                })
                
                if not auth_response.user:
                    raise Exception("Failed to create admin user in Supabase Auth")
                
                # Create admin user in our database
                admin_user = User(
                    id=auth_response.user.id,  # Use Supabase Auth UUID
                    email="admin@brikli.com",
                    first_name="Admin",
                    last_name="User",
                    user_type="ADMIN",
                    is_admin=True,
                    is_email_verified=True
                )

                session.add(admin_user)
                await session.commit()
                logger.info("Admin user created successfully")
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
