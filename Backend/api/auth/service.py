"""
Authentication service layer.

This module contains the business logic for authentication operations,
separated from the API route handlers for better organization and testing.
"""

import json
import logging
from uuid import UUID as PythonUUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

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
        
        # Check if user already exists
        existing_user = await session.get(User, uuid_obj)
        if existing_user:
            logger.info("User %s already exists in local DB", uuid_obj)
            return existing_user
        
        # Create new user data
        new_user_data = {
            "id": uuid_obj,
            "email": email,
            "first_name": metadata.get("first_name"),
            "last_name": metadata.get("last_name"),
            "phone": metadata.get("phone"),
            "user_type": UserType.LANDLORD,  # Default for this portal
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
            await session.commit()
            await session.refresh(db_user)
            logger.info("Successfully created user %s from Supabase data", uuid_obj)
            return db_user
        except Exception as e:
            await session.rollback()
            logger.error("Error creating user %s: %s", uuid_obj, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )
    
    @staticmethod
    async def get_user_profile(user: User) -> UserResponse:
        """
        Get user profile information.
        
        Args:
            user: The user instance to return.
            
        Returns:
            UserResponse with the user's profile data.
        """
        return UserResponse.model_validate(user)
    
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
        session: AsyncSession
    ) -> dict:
        """
        Handle Supabase webhook for user synchronization.
        
        Args:
            payload: The webhook payload from Supabase.
            session: Database session for user creation.
            
        Returns:
            Dictionary with operation result message.
        """
        # Only process INSERT events for auth.users table
        if payload.type != "INSERT" or payload.table != "users" or payload.schema_name != "auth":
            return {"message": "Event ignored"}
        
        if not payload.record:
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
            return {"message": "Invalid user data"}
        
        # Convert user_id string to UUID
        try:
            uuid_obj = PythonUUID(user_id)
        except ValueError:
            logger.error(f"Invalid UUID format for user_id: {user_id}")
            return {"message": "Invalid user ID format"}
        
        # Check if user already exists
        existing_user = await session.get(User, uuid_obj)
        if existing_user:
            logger.info("User %s already exists in local DB", uuid_obj)
            return {"message": "User already exists"}
        
        # Extract metadata
        metadata = extract_user_metadata_from_supabase(raw_user_meta_data)
        
        # Use the new helper method to create user
        try:
            await AuthService.create_user_from_supabase(
                user_id, email, metadata, session
            )
            return {"message": "User created successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error creating user %s from webhook", uuid_obj)
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
            
        except Exception as e:
            # Check for authentication errors by examining the exception class name
            if hasattr(e, '__class__') and e.__class__.__name__ == 'GoTrueApiError':
                logger.info(f"Password verification failed for user {email}: {str(e)}")
                return False
            
            # Log unexpected errors but still return False
            logger.error(f"Unexpected error during password verification for {email}: {str(e)}")
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
        except Exception as e:
            # Check for specific Supabase errors
            if hasattr(e, '__class__') and e.__class__.__name__ == 'GoTrueApiError':
                error_msg = str(e)
                
                # Check for weak password error
                if "password" in error_msg.lower() and "weak" in error_msg.lower():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="New password does not meet security requirements"
                    )
                
                logger.error(f"Supabase error during password change for {email}: {error_msg}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Password change failed: {error_msg}"
                )
            
            # Log unexpected errors
            logger.error(f"Unexpected error during password change for {email}: {str(e)}")
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
        except Exception as e:
            # Re-raise if it's an HTTPException that we've already processed
            if isinstance(e, HTTPException):
                raise

            # Workaround for potential linter issue with GoTrueApiError import
            if e.__class__.__name__ == 'GoTrueApiError':
                logger.warning(f"Failed to resend verification email to {email}: {e}")
                
                status_code = getattr(e, 'status', 500)
                message = getattr(e, 'message', str(e))

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
            
            # Handle other unexpected exceptions
            logger.error(f"Unexpected error resending verification email for {email}: {str(e)}")
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