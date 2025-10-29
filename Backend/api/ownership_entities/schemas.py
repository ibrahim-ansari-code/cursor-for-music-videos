"""
Ownership Entity API Schemas

Defines request and response schemas for ownership entity CRUD operations.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from Backend.models.ownership_entity import EntityType


# ===== BASE SCHEMAS =====

class OwnershipEntityBase(BaseModel):
    """Base schema for ownership entity"""
    entity_type: str = Field(
        ...,
        description="Type of entity: company, individual, trust, partnership, llc, corporation, other"
    )
    name: str = Field(..., min_length=1, max_length=255, description="Display name of the entity")
    legal_name: Optional[str] = Field(None, max_length=500, description="Legal/registered name")
    tax_id: Optional[str] = Field(None, max_length=100, description="Tax ID / EIN / Business Number")

    # Contact information
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_name: Optional[str] = Field(None, max_length=255, description="Primary contact person")

    # Address
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(default="Canada", max_length=100)

    # Notes
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("name", "legal_name", "contact_name")
    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure string fields are not empty or just whitespace"""
        if v is not None and not v.strip():
            raise ValueError("Field must not be empty if provided")
        return v.strip() if v else v

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type"""
        valid_types = {'company', 'individual', 'trust', 'partnership', 'llc', 'corporation', 'other'}
        if v.lower() not in valid_types:
            raise ValueError(f"Entity type must be one of: {', '.join(valid_types)}")
        return v.lower()


# ===== CREATE SCHEMA =====

class OwnershipEntityCreate(OwnershipEntityBase):
    """Schema for creating a new ownership entity"""
    pass


# ===== UPDATE SCHEMA =====

class OwnershipEntityUpdate(BaseModel):
    """Schema for updating an ownership entity (all fields optional)"""
    entity_type: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=500)
    tax_id: Optional[str] = Field(None, max_length=100)

    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    contact_name: Optional[str] = Field(None, max_length=255)

    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    province: Optional[str] = Field(None, max_length=50)
    postal_code: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)

    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("name", "legal_name", "contact_name")
    @classmethod
    def validate_not_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """Ensure string fields are not empty if provided"""
        if v is not None and not v.strip():
            raise ValueError("Field must not be empty if provided")
        return v.strip() if v else v

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate entity type if provided"""
        if v is not None:
            valid_types = {'company', 'individual', 'trust', 'partnership', 'llc', 'corporation', 'other'}
            if v.lower() not in valid_types:
                raise ValueError(f"Entity type must be one of: {', '.join(valid_types)}")
            return v.lower()
        return v

    model_config = ConfigDict(extra="forbid")  # Prevent unexpected fields


# ===== RESPONSE SCHEMAS =====

class OwnershipEntityResponse(OwnershipEntityBase):
    """Response schema for ownership entity"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnershipEntityWithStats(OwnershipEntityResponse):
    """Response schema with additional statistics"""
    total_units: int = Field(default=0, description="Total number of units owned by this entity")
    total_monthly_rent: float = Field(default=0.0, description="Total monthly rent across all units")

    model_config = ConfigDict(from_attributes=True)


# ===== LIST RESPONSE =====

class OwnershipEntityListResponse(BaseModel):
    """Response schema for paginated list of ownership entities"""
    entities: list[OwnershipEntityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)
