from datetime import datetime
from decimal import Decimal
from uuid import UUID as PythonUUID

from pydantic import BaseModel, ConfigDict, field_validator

from Backend.api.units import TenantInfo
from Backend.models.enums import PropertyStatus
from Backend.models.property import PropertyType


class PropertyCreate(BaseModel):
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: PropertyType
    description: str | None = None
    year_built: int | None = None
    status: PropertyStatus | None = PropertyStatus.ACTIVE
    units: list[str] | None = None

    # Validator to ensure 'name' is not empty or whitespace only
    @field_validator("name")
    def name_must_not_be_empty(cls, value):
        if not value or not value.strip():
            raise ValueError("name must not be empty")
        return value


# New Model for Property Updates (Excludes units and potentially immutable fields like property_type)
class PropertyUpdate(BaseModel):
    """Schema for updating an existing property's details."""

    name: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
    description: str | None = None
    year_built: int | None = None
    status: PropertyStatus | None = None

    @field_validator("name")
    def name_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("name must not be an empty string")
        return value

    model_config = ConfigDict(extra="forbid")  # Prevent unexpected fields like 'units'


class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: PropertyType
    description: str | None = None
    year_built: int | None = None
    status: PropertyStatus = PropertyStatus.ACTIVE
    user_id: PythonUUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwnerResponse(BaseModel):
    id: PythonUUID
    first_name: str | None = None
    last_name: str | None = None
    email: str
    phone: str | None = None
    profile_image_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UnitResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    size: float | None = None
    monthly_rent: Decimal | None = None
    is_rented: bool
    bedrooms: int | None = None
    bathrooms: float | None = None
    floor: int | None = None
    created_at: datetime
    updated_at: datetime
    tenant: TenantInfo | None = None

    model_config = ConfigDict(from_attributes=True)


class PropertyDetailResponse_Standalone(BaseModel):
    # Fields from PropertyResponse
    id: int
    name: str
    address: str
    city: str
    province: str
    postal_code: str
    property_type: PropertyType
    description: str | None = None
    year_built: int | None = None
    status: PropertyStatus
    user_id: PythonUUID
    created_at: datetime
    updated_at: datetime
    # Additional fields for detail view
    owner: OwnerResponse | None = None
    units: list[UnitResponse] = []  # Changed from List[UnitResponse]

    model_config = ConfigDict(from_attributes=True)

class PropertyDetailResponse(PropertyResponse):
    owner: OwnerResponse | None = None
    # Add additional fields for property details
    # Changed from str to PropertyStatus
    status: PropertyStatus = PropertyStatus.ACTIVE
    units: list[UnitResponse] = []  # Changed from List[UnitResponse] 