import logging
import traceback
from datetime import datetime
from typing import Optional, Protocol
from uuid import UUID as PythonUUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import col

from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.utils.azure_blob import upload_avatar_to_blob
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.utils.supabase import get_supabase_client

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

# Set up security scheme
security = HTTPBearer()

# === Type Protocols ===


class HasUpdatedAt(Protocol):
    """Protocol for objects that have an updated_at attribute."""
    updated_at: datetime

# === Helper Functions ===


def touch_updated_at(obj: HasUpdatedAt) -> None:
    """
    Helper function to set the updated_at field to the current UTC time.

    Args:
        obj: Any object with an updated_at attribute to be updated.
    """
    # Use our datetime utility for consistent audit timestamp handling
    obj.updated_at = create_audit_datetime()

# === Models ===


class UserResponse(BaseModel):
    id: PythonUUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    user_type: UserType
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_admin: bool

    class Config:
        from_attributes = True

    @field_validator('user_type', mode='before')
    def convert_user_type_to_upper(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class AvatarUploadResponse(BaseModel):
    profile_image_url: str

# === Pydantic Models for sync-user ===


class UserSyncRequest(BaseModel):
    supabase_user_id: str  # This will be the UUID from Supabase
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    # Assuming UserType enum strings like "LANDLORD"
    user_type: str | None = None


class UserSyncResponse(UserResponse):  # Reuse existing UserResponse
    pass

# === Authentication ===


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    """Get current user from Supabase JWT token"""
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
                "User with Supabase ID %s not found in local database.", actual_user_from_supabase.id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User authenticated with Supabase but not found in local application database.",
                headers={"WWW-Authenticate": "Bearer"},
            )
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

# === API Routes ===


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/users/{user_id}/profile", response_model=UserResponse)
async def update_user_profile(
    user_id: PythonUUID,
    profile_update: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update user profile"""
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's profile"
        )

    # Update user profile
    for field, value in profile_update.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)

    touch_updated_at(current_user)
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)

    return current_user


@router.post("/users/{user_id}/avatar", response_model=AvatarUploadResponse)
async def upload_user_avatar(
    user_id: PythonUUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Uploads a new avatar image for the specified user.

    Only the user themselves or an admin can upload an avatar. 
    The image is stored in Azure Blob Storage, and the user's profile 
    is updated with the new avatar URL.

    Args:
        user_id: The ID of the user whose avatar is being updated.
        file: The image file to upload.

    Returns:
        An object containing the URL of the uploaded avatar image.
    """
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's avatar"
        )

    try:
        # Upload to Azure Blob Storage
        profile_image_url = await upload_avatar_to_blob(file, current_user.id)

        # Update user profile
        current_user.profile_image_url = profile_image_url
        touch_updated_at(current_user)
        session.add(current_user)
        await session.commit()

        return AvatarUploadResponse(profile_image_url=profile_image_url)
    except Exception as e:
        logger.error("Error uploading avatar: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload avatar"
        )


@router.post("/sync-user", response_model=UserSyncResponse, status_code=status.HTTP_200_OK)
async def sync_supabase_user(
    sync_request: UserSyncRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Synchronize a Supabase user to the local database.
    If the user exists, it returns the existing user.
    If not, it creates a new user record.
    """
    # Check if user already exists by Supabase ID (which is our User.id)
    existing_user = await session.get(User, sync_request.supabase_user_id)

    if existing_user:
        # If user exists, update fields if necessary or just return
        # For now, just return the existing user as per requirements.
        # Future enhancement: update fields if they differ from sync_request.
        logger.info("User with Supabase ID %s already exists. Returning existing user.",
                    sync_request.supabase_user_id)
        return existing_user

    # User does not exist, create a new one
    logger.info("User with Supabase ID %s not found. Creating new user.",
                sync_request.supabase_user_id)

    new_user_data = {
        # Explicitly set our ID to Supabase's User ID
        "id": sync_request.supabase_user_id,
        "email": sync_request.email,
        "first_name": sync_request.first_name,
        "last_name": sync_request.last_name,
        "phone": sync_request.phone,
        # Ensure uppercase or a default
        "user_type": sync_request.user_type.upper() if sync_request.user_type else "UNKNOWN",
        # Default values based on observed schema and common practice:
        "is_active": True,
        "is_admin": False,  # New users from Supabase signup are not admins by default
        # Email verification is handled by Supabase, this reflects initial state
        "is_email_verified": False,
        # Store timestamps as naive datetime using our utility
        "created_at": create_audit_datetime(),
        "updated_at": create_audit_datetime(),
    }

    # Ensure all fields in User model are accounted for, even if Optional
    # and not in sync_request, to avoid issues if they are not nullable in DB
    # or if SQLModel doesn't set a default for them when None.
    # Address fields:
    new_user_data["address"] = None
    new_user_data["city"] = None
    new_user_data["province"] = None
    new_user_data["postal_code"] = None
    new_user_data["profile_image_url"] = None

    try:
        db_user = User.model_validate(new_user_data)
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        logger.info(
            "Successfully created and synced user %s from Supabase.", db_user.id)
        return db_user
    except Exception as e:
        await session.rollback()
        logger.error("Error creating user during sync: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user in local database: {str(e)}"
        )

# Ensure UserType enum/string consistency.
# The User model has `user_type: str`. The validator in UserResponse converts to upper.
# It's good practice for `sync_request.user_type` to also be handled consistently.
# The `user_type` in `new_user_data` is set to `sync_request.user_type.upper()`.
