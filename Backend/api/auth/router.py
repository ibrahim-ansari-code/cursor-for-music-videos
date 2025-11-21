"""
Authentication API routes.

This module contains all the FastAPI route handlers for authentication-related
endpoints including user profile management, webhooks, and future auth features.
"""

import logging
from typing import Optional
from uuid import UUID as PythonUUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.config import settings
from Backend.database import get_session
from Backend.models.user import User
from .dependencies import get_current_user, get_current_user_no_subscription_check
from .helpers import validate_webhook_secret
from .webhook_rate_limiter import check_webhook_rate_limit
from .schemas import (
    UserResponse,
    ProfileUpdateRequest,
    AvatarUploadResponse,
    SupabaseWebhookPayload,
    UserSyncRequest,
    UserSyncResponse,
    EmailVerificationRequest,
    PasswordVerificationRequest,
    PasswordChangeRequest
)
from .service import AuthService

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# === API Routes ===

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get current user profile.
    
    Returns the authenticated user's profile information.
    This endpoint is used by the frontend to validate sessions
    and retrieve user data on app initialization.
    """
    return await AuthService.get_user_profile(current_user)


@router.put("/users/{user_id}/profile", response_model=UserResponse)
async def update_user_profile(
    user_id: PythonUUID,
    profile_update: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update user profile.
    
    Users can only update their own profile unless they are admins.
    All fields in the profile update request are optional to allow
    partial updates.
    """
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's profile"
        )
    
    # Determine which user to update
    if current_user.is_admin and current_user.id != user_id:
        # Admin updating another user - fetch the target user
        user_to_update = await AuthService.get_user_by_id(user_id, session)
        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    else:
        # User updating their own profile
        user_to_update = current_user
    
    return await AuthService.update_user_profile(
        user_to_update,
        profile_update,
        session
    )


