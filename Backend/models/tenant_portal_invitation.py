"""
Tenant Portal Invitation Model

Tracks invitations sent by landlords to tenants for portal access.
Links tenant records to user accounts upon acceptance.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from Backend.utils.datetime_utils import create_audit_datetime


def hash_token(token: str) -> str:
    """Hash a token using SHA-256 for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()

if TYPE_CHECKING:
    from Backend.models.tenant import Tenant
    from Backend.models.user import User


class InvitationStatus(str, Enum):
    """Status of a tenant portal invitation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


def get_default_expiry() -> datetime:
    """Get default expiry datetime (7 days from now, timezone-aware UTC)."""
    return datetime.now(timezone.utc) + timedelta(days=7)


class TenantPortalInvitation(SQLModel, table=True):
    """
    Tenant Portal Invitation Model.
    
    Tracks invitations sent by landlords to tenants for portal access.
    When a tenant accepts an invitation, their user account is linked
    to the tenant record via tenants.user_id.
    """
    __tablename__ = "tenant_portal_invitations"

    id: PythonUUID = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default="gen_random_uuid()",
        ),
    )
    
    # Links to tenant and inviting landlord
    tenant_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    invited_by: PythonUUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    
    # Invitation details
    invitation_token: str = Field(
        sa_column=Column(Text, nullable=False, unique=True, index=True),
    )
    email: str = Field(
        sa_column=Column(Text, nullable=False),
    )
    
    # Status tracking
    status: InvitationStatus = Field(
        default=InvitationStatus.PENDING,
        sa_column=Column(String, nullable=False, default="pending"),
    )
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    expires_at: datetime = Field(
        default_factory=get_default_expiry,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    accepted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    revoked_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    
    # Relationships
    tenant: Optional["Tenant"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[TenantPortalInvitation.tenant_id]",
            "lazy": "selectin",
        }
    )
    inviter: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[TenantPortalInvitation.invited_by]",
            "lazy": "selectin",
        }
    )
    
    @property
    def is_valid(self) -> bool:
        """Check if invitation is still valid (pending and not expired)."""
        return (
            self.status == InvitationStatus.PENDING
            and self.expires_at > datetime.now(timezone.utc)
        )
    
    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return self.expires_at <= datetime.now(timezone.utc)

    __table_args__ = (
        # Note: Indexes are created in migration, but we define them here for documentation
        Index("idx_tenant_portal_invitations_status", "status"),
    )

