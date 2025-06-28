"""
Authentication dependencies for FastAPI.

This module contains dependency injection functions used across authentication
endpoints, primarily for user authentication and authorization.
"""

import logging
import traceback
from uuid import UUID as PythonUUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import col

from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.utils.supabase import get_supabase_client

# Configure logging
logger = logging.getLogger(__name__)

# Set up security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Retrieves the current authenticated user based on a Supabase JWT token.
    
    Validates the provided JWT token with Supabase, extracts the user ID, and attempts 
    to fetch the corresponding user from the local database. If the user does not exist 
    locally, performs just-in-time (JIT) user creation in a concurrency-safe manner 
    using a nested transaction. Raises HTTP exceptions for invalid credentials or 
    unexpected errors.
    
    Args:
        credentials: The HTTP authorization credentials containing the JWT token.
        session: The database session for user queries.
    
    Returns:
        The authenticated User instance from the local database.
        
    Raises:
        HTTPException: For authentication failures or server errors.
    """
    user_response_from_supabase = None
    try:
        supabase = get_supabase_client()
        user_response_from_supabase = supabase.auth.get_user(
            credentials.credentials)

        if not user_response_from_supabase or not hasattr(user_response_from_supabase, 'user') or not user_response_from_supabase.user:
            logger.warning(
                "Supabase auth.get_user did not return a user or in expected format.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials (user data not returned by Supabase in expected format)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        actual_user_from_supabase = user_response_from_supabase.user

        if not hasattr(actual_user_from_supabase, 'id') or actual_user_from_supabase.id is None:
            logger.error("Supabase user object (nested) is missing ID. Repr: %s", repr(
                actual_user_from_supabase))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase user object (nested) is missing ID.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Quick sanity-check that the ID looks like a UUID
        try:
            uuid_obj = PythonUUID(str(actual_user_from_supabase.id))
        except ValueError as e:
            logger.warning("Supabase ID is not a valid UUID: %s",
                           actual_user_from_supabase.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        # Use session.get which handles primary-key lookup and proper typing
        db_user = await session.get(User, uuid_obj)

        # Fallback to explicit select if session.get returned None (e.g., composite PK future changes)
        if db_user is None:
            result = await session.execute(select(User).where(col(User.id) == uuid_obj))
            db_user = result.scalar_one_or_none()

        if not db_user:
            logger.warning(
                "User with Supabase ID %s not found in local database. Attempting JIT creation.", actual_user_from_supabase.id)
            
            # Use a transaction with a lock to prevent race conditions
            async with session.begin_nested():
                # Re-check if user was created by a concurrent request while we were waiting for the lock
                check_user_again = await session.get(User, uuid_obj)
                if check_user_again:
                    logger.info("User %s was created by a concurrent request. Using existing user.", uuid_obj)
                    return check_user_again

                # JIT User Creation - if still not found, proceed with creation
                user_metadata = actual_user_from_supabase.user_metadata or {}
                full_name = user_metadata.get("full_name", "")
                first_name = user_metadata.get("first_name")
                last_name = user_metadata.get("last_name")

                if not first_name and full_name:
                    parts = full_name.split(" ", 1)
                    first_name = parts[0]
                    last_name = parts[1] if len(parts) > 1 else ""

                new_user_data = {
                    "id": uuid_obj,
                    "email": actual_user_from_supabase.email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_email_verified": user_metadata.get("email_verified", False),
                    "user_type": UserType.LANDLORD
                }

                db_user = User.model_validate(new_user_data)
                session.add(db_user)
                await session.flush() # Use flush instead of commit inside the nested transaction
                logger.info("Successfully provisioned user %s via JIT.", db_user.id)
            
            # After the nested transaction commits to a savepoint, refresh the object to ensure
            # it's up-to-date in the parent session. The final commit of the overall transaction
            # is handled by the FastAPI dependency lifecycle (e.g., a middleware) to ensure
            # the entire request is treated as a single unit of work.
            await session.refresh(db_user)

        return db_user
    except HTTPException as http_exc:  # Re-raise HTTPException to preserve status code and details
        raise http_exc
    except Exception as e:
        logger.error(
            "Authentication error in get_current_user. Exception type: %s, Exception: %s", type(e), repr(e))
        logger.error("Traceback: %s", traceback.format_exc())
        # Log the state of user_response_from_supabase if it was assigned
        if 'user_response_from_supabase' in locals() and user_response_from_supabase is not None:
            logger.error("State of user_response_from_supabase when error occurred: type=%s, repr=%s, attributes: %s", type(
                user_response_from_supabase), repr(user_response_from_supabase), dir(user_response_from_supabase))
        else:
            logger.error(
                "user_response_from_supabase was not successfully assigned or was None prior to the error.")
        raise HTTPException(
            # Changed from 401 to 500 for unexpected errors
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not validate credentials due to an unexpected server error: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensures the current user is active.
    
    Args:
        current_user: The authenticated user from get_current_user.
        
    Returns:
        The active user instance.
        
    Raises:
        HTTPException: If the user account is deactivated.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensures the current user is an admin.
    
    Args:
        current_user: The authenticated active user.
        
    Returns:
        The admin user instance.
        
    Raises:
        HTTPException: If the user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_current_verified_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Ensures the current user has a verified email.
    
    Args:
        current_user: The authenticated active user.
        
    Returns:
        The verified user instance.
        
    Raises:
        HTTPException: If the user's email is not verified.
    """
    if not current_user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user