@router.post("/users/{user_id}/avatar", response_model=AvatarUploadResponse)
async def upload_user_avatar(
    user_id: PythonUUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Upload a new avatar image for a user.
    
    Only the user themselves or an admin can perform this action. 
    The image is stored in Azure Blob Storage, and the user's profile 
    is updated with the new avatar URL.
    
    Args:
        user_id: The UUID of the user whose avatar is being updated.
        file: The image file to upload.
    
    Returns:
        An object containing the URL of the uploaded avatar image.
    """
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's avatar"
        )
    
    # Determine which user to update
    if current_user.is_admin and current_user.id != user_id:
        # Admin updating another user - fetch the target user
        user_to_update = await AuthService.get_user_by_id(user_id, session)
        if not user_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    else:
        # User updating their own avatar
        user_to_update = current_user
    
    return await AuthService.upload_user_avatar(
        user_to_update,
        file,
        session
    )


@router.post("/webhook/user-sync", status_code=status.HTTP_200_OK)
async def supabase_webhook_handler(
    payload: SupabaseWebhookPayload,
    request: Request,
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret"),
    session: AsyncSession = Depends(get_session)
):
    """
    Handle Supabase webhook events for user synchronization.
    
    Enterprise-grade webhook handler with:
    - Rate limiting per IP
    - Authentication via webhook secret
    - Audit logging for all requests
    - Processing time tracking
    - Comprehensive error handling
    
    Processes INSERT and UPDATE events from auth.users table to keep
    local database in sync with Supabase authentication state.
    
    Args:
        payload: Webhook payload from Supabase
        request: FastAPI request object (for IP extraction)
        x_webhook_secret: Webhook secret header
        session: Database session
        
    Returns:
        Operation result message
        
    Raises:
        HTTPException: For authentication or rate limit failures
    """
    import time
    start_time = time.time()
    
    # Extract client IP for rate limiting and audit logging
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limiting check
    if not await check_webhook_rate_limit(client_ip):
        logger.warning("Webhook rate limit exceeded for IP: %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )
    
    # Verify webhook secret
    if not validate_webhook_secret(x_webhook_secret, settings.SUPABASE_WEBHOOK_SECRET):
        if not settings.SUPABASE_WEBHOOK_SECRET:
            logger.error("SUPABASE_WEBHOOK_SECRET not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook secret not configured"
            )
        else:
            logger.warning("Invalid webhook secret received from IP: %s", client_ip)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret"
            )
    
    # Process webhook with audit logging
    result = await AuthService.handle_webhook_user_sync(
        payload, 
        session,
        client_ip=client_ip,
        processing_start_time=start_time
    )
    
    return result


@router.post("/sync-user", response_model=UserSyncResponse, status_code=status.HTTP_200_OK)
async def sync_supabase_user(
    sync_request: UserSyncRequest,
    webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    session: AsyncSession = Depends(get_session)
):
    """
    Synchronize a Supabase user to the local database.
    
    If a user with the given Supabase user ID exists, returns the existing user. 
    Otherwise, creates a new user with default values and returns the newly created 
    user. Requires a valid webhook secret if configured; returns a 403 error if 
    the secret is missing or invalid.
    
    Returns:
        The existing or newly created user as a database model instance.
    
    Raises:
        HTTPException: If the webhook secret is invalid or user creation fails.
    """
    # Verify webhook secret if configured
    if settings.SUPABASE_WEBHOOK_SECRET:
        if not webhook_secret or webhook_secret != settings.SUPABASE_WEBHOOK_SECRET:
            logger.warning("Invalid webhook secret attempt for sync-user endpoint")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid webhook secret"
            )
    else:
        # If no webhook secret is configured, log a warning
        logger.warning("sync-user endpoint called without webhook secret configuration - this is insecure!")
    
    return await AuthService.sync_user_from_supabase(sync_request, session)


@router.post("/resend-verification")
async def resend_verification_email(
    request: EmailVerificationRequest
):
    """
    Resend email verification.
    
    This endpoint is called by the registration form when users need to
    resend their verification email. It accepts an email address and
    triggers Supabase to resend the confirmation email.
    
    Note: This endpoint does not require authentication since users
    who haven't verified their email yet cannot log in.
    
    Args:
        request: Contains the email address to resend verification to.
        
    Returns:
        Success message (generic for security - doesn't reveal if email exists).
    """
    # Use the email from request, not from authenticated user
    # since unverified users can't authenticate
    email = request.email
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is required"
        )
    
    result = await AuthService.resend_verification_email(email)
    return result


@router.post("/verify-password")
async def verify_password(
    request: PasswordVerificationRequest,
    current_user: User = Depends(get_current_user_no_subscription_check)
):
    """
    Verify current password without creating a new session.
    
    This endpoint is used by the SecurityForm component to verify the
    current password before allowing a password change. It doesn't create
    a new session, just validates the password.
    
    Args:
        request: Contains the password to verify.
        current_user: The authenticated user making the request.
        
    Returns:
        Success response if password is correct.
        
    Raises:
        HTTPException: 401 if password is incorrect.
    """
    # Verify the password using the user's email
    is_valid = await AuthService.verify_user_password(
        email=current_user.email,
        password=request.password
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    return {"success": True, "message": "Password verified"}


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user_no_subscription_check),
    session: AsyncSession = Depends(get_session)
):
    """
    Change password with current password verification.
    
    This endpoint allows authenticated users to change their password.
    It requires the current password for verification and validates
    the new password meets security requirements.
    
    Args:
        request: Contains current and new password.
        current_user: The authenticated user making the request.
        session: Database session (not used but kept for consistency).
        
    Returns:
        Success response if password was changed.
        
    Raises:
        HTTPException: 401 if current password is incorrect.
        HTTPException: 400 if new password doesn't meet requirements.
    """
    # Change the password using the service
    success = await AuthService.change_user_password(
        email=current_user.email,
        current_password=request.current_password,
        new_password=request.new_password
    )
    
    if success:
        return {"success": True, "message": "Password changed successfully"}
    else:
        # This shouldn't happen as the service raises exceptions
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )