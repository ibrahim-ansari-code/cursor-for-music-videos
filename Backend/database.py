import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from backend.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create async database engine
engine = create_async_engine(
    settings.DATABASE_URL, 
    echo=True,
)

# Create async session
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncSession:
    """
    Get an async database session
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Initialize the database and create all tables
    """
    logger.info("Initializing database")
    async with engine.begin() as conn:
        # Uncomment for dropping all tables (development only)
        # await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database initialized successfully")
