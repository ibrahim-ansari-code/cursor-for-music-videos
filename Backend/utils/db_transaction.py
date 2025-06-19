"""Database transaction utilities for proper transaction management."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@asynccontextmanager
async def db_transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database transactions with automatic rollback on errors.
    
    Usage:
        async with db_transaction(session) as tx:
            # Database operations here
            tx.add(some_object)
            # Commit happens automatically on success
            # Rollback happens automatically on exception
    
    Args:
        session: SQLAlchemy async session
        
    Yields:
        The same session for database operations
        
    Raises:
        Any exception that occurs during the transaction (after rollback)
    """
    try:
        yield session
        await session.commit()
        logger.debug("Transaction committed successfully")
    except Exception as e:
        logger.warning("Transaction failed, rolling back: %s", str(e))
        await session.rollback()
        raise


@asynccontextmanager
async def db_transaction_with_savepoint(session: AsyncSession, savepoint_name: str = "sp1") -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for nested transactions using savepoints.
    
    Useful for operations that need partial rollback capabilities within a larger transaction.
    
    Args:
        session: SQLAlchemy async session
        savepoint_name: Name for the savepoint
        
    Yields:
        The same session for database operations
        
    Raises:
        Any exception that occurs during the transaction (after rollback to savepoint)
    """
    savepoint = await session.begin_nested()
    try:
        yield session
        await savepoint.commit()
        logger.debug("Savepoint %s committed successfully", savepoint_name)
    except Exception as e:
        logger.warning("Savepoint %s failed, rolling back: %s", savepoint_name, str(e))
        await savepoint.rollback()
        raise


async def execute_in_transaction(session: AsyncSession, operation_func, *args, **kwargs):
    """
    Execute a function within a database transaction.
    
    Args:
        session: SQLAlchemy async session
        operation_func: Async function to execute in transaction
        *args: Arguments to pass to operation_func
        **kwargs: Keyword arguments to pass to operation_func
        
    Returns:
        Result of operation_func
        
    Raises:
        Any exception from operation_func (after rollback)
    """
    async with db_transaction(session):
        return await operation_func(session, *args, **kwargs)
