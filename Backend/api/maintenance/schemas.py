from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from Backend.models.enums import MaintenancePriority, MaintenanceStatus


class MaintenanceRequestCreate(BaseModel):
    issue_title: str
    description: str | None = None
    property_id: int
    unit_id: int | None = None
    tenant_id: int | None = None
    priority: MaintenancePriority
    scheduled_date: date | None = None
    estimated_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    photos: list[str] | None = None
    assigned_to: str | None = None


class MaintenanceRequestUpdate(BaseModel):
    issue_title: str | None = None
    description: str | None = None
    property_id: int | None = None
    unit_id: int | None = None
    tenant_id: int | None = None
    priority: MaintenancePriority | None = None
    status: MaintenanceStatus | None = None
    scheduled_date: date | None = None
    completed_date: datetime | None = None
    estimated_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    photos: list[str] | None = None
    assigned_to: str | None = None


class PropertyInfo(BaseModel):
    id: int
    name: str


class UnitInfo(BaseModel):
    id: int
    name: str


class TenantInfo(BaseModel):
    id: int
    first_name: str
    last_name: str


class MaintenanceRequestResponse(BaseModel):
    id: int
    issue_title: str
    description: str | None
    property: PropertyInfo | None
    unit: UnitInfo | None
    tenant: TenantInfo | None
    request_date: datetime
    priority: MaintenancePriority
    status: MaintenanceStatus
    scheduled_date: date | None
    completed_date: datetime | None
    estimated_cost: Decimal | None
    actual_cost: Decimal | None
    photos: list[str] | None
    created_at: datetime
    updated_at: datetime
    assigned_to: str | None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def convert_nested_objects(cls, data):
        """Convert SQLModel objects to schema objects for nested relationships."""
        if isinstance(data, dict):
            return data
            
        # Convert the SQLModel object to a dictionary
        result = {}
        for field in cls.model_fields:
            value = getattr(data, field, None)
            
            # Handle nested objects
            if field == 'property' and value is not None:
                result[field] = {
                    'id': value.id,
                    'name': value.name
                }
            elif field == 'unit' and value is not None:
                result[field] = {
                    'id': value.id,
                    'name': value.name
                }
            elif field == 'tenant' and value is not None:
                result[field] = {
                    'id': value.id,
                    'first_name': value.first_name,
                    'last_name': value.last_name
                }
            else:
                result[field] = value
                
        return result


class MaintenanceSummaryResponse(BaseModel):
    total_requests: int
    pending: int
    in_progress: int
    completed: int
    scheduled: int
    cancelled: int


class MaintenancePhotoUploadResponse(BaseModel):
    photo_url: str