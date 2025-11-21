"""
Authentication dependencies for FastAPI.

This module contains dependency injection functions used across authentication
endpoints, primarily for user authentication and authorization.
"""

import logging
import traceback
import sentry_sdk
from uuid import UUID as PythonUUID

from fastapi import Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import (
    InterfaceError,
    OperationalError, 
    DisconnectionError,
    TimeoutError as SQLTimeoutError,
    DatabaseError
)
from sqlmodel import col

from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.utils.supabase import get_supabase_client
from Backend.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Set up security scheme
security = HTTPBearer()


async def _handle_auth_exception(
    exception: Exception, 
    context: str,
    user_response = None
) -> None:
    """
    Handle authentication exceptions with proper type checking and observability.
    
    This function provides robust, production-grade exception handling that:
    - Uses isinstance() checks instead of fragile string matching
    - Provides proper HTTP status codes for different error types
    - Integrates with Sentry for comprehensive error tracking
    - Includes contextual information for debugging
    - Follows enterprise patterns for error resilience
    
    Args:
        exception: The caught exception to handle
        context: String identifier for where the exception occurred
        user_response: Optional user response from Supabase for context
        
    Returns:
        HTTPException with appropriate status code and details
        
    Raises:
        HTTPException: Always raises an appropriate HTTP exception
    """
    exception_type = type(exception).__name__
    
    # Capture comprehensive context for Sentry
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("component", "authentication")
        scope.set_tag("function", context)
        scope.set_tag("exception_type", exception_type)
        
        # Add user context if available
        if user_response and hasattr(user_response, 'user') and user_response.user:
            scope.set_user({
                "id": getattr(user_response.user, 'id', 'unknown'),
                "email": getattr(user_response.user, 'email', 'unknown')
            })
        
        scope.set_context("auth_context", {
            "user_response_available": user_response is not None,
            "user_response_type": type(user_response).__name__ if user_response else None,
            "exception_message": str(exception),
            "has_supabase_user": (
                user_response and 
                hasattr(user_response, 'user') and 
                user_response.user is not None
            ) if user_response else False
        })
        
        # Handle database connection errors with proper isinstance checks
        if isinstance(exception, (InterfaceError, DisconnectionError, OperationalError)):
            logger.error(
                "Database connection error in %s: %s - %s", 
                context, exception_type, str(exception)
            )
            
            # Capture database connectivity issue
            sentry_sdk.capture_exception(exception)
            
            # Return user-friendly error with retry guidance
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection temporarily unavailable. Please try again in a few seconds.",
                headers={
                    "WWW-Authenticate": "Bearer", 
                    "Retry-After": "5",
                    "X-Error-Type": "database_connection"
                },
            )
        
        # Handle database timeout errors
        elif isinstance(exception, SQLTimeoutError):
            logger.error(
                "Database timeout error in %s: %s", 
                context, str(exception)
            )
            
            sentry_sdk.capture_exception(exception)
            
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timeout. Please try again.",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "Retry-After": "3",
                    "X-Error-Type": "database_timeout"
                },
            )
        
        # Handle general database errors
        elif isinstance(exception, DatabaseError):
            logger.error(
                "Database error in %s: %s - %s", 
                context, exception_type, str(exception)
            )
            
            sentry_sdk.capture_exception(exception)
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service temporarily unavailable.",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Error-Type": "database_error"
                },
            )
        
        # Handle all other exceptions
        else:
            logger.error(
                "Authentication error in %s. Exception type: %s, Exception: %s", 
                context, exception_type, repr(exception)
            )
            logger.error("Traceback: %s", traceback.format_exc())
            
            # Log user response state for debugging if available
            if user_response is not None:
                logger.error(
                    "State of user_response when error occurred: type=%s, repr=%s, attributes: %s", 
                    type(user_response), 
                    repr(user_response), 
                    dir(user_response)
                )
            else:
                logger.error(
                    "user_response was not successfully assigned or was None prior to the error."
                )
            
            # Capture the unexpected exception in Sentry
            sentry_sdk.capture_exception(exception)
            
            # Return generic server error without exposing internals
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service temporarily unavailable. Please try again.",
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Error-Type": "internal_server_error"
                },
            )


