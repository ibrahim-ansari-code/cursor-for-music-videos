import logging
from datetime import datetime
from typing import Optional
from enum import Enum

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

# === Authentication ===
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session)
):
    """Get current user from Supabase JWT token"""
    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Verify the JWT token with Supabase
        user = supabase.auth.get_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from our database
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in database",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return db_user
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
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
