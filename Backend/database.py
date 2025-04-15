import logging
import os
import Backend.models
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from passlib.context import CryptContext

from Backend.config import settings
from Backend.models.user import User

# Configure logging
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_database_url() -> str:
    """
    Get the appropriate database URL based on environment configuration.
    Falls back to SQLite if no DATABASE_URL is provided.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        logger.info("Using provided DATABASE_URL for database connection")
        return database_url
    
    # Default to SQLite
    sqlite_path = "sqlite:///./brikli.db"
    logger.info(f"No DATABASE_URL provided, falling back to SQLite at {sqlite_path}")
    return sqlite_path

# Create async database engine
engine = create_async_engine(
    get_database_url(),
    echo=settings.DEBUG,  # Only echo SQL in debug mode
    future=True,
    connect_args={"ssl": "require"}  # Use SQLAlchemy 2.0 style
)

# Create async session
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncSession:
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
                    is_admin=True
                )
                session.add(admin_user)
                await session.commit()
                logger.info("Admin user created successfully")
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
