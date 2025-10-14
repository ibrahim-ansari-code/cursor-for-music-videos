from datetime import datetime
from enum import Enum
from html import escape as html_escape
from typing import TYPE_CHECKING, Optional, Any
from uuid import UUID as PythonUUID, uuid4
import re

from sqlalchemy import (Column, DateTime, ForeignKey, Index, Integer, String,
                        text)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, Relationship, SQLModel, col
from pydantic import field_validator

from Backend.utils.datetime_utils import create_audit_datetime

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from Backend.models.lease import Lease
    from Backend.models.property import Property
    from Backend.models.units import PropertyUnit
    from Backend.models.user import User
    from Backend.models.maintenance import MaintenanceRequest
    from Backend.models.accounting.payment import Payment
    from Backend.models.accounting.invoice import Invoice


class TenantStatus(str, Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    EVICTED = "Evicted"
    MOVED_OUT = "Moved Out"


# Import TenantType from enums
from Backend.models.enums import TenantType


# Link table for tenant-unit many-to-many relationship


class TenantUnitLink(SQLModel, table=True):
    __tablename__ = "tenant_unit_link"  # type: ignore
    __table_args__ = (Index("ix_tenant_unit_link_unit_id", "unit_id"),)

    tenant_id: int | None = Field(
        default=None, foreign_key="tenants.id", primary_key=True
    )
    unit_id: int | None = Field(
        default=None, foreign_key="property_units.id", primary_key=True
    )
    start_date: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    end_date: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    user_id: PythonUUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            index=True,
        ),
    )
    
    # Tenant type and naming fields
    tenant_type: TenantType = Field(default=TenantType.INDIVIDUAL)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=200)
    contact_person: str | None = Field(default=None, max_length=200)
    
    phone: str | None = None
    email: str | None = None
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    created_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=create_audit_datetime,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    current_property_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey(
            "properties.id", ondelete="SET NULL"))
    )
    landlord_id: PythonUUID = Field(foreign_key="users.id")
    profile_image_url: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )

    # QuickBooks specific fields
    quickbooks_customer_id: str | None = Field(
        default=None, sa_column=Column(String, nullable=True)
    )
    last_synced_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    
    # Emergency contacts stored as JSONB array
    emergency_contacts: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=True),
        description='Emergency contact information as JSONB array'
    )

    # --- Relationships Defined Directly ---

    user: Optional["User"] = Relationship(
        back_populates="tenant_details",
        sa_relationship_kwargs={"foreign_keys": "[Tenant.user_id]"},
    )
    current_property: Optional["Property"] = Relationship(
        back_populates="current_tenants")

    leases: list["Lease"] = Relationship(back_populates="tenant")
    assigned_units: list["PropertyUnit"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={
            "foreign_keys": "[PropertyUnit.tenant_id]",
            "lazy": "selectin"
        }
    )
    units: list["PropertyUnit"] = Relationship(
        back_populates="tenants",
        link_model=TenantUnitLink,
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    maintenance_requests: list["MaintenanceRequest"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    payments: list["Payment"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    invoices: list["Invoice"] = Relationship(
        back_populates="tenant",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    @field_validator('emergency_contacts')
    @classmethod
    def validate_emergency_contacts(cls, v: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        """
        Validate and sanitize emergency contacts structure and business rules.

        Security measures implemented:
        1. XSS Prevention: HTML-escapes all text fields to prevent script injection
        2. Input Validation: Validates required fields, email format, and phone format
        3. Business Rules: Enforces maximum 5 contacts and single primary contact
        4. Database Constraints: Works in conjunction with PostgreSQL CHECK constraints

        This validator provides defense-in-depth security by:
        - Sanitizing user input at the application layer
        - Validating data integrity before database insertion
        - Preventing malicious payloads from being stored
        - Ensuring consistent data structure across the application

        Args:
            v: List of emergency contact dictionaries or None

        Returns:
            Sanitized and validated list of emergency contacts

        Raises:
            ValueError: If validation fails (max contacts, required fields, primary count, formats)

        Note: Database-level validation in migration file provides additional security layer.
        """
        if not v:
            return []

        # Security: Limit to maximum 5 contacts to prevent abuse
        if len(v) > 5:
            raise ValueError("Maximum 5 emergency contacts allowed")

        sanitized_contacts = []
        primary_count = 0

        for idx, contact in enumerate(v):
            # ============================================================================
            # REQUIRED FIELDS VALIDATION
            # ============================================================================

            # Validate name (required)
            if not contact.get('name') or not str(contact['name']).strip():
                raise ValueError(f"Emergency contact #{idx + 1}: name is required")

            # Validate phone (required)
            if not contact.get('phone') or not str(contact['phone']).strip():
                raise ValueError(f"Emergency contact #{idx + 1}: phone is required")

            # Validate relationship (required)
            if not contact.get('relationship') or not str(contact['relationship']).strip():
                raise ValueError(f"Emergency contact #{idx + 1}: relationship is required")

            # ============================================================================
            # XSS SANITIZATION: Escape HTML to prevent script injection
            # ============================================================================

            sanitized_contact = {
                # Security: HTML-escape name to prevent XSS attacks
                'name': html_escape(str(contact['name']).strip()),

                # Security: HTML-escape relationship to prevent XSS attacks
                'relationship': html_escape(str(contact['relationship']).strip()),

                # Security: Sanitize phone number (remove potential HTML/script content)
                # Keep only digits, spaces, hyphens, parentheses, and plus sign
                'phone': re.sub(r'[^\d\s\-\(\)\+]', '', str(contact['phone']).strip()),

                # Preserve boolean flag for primary contact
                'is_primary': bool(contact.get('is_primary', False)),
            }

            # ============================================================================
            # OPTIONAL FIELDS VALIDATION & SANITIZATION
            # ============================================================================

            # Email (optional) - validate format if provided
            if contact.get('email'):
                email = str(contact['email']).strip()
                if email:
                    # Basic email validation using regex
                    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                    if not re.match(email_pattern, email):
                        raise ValueError(
                            f"Emergency contact #{idx + 1}: invalid email format"
                        )
                    # Security: HTML-escape email (though emails shouldn't contain HTML)
                    sanitized_contact['email'] = html_escape(email)

            # Notes (optional) - sanitize if provided
            if contact.get('notes'):
                notes = str(contact['notes']).strip()
                if notes:
                    # Security: HTML-escape notes to prevent XSS attacks
                    # Notes are user-generated content and high-risk for XSS
                    sanitized_contact['notes'] = html_escape(notes)

            # Preserve ID if it exists (for updates), otherwise generate new UUID
            if contact.get('id'):
                sanitized_contact['id'] = contact['id']
            else:
                # Generate UUID for new contacts
                sanitized_contact['id'] = str(uuid4())

            # ============================================================================
            # BUSINESS RULE VALIDATION
            # ============================================================================

            # Count primary contacts for validation
            if sanitized_contact['is_primary']:
                primary_count += 1

            sanitized_contacts.append(sanitized_contact)

        # Ensure only one primary contact (business rule)
        if primary_count > 1:
            raise ValueError("Only one emergency contact can be marked as primary")

        return sanitized_contacts
    
    __table_args__ = (
        Index('idx_tenant_email_unique_per_landlord', "landlord_id", text("lower(email)"), unique=True, postgresql_where=text("email IS NOT NULL")),
        Index("ix_tenants_status", "status"),
        Index("idx_tenants_email_lower", text("lower(email)"),
              postgresql_where=text("email IS NOT NULL")),
        Index("ix_tenants_current_property_id", "current_property_id"),
        Index("idx_tenants_landlord_id", "landlord_id"),
        Index("ix_tenants_tenant_type", "tenant_type"),
    )
