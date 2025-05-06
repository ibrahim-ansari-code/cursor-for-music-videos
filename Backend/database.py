import logging
import os
import Backend.models
from typing import Optional, AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from passlib.context import CryptContext

from Backend.config import settings
from Backend.models.user import User

# Configure logging
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create async database engine
# Ensure settings.DATABASE_URL is loaded correctly by config.py
if not settings.DATABASE_URL or not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
    # Log the actual value for debugging if it exists but is wrong
    logger.error(f"DATABASE_URL environment variable invalid: {settings.DATABASE_URL}") 
    raise RuntimeError("DATABASE_URL environment variable not set/loaded correctly or missing asyncpg scheme.")

# Log masked URL
masked_db_url = settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL
logger.info(f"Creating async engine with URL: ...@{masked_db_url}")

engine = create_async_engine(
    settings.DATABASE_URL,  # Use DATABASE_URL directly from settings
    echo=settings.DEBUG,    # Only echo SQL in debug mode
    future=True
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
                admin_user = User(
                    email="admin@brikli.com",
                    hashed_password=pwd_context.hash("admin123"),
                    first_name="Admin",
                    last_name="User",
                    user_type="ADMIN",
                    is_admin=True
                )

                session.add(admin_user)
                await session.commit()
                logger.info("Admin user created successfully")
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
