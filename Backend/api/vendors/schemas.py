"""
Vendor Contact Schemas

Pydantic models for request/response validation for vendor contact endpoints.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VendorContactBase(BaseModel):
    """Base schema for vendor contact data"""
    company_name: str = Field(..., min_length=1, max_length=255, description="Vendor company or business name")
    contact_person: Optional[str] = Field(None, max_length=255, description="Primary contact person name")
    trade_category: str = Field(..., min_length=1, max_length=100, description="Type of service (Plumber, Electrician, etc.)")
    phone: str = Field(..., min_length=1, max_length=20, description="Vendor phone number")
    email: Optional[str] = Field(None, max_length=255, description="Vendor email address")
    notes: Optional[str] = Field(None, description="Additional notes about vendor")
    is_active: bool = Field(True, description="Whether vendor is currently active")

    @field_validator('company_name', 'trade_category', 'phone')
    @classmethod
    def validate_not_empty(cls, v: str, info) -> str:
        """Ensure required string fields are not empty after trimming"""
        if not v or not v.strip():
            raise ValueError(f'{info.field_name} cannot be empty')
        return v.strip()

    @field_validator('contact_person', 'email', 'notes')
    @classmethod
    def validate_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        """Trim optional string fields"""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class VendorContactCreate(VendorContactBase):
    """Schema for creating a new vendor contact"""
    pass


class VendorContactUpdate(BaseModel):
    """
    Schema for updating vendor contact - updates user-specific fields only.
    Central vendor fields cannot be updated by individual users.
    """
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    is_favorite: Optional[bool] = None
    personal_rating: Optional[int] = Field(None, ge=1, le=5, description="Personal rating 1-5")

    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Trim notes field"""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class VendorContactResponse(VendorContactBase):
    """Schema for vendor contact response - includes both vendor and user-specific data"""
    id: int
    user_id: UUID  # User who added this vendor
    created_at: datetime
    updated_at: datetime
    
    # User-specific fields from UserVendor join table
    is_favorite: bool = False
    personal_rating: Optional[int] = None
    
    # Platform-wide fields from Vendor table
    is_verified: bool = False
    average_rating: Optional[float] = None
    total_reviews: int = 0

    class Config:
        from_attributes = True


class VendorContactListResponse(BaseModel):
    """Schema for paginated list of vendor contacts"""
    vendors: list[VendorContactResponse]
    total: int
    limit: int
    offset: int


class VendorContactBulkDelete(BaseModel):
    """Schema for bulk delete request"""
    vendor_ids: list[int] = Field(..., min_length=1, description="List of vendor IDs to delete")

