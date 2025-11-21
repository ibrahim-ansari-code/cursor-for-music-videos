"""
Authentication module for Brikli API.

This module provides authentication and authorization functionality including:
- User authentication via JWT tokens
- User profile management
- Password operations
- Webhook handling for user synchronization
"""

from .dependencies import (
    get_current_user,
    get_current_user_no_subscription_check,
    get_user_id,
    get_current_active_user,
    get_current_admin_user,
    get_current_verified_user
)
from .router import router
from .schemas import (
    UserResponse,
    ProfileUpdateRequest,
    AvatarUploadResponse,
    UserSyncRequest,
    UserSyncResponse,
    SupabaseWebhookPayload,
    PasswordVerificationRequest,
    PasswordChangeRequest,
    EmailVerificationRequest
)
from .service import AuthService

__all__ = [
    # Router
    "router",
    
    # Dependencies (for use in other modules)
    "get_current_user",
    "get_current_user_no_subscription_check",
    "get_user_id",
    "get_current_active_user", 
    "get_current_admin_user",
    "get_current_verified_user",
    
    # Service
    "AuthService",
    
    # Schemas
    "UserResponse",
    "ProfileUpdateRequest",
    "AvatarUploadResponse",
    "UserSyncRequest",
    "UserSyncResponse",
    "SupabaseWebhookPayload",
    "PasswordVerificationRequest",
    "PasswordChangeRequest",
    "EmailVerificationRequest"
]