import logging
from datetime import datetime
from typing import Optional
from enum import Enum
import traceback

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, func
from pydantic import validator

from Backend.config import settings
from Backend.database import get_session
from Backend.models.user import User, UserType
from Backend.utils.azure_blob import upload_avatar_to_blob
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

# === Models ===
class UserResponse(BaseModel):
    id: str  # UUID from Supabase
    email: str
    first_name: str
    last_name: str
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

    @validator('user_type', pre=True)
    def convert_user_type_to_upper(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

class AvatarUploadResponse(BaseModel):
    profile_image_url: str

# === Pydantic Models for sync-user ===
class UserSyncRequest(BaseModel):
    supabase_user_id: str # This will be the UUID from Supabase
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    user_type: Optional[str] = None # Assuming UserType enum strings like "LANDLORD"

class UserSyncResponse(UserResponse): # Reuse existing UserResponse
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
        user_response_from_supabase = supabase.auth.get_user(credentials.credentials)

        if not user_response_from_supabase or not hasattr(user_response_from_supabase, 'user') or not user_response_from_supabase.user:
            logger.warning("Supabase auth.get_user did not return a user or in expected format.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials (user data not returned by Supabase in expected format)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        actual_user_from_supabase = user_response_from_supabase.user

        if not hasattr(actual_user_from_supabase, 'id') or actual_user_from_supabase.id is None:
            logger.error(f"Supabase user object (nested) is missing ID. Repr: {repr(actual_user_from_supabase)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase user object (nested) is missing ID.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        local_user_id_str = str(actual_user_from_supabase.id)
        result = await session.execute(select(User).where(User.id == local_user_id_str))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            logger.warning(f"User with Supabase ID {local_user_id_str} not found in local database.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User authenticated with Supabase but not found in local application database.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return db_user
    except HTTPException as http_exc: # Re-raise HTTPException to preserve status code and details
        raise http_exc
    except Exception as e:
        logger.error(f"Authentication error in get_current_user. Exception type: {type(e)}, Exception: {repr(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Log the state of user_response_from_supabase if it was assigned
        if 'user_response_from_supabase' in locals() and user_response_from_supabase is not None:
            logger.error(f"State of user_response_from_supabase when error occurred: type={type(user_response_from_supabase)}, repr={repr(user_response_from_supabase)}, attributes: {dir(user_response_from_supabase)}")
        else:
            logger.error("user_response_from_supabase was not successfully assigned or was None prior to the error.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Changed from 401 to 500 for unexpected errors
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
    user_id: str,
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
    for field, value in profile_update.dict(exclude_unset=True).items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    
    return current_user

@router.post("/users/{user_id}/avatar", response_model=AvatarUploadResponse)
async def upload_user_avatar(
    user_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Upload user avatar"""
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's avatar"
        )

    try:
        # Upload to Azure Blob Storage
        profile_image_url = await upload_avatar_to_blob(file, f"avatars/{user_id}")
        
        # Update user profile
        current_user.profile_image_url = profile_image_url
        current_user.updated_at = datetime.utcnow()
        session.add(current_user)
        await session.commit()
        
        return AvatarUploadResponse(profile_image_url=profile_image_url)
    except Exception as e:
        logger.error(f"Error uploading avatar: {str(e)}")
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
        logger.info(f"User with Supabase ID {sync_request.supabase_user_id} already exists. Returning existing user.")
        return existing_user

    # User does not exist, create a new one
    logger.info(f"User with Supabase ID {sync_request.supabase_user_id} not found. Creating new user.")
    
    new_user_data = {
        "id": sync_request.supabase_user_id, # Explicitly set our ID to Supabase's User ID
        "email": sync_request.email,
        "first_name": sync_request.first_name,
        "last_name": sync_request.last_name,
        "phone": sync_request.phone,
        "user_type": sync_request.user_type.upper() if sync_request.user_type else "UNKNOWN", # Ensure uppercase or a default
        # Default values based on observed schema and common practice:
        "is_active": True,
        "is_admin": False, # New users from Supabase signup are not admins by default
        "is_email_verified": False, # Email verification is handled by Supabase, this reflects initial state
        "created_at": datetime.utcnow(), # Handled by SQLModel default_factory if not set
        "updated_at": datetime.utcnow(), # Handled by SQLModel default_factory if not set
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
        logger.info(f"Successfully created and synced user {db_user.id} from Supabase.")
        return db_user
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating user during sync: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user in local database: {str(e)}"
        )

# Ensure UserType enum/string consistency.
# The User model has `user_type: str`. The validator in UserResponse converts to upper.
# It's good practice for `sync_request.user_type` to also be handled consistently.
# The `user_type` in `new_user_data` is set to `sync_request.user_type.upper()`.
