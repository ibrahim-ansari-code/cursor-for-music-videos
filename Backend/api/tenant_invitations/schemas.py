"""
Tenant Invitations API Schemas

Request and response schemas for tenant portal invitations.
"""
import re
from datetime import datetime
from uuid import UUID as PythonUUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from Backend.models.tenant_portal_invitation import InvitationStatus


# === Invitation Request/Response Schemas ===

class InvitationCreateRequest(BaseModel):
    """Request to create a new tenant portal invitation."""
    tenant_id: int = Field(..., description="ID of the tenant to invite")


class InvitationResponse(BaseModel):
    """Response for a tenant portal invitation."""
    id: PythonUUID
    tenant_id: int
    invited_by: PythonUUID
    email: str
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    
    # Nested tenant info
    tenant_name: str | None = None
    tenant_email: str | None = None
    
    model_config = ConfigDict(from_attributes=True)


class InvitationListResponse(BaseModel):
    """Response for listing invitations."""
    invitations: list[InvitationResponse]
    total: int


class InvitationRevokeResponse(BaseModel):
    """Response after revoking an invitation."""
    success: bool
    message: str


class InvitationResendResponse(BaseModel):
    """Response after resending an invitation."""
    success: bool
    message: str
    new_expires_at: datetime | None = None


# === Token Validation Schemas ===

class InvitationValidateRequest(BaseModel):
    """Request to validate an invitation token."""
    token: str = Field(..., min_length=40, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class InvitationValidateResponse(BaseModel):
    """Response for invitation token validation."""
    valid: bool
    email: str | None = None
    tenant_name: str | None = None
    landlord_name: str | None = None
    property_name: str | None = None
    unit_name: str | None = None
    expires_at: datetime | None = None
    message: str | None = None


# === Accept Invitation Schemas ===

class InvitationAcceptRequest(BaseModel):
    """Request to accept an invitation and link to user account."""
    token: str = Field(..., min_length=40, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    # User ID is extracted from the authenticated user's JWT


class InvitationAcceptResponse(BaseModel):
    """Response after accepting an invitation."""
    success: bool
    message: str
    tenant_id: int | None = None


# === Register and Accept Schemas (Streamlined Flow) ===

class RegisterAndAcceptRequest(BaseModel):
    """
    Request to register a new user and accept invitation in one step.

    This streamlined flow skips email verification because clicking
    the invitation link already proves email ownership (industry standard
    pattern used by Slack, Notion, Discourse, etc.).
    """
    token: str = Field(
        ...,
        min_length=40,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Invitation token from the email link"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's chosen password (min 8 characters, must include uppercase, lowercase, number, and special character)"
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's first name"
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User's last name"
    )

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """
        Validate password meets security requirements.

        Requirements (matching frontend validation):
        - At least 8 characters (enforced by min_length)
        - At least one lowercase letter
        - At least one uppercase letter
        - At least one digit
        - At least one special character
        """
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?~`]', v):
            raise ValueError('Password must contain at least one special character (!@#$%^&*()_+-=[]{};\':"|,.<>/?~`)')
        return v


class RegisterAndAcceptResponse(BaseModel):
    """Response after successful registration and invitation acceptance."""
    success: bool
    message: str
    tenant_id: int | None = None
    user_id: str | None = None
    # Supabase session for auto-sign-in
    access_token: str | None = None
    refresh_token: str | None = None


# === Tenant Info Schema (for public endpoint) ===

class TenantPublicInfo(BaseModel):
    """Public tenant info returned during invitation flow."""
    first_name: str | None = None
    email: str
    property_name: str | None = None
    unit_name: str | None = None

