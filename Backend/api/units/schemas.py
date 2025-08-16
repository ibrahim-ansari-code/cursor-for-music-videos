import logging
import re
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID as PythonUUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from Backend.models.enums import TenantType

logger = logging.getLogger(__name__)


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
    first_name: str | None = None  # Made optional for company tenants
    last_name: str | None = None   # Made optional for company tenants
    email: str | None = None
    company_name: str | None = None  # Added for company tenants
    tenant_type: TenantType | None = None   # Changed to Enum

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    @classmethod
    def validate_tenant_name_consistency(cls, values):
        """Ensure tenant has either individual names or company name based on type."""
        if values.tenant_type == TenantType.COMPANY:
            if not values.company_name:
                # Log warning but don't fail - allow graceful degradation
                logger.warning(
                    f"Company tenant {values.id} missing company_name")
        elif values.tenant_type == TenantType.INDIVIDUAL:
            if not values.first_name and not values.last_name:
                # Log warning but don't fail - allow graceful degradation
                logger.warning(
                    f"Individual tenant {values.id} missing first_name and last_name")
        return values


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
    # Contains error details for failed units
    failed: list[dict] = Field(default_factory=list)


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
                raise ValueError(
                    'max_rent must be greater than or equal to min_rent')
        return v

    @field_validator('max_bedrooms')
    @classmethod
    def validate_bedroom_range(cls, v: int | None, info) -> int | None:
        if v is not None and 'min_bedrooms' in info.data and info.data['min_bedrooms'] is not None:
            if v < info.data['min_bedrooms']:
                raise ValueError(
                    'max_bedrooms must be greater than or equal to min_bedrooms')
        return v


class CSVAssignmentRow(BaseModel):
    """Schema for a single row in CSV bulk assignment"""
    unit_number: str = Field(..., min_length=1, max_length=255,
                             description="Unit number/identifier as it appears in the property")
    tenant_email: str = Field(..., min_length=3, max_length=255)
    lease_start_date: date = Field(...)
    monthly_rent: Decimal = Field(..., gt=0)
    security_deposit: Decimal | None = Field(None, ge=0, 
                                           description="Security deposit amount. If not provided, defaults to monthly rent")

    @field_validator('tenant_email')
    @classmethod
    def validate_tenant_email(cls, v: str) -> str:
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()  # Normalize to lowercase

    @field_validator('lease_start_date')
    @classmethod
    def validate_lease_start_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError('Lease start date cannot be in the past')
        return v

    @model_validator(mode='after')
    def default_security_deposit(self):
        """Set security_deposit to monthly_rent when it's missing, preventing downstream None handling."""
        if self.security_deposit is None:
            self.security_deposit = self.monthly_rent
        return self


class CSVBulkAssignRequest(BaseModel):
    """Request schema for CSV bulk assignment"""
    assignments: list[CSVAssignmentRow] = Field(
        ..., min_length=1, max_length=1000)


class CSVAssignmentError(BaseModel):
    """Schema for CSV assignment errors"""
    row_number: int
    unit_number: str
    error_message: str
    error_type: str  # 'validation', 'unit_not_found', 'tenant_not_found', 'unit_occupied', 'lease_creation_failed', 'permission_denied', 'http_error_{code}'


class CSVBulkAssignResponse(BaseModel):
    """Response schema for CSV bulk assignment"""
    total_rows: int = Field(..., ge=0)
    successful_assignments: int = Field(..., ge=0)
    failed_assignments: int = Field(..., ge=0)
    errors: list[CSVAssignmentError]
    created_leases: list[int] = Field(
        default_factory=list)  # List of lease IDs


class BulkAssignmentRequest(BaseModel):
    """Request schema for bulk assignment (non-CSV)"""
    unit_ids: list[int] = Field(..., min_length=1, max_length=1000)
    tenant_id: int = Field(..., gt=0)
    lease_start_date: date = Field(...)
    end_date: date = Field(...)
    monthly_rent: Decimal | None = Field(None, gt=0)
    security_deposit: Decimal = Field(..., gt=0)
    rent_due_day: int = Field(default=1, ge=1, le=31)
    late_fee_amount: Decimal | None = Field(None, ge=0)
    late_fee_after_days: int | None = Field(None, ge=0)
    special_terms: str | None = Field(None, max_length=1000)

    @field_validator('lease_start_date')
    @classmethod
    def validate_lease_start_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError('Lease start date cannot be in the past')
        return v

    @model_validator(mode='after')
    def validate_end_date_after_start_date(self):
        if self.end_date <= self.lease_start_date:
            raise ValueError('End date must be after start date')
        return self


class BulkAssignmentResponse(BaseModel):
    """Response schema for bulk assignment"""
    total_units: int = Field(..., ge=0)
    successful_assignments: int = Field(..., ge=0)
    failed_assignments: int = Field(..., ge=0)
    errors: list[CSVAssignmentError]
    created_leases: list[int] = Field(
        default_factory=list)  # List of lease IDs
