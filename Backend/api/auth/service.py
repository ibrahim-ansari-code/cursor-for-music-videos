"""
Authentication service layer.

This module contains the business logic for authentication operations,
separated from the API route handlers for better organization and testing.
"""

import json
import logging
import sentry_sdk
from datetime import datetime, timezone
from uuid import UUID as PythonUUID

from fastapi import HTTPException, UploadFile, status
from supabase_auth.errors import AuthApiError, AuthError, AuthInvalidCredentialsError, AuthWeakPasswordError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.utils.azure_blob import upload_avatar_to_blob
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.utils.supabase import get_supabase_client
from .helpers import extract_user_metadata_from_supabase, touch_updated_at
from .schemas import (
    ProfileUpdateRequest,
    SupabaseWebhookPayload,
    UserResponse,
    UserSyncRequest,
    AvatarUploadResponse
)

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication-related operations."""
    
    @staticmethod
    async def get_user_by_id(user_id: PythonUUID, session: AsyncSession) -> User | None:
        """
        Get a user by their ID from the database.
        
        Args:
            user_id: The UUID of the user to retrieve.
            session: Database session for the query.
            
        Returns:
            The User instance if found, None otherwise.
        """
        user = await session.get(User, user_id)
        return user
    
    @staticmethod
    async def create_user_from_supabase(
        supabase_user_id: str,
        email: str,
        metadata: dict,
        session: AsyncSession
    ) -> User:
        """
        Create a new user in the local database from Supabase data.
        
        Args:
            supabase_user_id: The user's ID from Supabase (as string).
            email: The user's email address.
            metadata: Dictionary containing user metadata (first_name, last_name, phone, etc.).
            session: Database session for creating the user.
            
        Returns:
            The newly created User instance.
            
        Raises:
            HTTPException: If user creation fails or ID format is invalid.
        """
        # Convert user_id string to UUID
        try:
            uuid_obj = PythonUUID(supabase_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Use a transaction with SELECT FOR UPDATE to prevent race conditions
        user_to_return = None
        
        async with session.begin_nested():
            # Try to get the user with a lock
            result = await session.execute(
                select(User).where(col(User.id) == uuid_obj).with_for_update(skip_locked=False)
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.info("User %s already exists (found with lock), returning existing user", uuid_obj)
                user_to_return = existing_user
            else:
                # Create new user data within the locked transaction
                # Use user_type from metadata if provided, otherwise default to LANDLORD
                user_type_str = metadata.get("user_type", "LANDLORD")
                if isinstance(user_type_str, str):
                    user_type = UserType(user_type_str)
                else:
                    user_type = user_type_str if isinstance(user_type_str, UserType) else UserType.LANDLORD

                new_user_data = {
                    "id": uuid_obj,
                    "email": email,
                    "first_name": metadata.get("first_name"),
                    "last_name": metadata.get("last_name"),
                    "phone": metadata.get("phone"),
                    "user_type": user_type,
                    "is_active": True,
                    "is_admin": False,
                    "is_email_verified": metadata.get("is_email_verified", False),
                    "created_at": create_audit_datetime(),
                    "updated_at": create_audit_datetime(),
                    "address": None,
                    "city": None,
                    "province": None,
                    "postal_code": None,
                    "profile_image_url": None
                }
                
                try:
                    db_user = User.model_validate(new_user_data)
                    session.add(db_user)
                    await session.flush()  # Flush within the nested transaction
                    logger.info("Successfully created user %s from Supabase data", uuid_obj)
                    user_to_return = db_user
                    # The nested transaction will commit to a savepoint
                except Exception as e:
                    logger.error("Error creating user %s: %s", uuid_obj, str(e))
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to create user: {str(e)}"
                    ) from e
        
        # Refresh the user after the nested transaction commits if it was newly created
        if user_to_return and hasattr(user_to_return, '_sa_instance_state'):
            await session.refresh(user_to_return)
        
        return user_to_return
    
    @staticmethod
    async def get_user_profile(user: User, session: AsyncSession | None = None) -> UserResponse:
        """
        Get user profile information.

        For TENANT users, this also updates their portal login tracking
        (last_portal_login_at and portal_status) to track seat usage.

        Args:
            user: The user instance to return.
            session: Database session (required for tenant login tracking).

        Returns:
            UserResponse with the user's profile data.
        """
        # Track tenant portal login if this is a tenant user
        if session and user.user_type == UserType.TENANT:
            await AuthService._track_tenant_portal_login(user, session)

        return UserResponse.model_validate(user)

    @staticmethod
    async def _track_tenant_portal_login(user: User, session: AsyncSession) -> None:
        """
        Update tenant's portal login tracking fields.

        This is called when a tenant accesses /auth/me to track:
        - last_portal_login_at: timestamp of this access
        - portal_status: set to ACTIVE if not already

        Args:
            user: The tenant user accessing the portal.
            session: Database session for the update.
        """
        from Backend.models.tenant import Tenant
        from Backend.models.enums import PortalStatus

        try:
            # Find the tenant record linked to this user
            stmt = select(Tenant).where(col(Tenant.user_id) == user.id)
            result = await session.execute(stmt)
            tenant = result.scalar_one_or_none()

            if tenant:
                # Update portal tracking fields
                tenant.last_portal_login_at = datetime.now(timezone.utc)
                if tenant.portal_status != PortalStatus.ACTIVE:
                    tenant.portal_status = PortalStatus.ACTIVE
                    logger.info(
                        "Tenant %s portal_status updated to ACTIVE",
                        tenant.id
                    )
                session.add(tenant)
                await session.commit()
        except Exception as e:
            # Don't fail the /me request if tracking fails
            logger.warning(
                "Failed to track tenant portal login for user %s: %s",
                user.id, str(e)
            )
            await session.rollback()
    
    @staticmethod
    async def update_user_profile(
        user: User,
        profile_update: ProfileUpdateRequest,
        session: AsyncSession
    ) -> UserResponse:
        """
        Update user profile information.
        
        Args:
            user: The user to update.
            profile_update: The profile fields to update.
            session: Database session for persistence.
            
        Returns:
            Updated UserResponse.
        """
        # Update user profile fields
        for field, value in profile_update.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        
        touch_updated_at(user)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        return UserResponse.model_validate(user)
    
    @staticmethod
    async def upload_user_avatar(
        user: User,
        file: UploadFile,
        session: AsyncSession
    ) -> AvatarUploadResponse:
        """
        Upload and update user avatar.
        
        Args:
            user: The user whose avatar is being updated.
            file: The uploaded image file.
            session: Database session for persistence.
            
        Returns:
            AvatarUploadResponse with the new avatar URL.
            
        Raises:
            HTTPException: If upload fails.
        """
        try:
            # Upload to Azure Blob Storage
            profile_image_url = await upload_avatar_to_blob(file, user.id)
            
            # Update user profile
            user.profile_image_url = profile_image_url
            touch_updated_at(user)
            session.add(user)
            await session.commit()
            
            return AvatarUploadResponse(profile_image_url=profile_image_url)
        except Exception as e:
            logger.error("Error uploading avatar: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload avatar"
            )
    
    @staticmethod
    async def handle_webhook_user_sync(
        payload: SupabaseWebhookPayload,
        session: AsyncSession,
        client_ip: str = "unknown",
        processing_start_time: float | None = None
    ) -> dict:
        """
        Handle Supabase webhook for user synchronization.
        
        This webhook handles proactive user synchronization from Supabase auth.users
        to the local users table. It processes both INSERT and UPDATE events to ensure
        the local database stays in sync with Supabase authentication state.
        
        Key features:
        - OAuth account linking: If a user signs in with a different OAuth provider
          (e.g., Google then Microsoft) using the same email, this will link the accounts
          by updating the existing user's Supabase ID to the new one.
        - Idempotency: Safely handles duplicate webhook calls.
        - Metadata updates: Keeps user profile data in sync.
        - Audit logging: All webhook events are logged for monitoring and debugging.
        
        Args:
            payload: The webhook payload from Supabase.
            session: Database session for user operations.
            client_ip: Client IP address for audit logging.
            processing_start_time: Start time for performance tracking.
            
        Returns:
            Dictionary with operation result message.
            
        Raises:
            HTTPException: If user creation/update fails.
        """
        import time
        from Backend.models.webhook_audit_log import WebhookAuditLog
        
        # Track processing time
        start_time = processing_start_time or time.time()
        # Helper function to create audit log
        async def create_audit_log(
            success: bool,
            action_taken: str | None = None,
            error_message: str | None = None,
            error_type: str | None = None,
            record_id: str | None = None,
            record_email: str | None = None
        ):
            """Create webhook audit log entry (without committing)."""
            processing_time_ms = (time.time() - start_time) * 1000
            
            audit_log = WebhookAuditLog(
                webhook_type="user_sync",
                event_type=payload.type,
                source_ip=client_ip,
                table_name=f"{payload.schema_name}.{payload.table}",
                record_id=record_id,
                record_email=record_email,
                success=success,
                action_taken=action_taken,
                error_message=error_message,
                error_type=error_type,
                processing_time_ms=processing_time_ms
            )
            
            session.add(audit_log)
            # Session will be committed by parent function for atomicity
        
        # Only process INSERT/UPDATE events for auth.users table
        if payload.table != "users" or payload.schema_name != "auth":
            logger.debug("Ignoring webhook for table %s.%s", payload.schema_name, payload.table)
            await create_audit_log(
                success=True,
                action_taken="ignored_table"
            )
            await session.commit()
            return {"message": "Event ignored - not auth.users table"}
        
        if payload.type not in ["INSERT", "UPDATE"]:
            logger.debug("Ignoring %s event for auth.users", payload.type)
            await create_audit_log(
                success=True,
                action_taken="ignored_event_type"
            )
            await session.commit()
            return {"message": f"Event ignored - {payload.type} not supported"}
        
        if not payload.record:
            logger.warning("Webhook received with no record data")
            await create_audit_log(
                success=False,
                action_taken="error",
                error_type="missing_record_data",
                error_message="No record data in webhook payload"
            )
            await session.commit()
            return {"message": "No record data"}
        
        # Extract user data from webhook payload
        user_id = payload.record.get("id")
        email = payload.record.get("email")
        raw_user_meta_data = payload.record.get("raw_user_meta_data", {})
        
        # Handle case where raw_user_meta_data might be a JSON string
        if isinstance(raw_user_meta_data, str):
            try:
                raw_user_meta_data = json.loads(raw_user_meta_data)
            except json.JSONDecodeError:
                logger.warning("Failed to parse raw_user_meta_data as JSON, using empty dict")
                raw_user_meta_data = {}
        
        if not user_id or not email:
            logger.error("Missing user_id or email in webhook payload")
            await create_audit_log(
                success=False,
                action_taken="error",
                error_type="missing_required_fields",
                error_message="Missing user_id or email"
            )
            await session.commit()
            return {"message": "Invalid user data - missing required fields"}
        
        # Convert user_id string to UUID
        try:
            uuid_obj = PythonUUID(user_id)
        except ValueError:
            logger.error("Invalid UUID format for user_id: %s", user_id)
            await create_audit_log(
                success=False,
                action_taken="error",
                error_type="invalid_uuid_format",
                error_message=f"Invalid UUID: {user_id}",
                record_id=str(user_id),
                record_email=email
            )
            return {"message": "Invalid user ID format"}
        
        logger.info(
            "[Webhook] Processing %s event for user %s (email: %s)",
            payload.type,
            uuid_obj,
            email
        )
        
        # Check if user already exists by Supabase ID
        existing_user = await session.get(User, uuid_obj)
        
        if existing_user:
            # User exists with this Supabase ID - idempotent operation
            if payload.type == "INSERT":
                logger.info(
                    "[Webhook] User %s already exists in local DB (idempotent INSERT)",
                    uuid_obj
                )
                await create_audit_log(
                    success=True,
                    action_taken="idempotent",
                    record_id=str(uuid_obj),
                    record_email=email
                )
                await session.commit()
                return {"message": "User already exists - idempotent"}
            
            # UPDATE event - update user metadata
            logger.info("[Webhook] Updating existing user %s metadata", uuid_obj)
            metadata = extract_user_metadata_from_supabase(raw_user_meta_data)
            
            # Update fields if they changed
            if metadata.get("first_name") and existing_user.first_name != metadata["first_name"]:
                existing_user.first_name = metadata["first_name"]
            if metadata.get("last_name") and existing_user.last_name != metadata["last_name"]:
                existing_user.last_name = metadata["last_name"]
            if metadata.get("phone") and existing_user.phone != metadata["phone"]:
                existing_user.phone = metadata["phone"]
            if existing_user.is_email_verified != metadata.get("is_email_verified", False):
                existing_user.is_email_verified = metadata["is_email_verified"]
            
            existing_user.updated_at = datetime.now(timezone.utc)
            
            await create_audit_log(
                success=True,
                action_taken="updated",
                record_id=str(uuid_obj),
                record_email=email
            )
            await session.commit()
            return {"message": "User metadata updated successfully"}
        
        # User doesn't exist with this Supabase ID - check for email conflict (OAuth linking)
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user_with_same_email = result.scalar_one_or_none()
        
        if user_with_same_email:
            # Email conflict detected - this should NOT happen with enable_manual_linking=true
            # Supabase should prompt user to link accounts and maintain same user_id
            logger.error(
                "[Webhook] UNEXPECTED: User with email %s exists with different Supabase ID. "
                "Old ID: %s, New ID: %s. This indicates Supabase account linking failed or was declined.",
                email,
                user_with_same_email.id,
                uuid_obj
            )
            
            # Capture in Sentry for monitoring
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "webhook")
                scope.set_tag("error_type", "duplicate_email_different_id")
                scope.set_context("email_conflict", {
                    "email": email,
                    "existing_user_id": str(user_with_same_email.id),
                    "new_supabase_id": str(uuid_obj),
                    "action": "rejected"
                })
                sentry_sdk.capture_message(
                    "Webhook detected email conflict - Supabase account linking may have failed",
                    level="warning"
                )
            
            await create_audit_log(
                success=False,
                action_taken="error",
                error_type="email_conflict",
                error_message=f"Email {email} already exists with different Supabase ID",
                record_id=str(uuid_obj),
                record_email=email
            )
            await session.commit()
            
            # Return error - user should use existing account or contact support
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "An account with this email already exists. "
                    "Please sign in with your existing authentication method or contact support."
                )
            )
        
        # No existing user found - create new user
        logger.info("[Webhook] Creating new user %s in local DB", uuid_obj)
        
        # Extract metadata
        metadata = extract_user_metadata_from_supabase(raw_user_meta_data)
        
        # Use the helper method to create user
        try:
            await AuthService.create_user_from_supabase(
                user_id, email, metadata, session
            )
            logger.info("[Webhook] Successfully created user %s", uuid_obj)
            
            await create_audit_log(
                success=True,
                action_taken="created",
                record_id=str(uuid_obj),
                record_email=email
            )
            await session.commit()
            return {"message": "User created successfully"}
        except HTTPException:
            await create_audit_log(
                success=False,
                action_taken="error",
                error_type="http_exception",
                error_message="Failed to create user - HTTP exception",
                record_id=str(uuid_obj),
                record_email=email
            )
            await session.commit()
            raise
        except Exception as e:
            logger.exception("[Webhook] Error creating user %s", uuid_obj)
            await create_audit_log(
                success=False,
                action_taken="error",
                error_type=type(e).__name__,
                error_message=str(e),
                record_id=str(uuid_obj),
                record_email=email
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            ) from e
    
    @staticmethod
    async def sync_user_from_supabase(
        sync_request: UserSyncRequest,
        session: AsyncSession
    ) -> UserResponse:
        """
        Manually sync a user from Supabase to local database.
        
        Args:
            sync_request: The user data to sync.
            session: Database session for user operations.
            
        Returns:
            UserResponse for the synced user.
            
        Raises:
            HTTPException: If sync fails.
        """
        # Convert user_id string to UUID
        try:
            uuid_obj = PythonUUID(sync_request.supabase_user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format"
            )
        
        # Check if user already exists
        existing_user = await session.get(User, uuid_obj)
        
        if existing_user:
            # User exists, return existing user
            logger.info("User with Supabase ID %s already exists. Returning existing user.",
                        sync_request.supabase_user_id)
            return UserResponse.model_validate(existing_user)
        
        # User does not exist, create a new one
        logger.info("User with Supabase ID %s not found. Creating new user.",
                    sync_request.supabase_user_id)
        
        # Prepare metadata
        metadata = {
            "first_name": sync_request.first_name,
            "last_name": sync_request.last_name,
            "phone": sync_request.phone,
            "is_email_verified": False
        }
        
        # Use the new helper method to create user
        try:
            db_user = await AuthService.create_user_from_supabase(
                sync_request.supabase_user_id,
                sync_request.email,
                metadata,
                session
            )
            return UserResponse.model_validate(db_user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Error creating user during sync: %s", str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user in local database: {str(e)}"
            )
    
    # === Future service methods (to be implemented) ===
    
    @staticmethod
    async def verify_user_password(email: str, password: str) -> bool:
        """
        Verify a user's password without creating a new session.
        
        Uses Supabase's signInWithPassword but immediately signs out to avoid
        creating a persistent session. This is used for password verification
        before sensitive operations like password changes.
        
        Args:
            email: The user's email address.
            password: The password to verify.
            
        Returns:
            True if password is correct, False otherwise.
            
        Note:
            We use email instead of user_id because Supabase auth requires email
            for authentication. The user_id is not sufficient for password verification.
        """
        try:
            supabase = get_supabase_client()
            
            # Attempt to sign in with the provided credentials
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            # If we get here, the password was correct
            # Immediately sign out to avoid keeping the session
            if response.session:
                supabase.auth.sign_out()
            
            logger.info(f"Password verified successfully for user {email}")
            return True
            
        except (AuthApiError, AuthError, AuthInvalidCredentialsError) as auth_error:
            # Expected authentication failure - password is incorrect  
            logger.info(f"Password verification failed for user {email}: {str(auth_error)}")
            return False
        except Exception as e:
            # Log unexpected errors but still return False
            logger.error(f"Unexpected error during password verification for {email}: {str(e)}")
            
            # Report unexpected errors to Sentry for investigation
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "authentication")
                scope.set_tag("function", "verify_user_password")
                scope.set_context("auth_context", {
                    "email": email,
                    "exception_type": type(e).__name__
                })
                sentry_sdk.capture_exception(e)
            
            return False
    
    @staticmethod
    async def change_user_password(
        email: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password after verification.
        
        This method first verifies the current password, then updates to the new password
        using Supabase's auth system. A temporary session is created for the password
        update and then immediately terminated.
        
        Args:
            email: The user's email address.
            current_password: The current password for verification.
            new_password: The new password to set.
            
        Returns:
            True if password changed successfully, False otherwise.
            
        Raises:
            HTTPException: If password change fails due to validation or other errors.
        """
        try:
            # First verify the current password
            is_valid = await AuthService.verify_user_password(email, current_password)
            if not is_valid:
                logger.warning(f"Password change failed for {email}: incorrect current password")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )
            
            supabase = get_supabase_client()
            
            # Sign in to get a session for password update
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": current_password
            })
            
            if not auth_response.session:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to establish session for password update"
                )
            
            # Update the password
            update_response = supabase.auth.update_user({
                "password": new_password
            })
            
            # Sign out to terminate the session
            supabase.auth.sign_out()
            
            logger.info(f"Password changed successfully for user {email}")
            return True
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except (AuthApiError, AuthWeakPasswordError, AuthError) as auth_error:
            # Handle specific Supabase authentication errors
            error_msg = str(auth_error).lower()
            
            # Check for weak password error (or direct AuthWeakPasswordError)
            if isinstance(auth_error, AuthWeakPasswordError) or ("password" in error_msg and "weak" in error_msg):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password does not meet security requirements. Please choose a stronger password."
                )
            
            # Log and report the auth error for analysis
            logger.warning(f"Password change failed for {email}: {auth_error}")
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "authentication")
                scope.set_tag("function", "change_user_password")
                scope.set_context("auth_context", {
                    "email": email,
                    "error_message": str(auth_error)
                })
                sentry_sdk.capture_exception(auth_error)
            
            # Generic Supabase auth error
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Password change failed: {str(auth_error)}"
            )
        except Exception as e:
            # Log unexpected errors and report to Sentry
            logger.error(f"Unexpected error during password change for {email}: {str(e)}")
            
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "authentication")
                scope.set_tag("function", "change_user_password")
                scope.set_context("auth_context", {
                    "email": email,
                    "exception_type": type(e).__name__
                })
                sentry_sdk.capture_exception(e)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during password change"
            )
    
    @staticmethod
    async def resend_verification_email(email: str) -> dict:
        """
        Resend email verification to user.
        
        This method works with Supabase's auth system to resend the confirmation email.
        Note: Supabase has rate limiting on email sending to prevent abuse.
        
        Args:
            email: The email address to resend verification to.
            
        Returns:
            Dictionary with success status and message.
            
        Raises:
            HTTPException: If the operation fails.
        """
        try:
            supabase = get_supabase_client()
            
            supabase.auth.resend(
                {
                    "type": "signup",
                    "email": email
                }
            )
            
            logger.info(f"Successfully requested verification email resend for {email}")
            return {
                "success": True,
                "message": "If an account exists with this email, a verification email has been sent."
            }
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except (AuthApiError, AuthError) as auth_error:
            # Handle Supabase authentication errors
            logger.warning(f"Failed to resend verification email to {email}: {auth_error}")
            
            status_code = getattr(auth_error, 'status', 500)
            message = str(auth_error)

            # Report auth error to Sentry for monitoring
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "authentication")
                scope.set_tag("function", "resend_verification_email")
                scope.set_context("auth_context", {
                    "email": email,
                    "status_code": status_code,
                    "error_message": message
                })
                sentry_sdk.capture_exception(auth_error)

            if status_code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait before trying again."
                )
            elif "user not found" in message.lower():
                logger.info(f"Resend verification requested for non-existent email, returning generic message.")
                return {
                    "success": True,
                    "message": "If an account exists with this email, a verification email has been sent."
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to resend verification email: {message}"
                )
        except Exception as e:
            # Handle other unexpected exceptions
            logger.error(f"Unexpected error resending verification email for {email}: {str(e)}")
            
            # Report unexpected errors to Sentry for investigation
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("component", "authentication")
                scope.set_tag("function", "resend_verification_email")
                scope.set_context("auth_context", {
                    "email": email,
                    "exception_type": type(e).__name__
                })
                sentry_sdk.capture_exception(e)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please try again later."
            )
    
    @staticmethod
    async def request_email_verification(user_id: PythonUUID, session: AsyncSession) -> bool:
        """
        Request email verification for a specific user.
        
        This is different from resend_verification_email in that it's called by
        authenticated users to request verification, whereas resend_verification_email
        is called during registration by unauthenticated users.
        
        Args:
            user_id: The user's ID who is requesting verification.
            session: Database session to fetch user details.
            
        Returns:
            True if verification email was sent successfully.
            
        Raises:
            HTTPException: If user not found or email sending fails.
        """
        # Get user from database
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_email_verified:
            logger.info(f"User {user_id} already has verified email")
            return True
        
        # Use the existing resend method
        result = await AuthService.resend_verification_email(user.email)
        return result.get("success", False)
    
    @staticmethod
    async def verify_email_token(token: str) -> bool:
        """
        Verify an email verification token.
        
        Note: In the current architecture, Supabase handles email verification
        directly through their hosted confirmation URLs. This method is a placeholder
        for potential future implementation where we might need to handle
        verification tokens directly.
        
        Args:
            token: The verification token from the email link.
            
        Returns:
            True if token is valid and email was verified.
            
        Raises:
            HTTPException: If token is invalid or verification fails.
        """
        # Currently, Supabase handles email verification through their hosted pages
        # This method would be implemented if we need custom verification handling
        logger.warning("verify_email_token called but Supabase handles verification directly")
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Email verification is handled by Supabase authentication service"
        )