def parse_user_name(user_metadata: dict) -> tuple[Optional[str], Optional[str]]:
    """
    Extract first_name and last_name from Supabase user metadata
    
    Args:
        user_metadata: Supabase user metadata dictionary
        
    Returns:
        Tuple of (first_name, last_name), both strings or None
    """
    full_name = user_metadata.get("full_name", "")
    first_name = user_metadata.get("first_name")
    last_name = user_metadata.get("last_name")

    if not first_name and full_name:
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    return first_name, last_name


def get_token_from_request(
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for SSE authentication")
) -> str:
    """
    Extract JWT token from either Authorization header or query parameter.
    
    This function supports both standard header-based authentication and 
    query parameter authentication for SSE compatibility (EventSource can't send headers).
    
    Args:
        request: The FastAPI request object
        token: Optional JWT token from query parameter
        
    Returns:
        The JWT token string
        
    Raises:
        HTTPException: If no valid token is found
    """
    # Try Authorization header first (standard)
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    # Fall back to query parameter (for SSE)
    if token:
        return token
    
    # No valid token found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No valid authentication token provided. Use Authorization header or 'token' query parameter.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    request: Request,  # Injected by FastAPI automatically
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
    check_subscription: bool = True  # ENABLED: Blocks write operations, allows read
) -> User:
    """
    Retrieves the current authenticated user based on a Supabase JWT token.
    
    Validates the provided JWT token with Supabase, extracts the user ID, and attempts 
    to fetch the corresponding user from the local database. If the user does not exist 
    locally, performs just-in-time (JIT) user creation in a concurrency-safe manner 
    using a nested transaction. Raises HTTP exceptions for invalid credentials or 
    unexpected errors.
    
    **Subscription Enforcement:**
    - GET requests (read operations): FREE - users can browse without subscription
    - POST/PUT/DELETE/PATCH (write operations): REQUIRES subscription
    - Admins: ALWAYS bypass subscription checks
    - Billing routes: Use get_current_user_no_subscription_check
    
    **User Experience:**
    - Users can sign up and explore the app freely
    - When they try to create/modify data, they get a 402 error
    - Frontend catches 402 and shows subscription modal
    - Graceful upgrade flow, no hard blocks on login
    
    Args:
        request: The FastAPI request object (auto-injected) for checking HTTP method.
        credentials: The HTTP authorization credentials containing the JWT token.
        session: The database session for user queries.
        check_subscription: If True (default), requires active subscription for write operations.
    
    Returns:
        The authenticated User instance from the local database.
        
    Raises:
        HTTPException: 
            - 401: Authentication failures
            - 402: Subscription required (write operations only)
            - 500: Server errors
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
            # User not found - webhook should have created them
            logger.error(
                "User with Supabase ID %s not found in local database. "
                "This indicates the webhook is not functioning correctly.",
                uuid_obj
            )
            
            # Capture error in Sentry for monitoring
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "authentication")
                scope.set_tag("error_type", "user_not_synced")
                scope.set_tag("user_id", str(uuid_obj))
                scope.set_tag("email", actual_user_from_supabase.email)
                scope.set_context("auth_failure", {
                    "supabase_id": str(uuid_obj),
                    "email": actual_user_from_supabase.email,
                    "reason": "user_not_found_in_local_db"
                })
                sentry_sdk.capture_message(
                    "User authentication failed - not synced from Supabase",
                    level="error"
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Your account has not been properly synchronized. "
                    "Please try signing out and signing in again. "
                    "If this persists, contact support@brikli.com"
                ),
                headers={
                    "WWW-Authenticate": "Bearer",
                    "X-Error-Type": "user_not_synced",
                    "X-Support-Contact": "support@brikli.com"
                },
            )
        
        # ============================================================
        # SUBSCRIPTION CHECK (enforced platform-wide)
        # ============================================================
        if check_subscription:
            from datetime import datetime, timezone as dt_timezone
            
            # Auto-exempt GET requests (read operations) - users can browse without subscription
            if request and request.method == "GET":
                logger.debug(f"GET request - bypassing subscription check for user {db_user.email}")
                return db_user
            
            # Admins bypass subscription requirement
            if not db_user.is_admin:
                # Check subscription status (denormalized on user for fast access)
                has_active_subscription = db_user.subscription_status in ['active', 'trialing']
                
                # Check trial period as fallback
                in_trial_period = False
                if db_user.trial_ends_at:
                    now = datetime.now(dt_timezone.utc)
                    trial_end = db_user.trial_ends_at
                    
                    # Ensure trial_end is timezone-aware
                    if trial_end.tzinfo is None:
                        trial_end = trial_end.replace(tzinfo=dt_timezone.utc)
                    
                    if trial_end > now:
                        in_trial_period = True
                
                # Deny access if no active subscription or trial
                if not has_active_subscription and not in_trial_period:
                    logger.warning(
                        f"Subscription required | "
                        f"user_id={db_user.id} | "
                        f"email={db_user.email} | "
                        f"status={db_user.subscription_status} | "
                        f"trial_ends_at={db_user.trial_ends_at}"
                    )
                    
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail={
                            "code": "SUBSCRIPTION_REQUIRED",
                            "message": "Active subscription required to access this resource",
                            "subscription_status": db_user.subscription_status,
                            "trial_ended": bool(db_user.trial_ends_at and db_user.trial_ends_at < now),
                            "upgrade_url": f"{settings.FRONTEND_URL}/settings?tab=billing"
                        }
                    )

        return db_user
    except HTTPException as http_exc:  # Re-raise HTTPException to preserve status code and details
        raise http_exc
    except Exception as e:
        await _handle_auth_exception(
            e, 
            context="get_current_user",
            user_response=user_response_from_supabase if 'user_response_from_supabase' in locals() else None
        )
        # This line should never be reached due to HTTPException being raised in _handle_auth_exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
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


async def get_current_landlord_or_admin(
    current_user: User = Depends(get_current_verified_user)
) -> User:
    """
    Ensures the current user is a landlord or admin (not a tenant).
    
    Used for features that require property management permissions,
    such as tax preferences, property management, and financial reporting.
    
    Args:
        current_user: The authenticated verified user.
        
    Returns:
        The user if they are landlord or admin.
        
    Raises:
        HTTPException: If the user is a tenant.
    """
    if current_user.user_type == UserType.TENANT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden for tenant users"
        )
    return current_user


async def get_user_id(current_user: User = Depends(get_current_user)) -> PythonUUID:
    """
    Dependency to get the current user's ID directly.
    
    This avoids lazy loading issues in async exception handlers by eagerly
    extracting the user_id from the User object. Use this when you only need
    the user_id and don't need the full User object.
    
    Args:
        current_user: The authenticated user from get_current_user dependency
        
    Returns:
        PythonUUID: The user's ID
    """
    return current_user.id


async def get_current_user_sse(
    request: Request,
    session: AsyncSession = Depends(get_session),
    token: Optional[str] = Query(None, description="JWT token for SSE authentication")
) -> User:
    """
    SSE-compatible version of get_current_user that supports query parameter authentication.
    
    This function is designed for Server-Sent Events endpoints where standard EventSource
    cannot send custom headers. It supports both Authorization headers and query parameters.
    
    Args:
        request: The FastAPI request object
        session: The database session for user queries
        token: Optional JWT token from query parameter
        
    Returns:
        The authenticated User instance from the local database
        
    Raises:
        HTTPException: If authentication fails or user is not found
    """
    try:
        # Extract token from either header or query parameter
        jwt_token = get_token_from_request(request, token)
        
        # Use Supabase to validate the JWT (reuse existing logic)
        supabase = get_supabase_client()
        user_response_from_supabase = supabase.auth.get_user(jwt_token)
        
        if not user_response_from_supabase:
            logger.error("Supabase auth.get_user returned None or falsy response")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials (no user response from Supabase)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract the user from the response
        if not hasattr(user_response_from_supabase, 'user') or user_response_from_supabase.user is None:
            logger.error("Supabase response missing user data")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials (user data not returned by Supabase)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        actual_user_from_supabase = user_response_from_supabase.user

        if not hasattr(actual_user_from_supabase, 'id') or actual_user_from_supabase.id is None:
            logger.error("Supabase user object is missing ID")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase user object is missing ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Convert to UUID
        try:
            uuid_obj = PythonUUID(str(actual_user_from_supabase.id))
        except ValueError as e:
            logger.warning("Supabase ID is not a valid UUID: %s", actual_user_from_supabase.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

        # Check for existing user in database
        db_user = await session.get(User, uuid_obj)
        
        if db_user:
            return db_user

        # JIT user creation (same logic as regular auth)
        logger.warning("User with Supabase ID %s not found in local database. Attempting JIT creation.", uuid_obj)
        
        async with session.begin_nested():
            # Re-check if user was created by concurrent request
            check_user_again = await session.get(User, uuid_obj)
            if check_user_again:
                logger.info("User %s was created by a concurrent request. Using existing user.", uuid_obj)
                return check_user_again

            # Create new user
            metadata = actual_user_from_supabase.user_metadata if hasattr(actual_user_from_supabase, 'user_metadata') else {}
            first_name, last_name = parse_user_name(metadata)
            
            # Ensure email is not None
            user_email = actual_user_from_supabase.email
            if not user_email:
                logger.error("Supabase user has no email address")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User account is missing email address",
                )
            
            new_user = User(
                id=uuid_obj,
                email=user_email,
                first_name=first_name,
                last_name=last_name,
                phone=actual_user_from_supabase.phone if hasattr(actual_user_from_supabase, 'phone') else None,
                user_type=UserType.LANDLORD.value,  # Use .value for enum
            )
            
            session.add(new_user)
            await session.flush()  # Use flush instead of commit inside the nested transaction
            
        # After the nested transaction commits to a savepoint, refresh the object
        await session.refresh(new_user)
        
        logger.info("Successfully created new user via SSE auth: %s", new_user.id)
        return new_user

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        await _handle_auth_exception(
            e,
            context="get_current_user_sse",
            user_response=user_response_from_supabase if 'user_response_from_supabase' in locals() else None
        )
        # This line should never be reached due to HTTPException being raised in _handle_auth_exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


# ============================================================
# SUBSCRIPTION-EXEMPT DEPENDENCY
# ============================================================

async def get_current_user_no_subscription_check(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
) -> User:
    """
    Dependency that authenticates the user WITHOUT checking subscription status.
    
    **Use Case:**
    Only use this for routes where users MUST have access regardless of subscription:
    - Password management endpoints (/auth/verify-password, /auth/change-password)
    - Billing endpoints (/billing/checkout-session, /billing/portal-session, /billing/status, /billing/resume)
    
    **DO NOT use this for:**
    - Core platform features (properties, leases, tenants, accounting, etc.)
    - Any feature that should be subscription-gated
    
    Example:
        ```python
        @router.post("/billing/checkout-session")
        async def create_checkout(
            current_user: User = Depends(get_current_user_no_subscription_check),
            ...
        ):
            # User can access this even without active subscription
            ...
        ```
    
    Args:
        request: The FastAPI request object (auto-injected).
        credentials: The HTTP authorization credentials containing the JWT token.
        session: The database session for user queries.
    
    Returns:
        The authenticated User instance (subscription not checked).
        
    Raises:
        HTTPException: For authentication failures only.
    """
    return await get_current_user(
        request=request,
        credentials=credentials,
        session=session,
        check_subscription=False
    )
