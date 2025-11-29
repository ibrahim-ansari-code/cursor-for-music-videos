"""
Tenant Invitations API Schemas

Request and response schemas for tenant portal invitations.
"""
from datetime import datetime
from uuid import UUID as PythonUUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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


# === Tenant Info Schema (for public endpoint) ===

class TenantPublicInfo(BaseModel):
    """Public tenant info returned during invitation flow."""
    first_name: str | None = None
    email: str
    property_name: str | None = None
    unit_name: str | None = None

