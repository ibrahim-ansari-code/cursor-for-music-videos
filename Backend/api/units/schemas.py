from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, field_validator


class UnitValidatorMixin:
    """Mixin class containing shared validators for unit fields."""
    
    @field_validator('monthly_rent')
    @classmethod
    def validate_rent(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v < 0:
            raise ValueError('Monthly rent cannot be negative')
        return v
    
    @field_validator('size')
    @classmethod
    def validate_size(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError('Size must be greater than 0')
        return v
    
    @field_validator('bedrooms')
    @classmethod
    def validate_bedrooms(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError('Bedrooms cannot be negative')
        return v
    
    @field_validator('bathrooms')
    @classmethod
    def validate_bathrooms(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError('Bathrooms cannot be negative')
        return v


class UnitBase(UnitValidatorMixin, BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    size: float | None = None
    monthly_rent: Decimal | None = None
    is_rented: bool = False
    bedrooms: int | None = None
    bathrooms: float | None = None
    floor: int | None = None


class UnitCreate(UnitBase):
    pass


class UnitUpdate(UnitValidatorMixin, BaseModel):
    """Represents the fields that can be updated for a property unit.
    
    Note: is_rented is managed internally based on tenant assignment/lease status
    and cannot be directly modified.
    """
    name: str | None = None  # Allow partial updates
    description: str | None = None
    size: float | None = None
    monthly_rent: Decimal | None = None
    bedrooms: int | None = None
    bathrooms: float | None = None
    floor: int | None = None
    tenant_id: int | None = None  # Added tenant_id for assignments


class TenantInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UnitCreateResponse(UnitBase):
    """Specific response model for creating a unit (omits tenant)"""
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UnitResponse(UnitBase):
    """Standard response model including optional tenant info"""
    id: int
    property_id: int
    created_at: datetime
    updated_at: datetime
    tenant: TenantInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class BulkUnitCreate(BaseModel):
    """Schema for bulk unit creation"""
    units: list[UnitCreate] = Field(..., min_length=1, max_length=100)


class BulkUnitCreateResponse(BaseModel):
    """Response for bulk unit creation"""
    created: list[UnitCreateResponse]
    failed: list[dict] = Field(default_factory=list)  # Contains error details for failed units


class UnitSearchFilters(BaseModel):
    """Filters for unit search"""
    min_rent: Decimal | None = Field(None, ge=0)
    max_rent: Decimal | None = Field(None, ge=0)
    min_bedrooms: int | None = Field(None, ge=0)
    max_bedrooms: int | None = Field(None, ge=0)
    min_bathrooms: float | None = Field(None, ge=0)
    is_rented: bool | None = None
    property_ids: list[int] | None = None
    
    @field_validator('max_rent')
    @classmethod
    def validate_rent_range(cls, v: Decimal | None, info) -> Decimal | None:
        if v is not None and 'min_rent' in info.data and info.data['min_rent'] is not None:
            if v < info.data['min_rent']:
                raise ValueError('max_rent must be greater than or equal to min_rent')
        return v
    
    @field_validator('max_bedrooms')
    @classmethod
    def validate_bedroom_range(cls, v: int | None, info) -> int | None:
        if v is not None and 'min_bedrooms' in info.data and info.data['min_bedrooms'] is not None:
            if v < info.data['min_bedrooms']:
                raise ValueError('max_bedrooms must be greater than or equal to min_bedrooms')
        return v
