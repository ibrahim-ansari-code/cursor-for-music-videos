"""
Vendor Models - Normalized Design

Defines the Vendor and UserVendor SQLModels for the normalized vendor system.
- Vendor: Central table for all vendors (shared across users)
- UserVendor: Join table linking users to vendors with user-specific data
"""
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID as PythonUUID
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from Backend.models.user import User
    from Backend.models.maintenance import MaintenanceRequest


class Vendor(SQLModel, table=True):
    """
    Central repository of all vendors/contractors in the platform.
    
    This table is shared across all users to prevent duplication and enable
    future marketplace features like ratings, reviews, and vendor discovery.
    """
    __tablename__ = "vendors"

    __table_args__ = (
        Index("idx_vendors_company_name", "company_name"),
        Index("idx_vendors_trade_category", "trade_category"),
        Index("idx_vendors_phone", "phone"),
        Index("idx_vendors_is_verified", "is_verified"),
    )

    # Primary Key
    id: int | None = Field(default=None, primary_key=True)
    
    # Core Vendor Information
    company_name: str = Field(
        sa_column=Column(String(255), nullable=False),
        description="Vendor company or business name"
    )
    contact_person: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
        description="Name of primary contact person"
    )
    trade_category: str = Field(
        sa_column=Column(String(100), nullable=False),
        description="Type of service (Plumber, Electrician, HVAC, etc.)"
    )
    
    # Contact Information
    phone: str = Field(
        sa_column=Column(String(20), nullable=False),
        description="Vendor phone number for notifications"
    )
    email: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
        description="Vendor email address"
    )
    
    # Platform Features (Future)
    is_verified: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
        description="Whether vendor has been verified by platform"
    )
    verification_date: datetime | None = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True),
        description="Date vendor was verified"
    )
    average_rating: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(3, 2), nullable=True),
        description="Platform-wide average rating (0-5 scale)"
    )
    total_reviews: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default="0"),
        description="Total number of reviews across all users"
    )
    
    # Audit Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.func.now()
        )
    )
    
    # Relationships
    user_associations: list["UserVendor"] = Relationship(back_populates="vendor")
    maintenance_requests: list["MaintenanceRequest"] = Relationship(
        back_populates="vendor"
    )


class UserVendor(SQLModel, table=True):
    """
    Join table linking users to vendors with user-specific preferences.
    
    Stores user-specific data like notes, favorites, and personal ratings
    while keeping the vendor data centralized.
    """
    __tablename__ = "user_vendors"

    __table_args__ = (
        Index("idx_user_vendors_user_id", "user_id"),
        Index("idx_user_vendors_vendor_id", "vendor_id"),
        Index("idx_user_vendors_is_active", "user_id", "is_active"),
        Index("idx_user_vendors_is_favorite", "user_id", "is_favorite"),
        sa.UniqueConstraint("user_id", "vendor_id", name="user_vendors_unique_association"),
    )

    # Primary Key
    id: int | None = Field(default=None, primary_key=True)
    
    # Foreign Keys
    user_id: PythonUUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    vendor_id: int = Field(
        sa_column=Column(
            Integer,
            sa.ForeignKey("vendors.id", ondelete="CASCADE"),
            nullable=False
        )
    )
    
    # User-Specific Data
    notes: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="User's personal notes about this vendor"
    )
    is_active: bool = Field(
        default=True,
        sa_column=Column(Boolean, nullable=False, server_default="true"),
        description="Whether user currently works with this vendor"
    )
    is_favorite: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default="false"),
        description="Whether user has marked this as favorite"
    )
    personal_rating: int | None = Field(
        default=None,
        sa_column=Column(Integer, nullable=True),
        description="User's personal rating (1-5 scale)"
    )
    
    # Audit Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP")
        )
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.func.now()
        )
    )
    
    # Relationships
    user: "User" = Relationship(back_populates="vendor_associations")
    vendor: "Vendor" = Relationship(back_populates="user_associations")

