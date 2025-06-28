"""
Authentication schemas for request/response validation.

This module contains all Pydantic models used for authentication-related
API endpoints, including user management, profile updates, and webhooks.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID as PythonUUID

from pydantic import BaseModel, EmailStr, field_validator, Field, ConfigDict, ValidationInfo

from Backend.models.enums import UserType


# === Response Models ===

class UserResponse(BaseModel):
    """
    User response model for API endpoints.
    
    This is the standard response format for user data across all endpoints.
    Includes all user fields that are safe to expose via API.
    """
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
    is_email_verified: bool

    model_config = ConfigDict(from_attributes=True)

    @field_validator('user_type', mode='before')
    def convert_user_type_to_upper(cls, v):
        """Ensure user_type is always uppercase for consistency."""
        if isinstance(v, str):
            return v.upper()
        return v


class AvatarUploadResponse(BaseModel):
    """Response model for avatar upload endpoint."""
    profile_image_url: str


# === Request Models ===

class ProfileUpdateRequest(BaseModel):
    """
    Request model for updating user profile.
    
    All fields are optional to allow partial updates.
    """
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    
    model_config = ConfigDict(extra='forbid')


class UserSyncRequest(BaseModel):
    """
    Request model for manual user synchronization.
    
    Used by the sync-user endpoint to create/update users from Supabase data.
    """
    supabase_user_id: str  # This will be the UUID from Supabase
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    user_type: UserType = UserType.LANDLORD  # Default to LANDLORD, use enum directly
    
    @field_validator('user_type', mode='before')
    def convert_user_type_string(cls, v):
        """Convert string to UserType enum if necessary."""
        if isinstance(v, str):
            try:
                return UserType(v.upper())
            except ValueError:
                raise ValueError(f"Invalid user type: {v}. Must be one of {[ut.value for ut in UserType]}")
        return v


# === Webhook Models ===

class SupabaseWebhookPayload(BaseModel):
    """
    Supabase webhook payload structure.
    
    This model represents the webhook payload sent by Supabase when
    user-related events occur (INSERT, UPDATE, DELETE).
    """
    type: str  # INSERT, UPDATE, DELETE
    table: str  # table name
    schema_name: str = Field(alias="schema")  # usually 'auth' for auth.users
    record: dict | None = None  # The new record (for INSERT/UPDATE)
    old_record: dict | None = None  # The old record (for UPDATE/DELETE)


# === Alias for backward compatibility ===
UserSyncResponse = UserResponse  # Reuse existing UserResponse


# === Future Request Models (for new endpoints) ===

class PasswordVerificationRequest(BaseModel):
    """Request model for password verification endpoint."""
    password: str


class PasswordChangeRequest(BaseModel):
    """Request model for password change endpoint."""
    current_password: str
    new_password: str

    @field_validator('new_password')
    def validate_password_strength(cls, v, info: ValidationInfo):
        """
        Validate password meets minimum security requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one number
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        
        # Ensure new password is different from current
        if info.data and 'current_password' in info.data and v == info.data['current_password']:
            raise ValueError("New password must be different from current password")
        
        return v


class EmailVerificationRequest(BaseModel):
    """Request model for email verification resend."""
    email: EmailStr  # Required - endpoint doesn't require authentication