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
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    tenant_type: str | None = None


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
        """
        Convert SQLModel ORM objects to Pydantic schema for nested relationships.
        
        Only accesses specific nested fields to avoid triggering lazy loading.
        All relationships must be eager-loaded with selectinload() before validation.
        """
        if isinstance(data, dict):
            return data
        
        # Build result dict by directly accessing known fields
        # This is simpler and more explicit than iterating over all schema fields
        result = {
            'id': data.id,
            'issue_title': data.issue_title,
            'description': data.description,
            'request_date': data.request_date,
            'priority': data.priority,
            'status': data.status,
            'scheduled_date': getattr(data, 'scheduled_date', None),
            'completed_date': getattr(data, 'completed_date', None),
            'estimated_cost': getattr(data, 'estimated_cost', None),
            'actual_cost': getattr(data, 'actual_cost', None),
            'photos': getattr(data, 'photos', None),
            'created_at': data.created_at,
            'updated_at': data.updated_at,
            'assigned_to': getattr(data, 'assigned_to', None),
        }
        
        # Handle nested relationships (must be eager-loaded)
        if hasattr(data, 'property') and data.property is not None:
            result['property'] = {
                'id': data.property.id,
                'name': data.property.name
            }
        else:
            result['property'] = None
            
        if hasattr(data, 'unit') and data.unit is not None:
            result['unit'] = {
                'id': data.unit.id,
                'name': data.unit.name
            }
        else:
            result['unit'] = None
            
        if hasattr(data, 'tenant') and data.tenant is not None:
            result['tenant'] = {
                'id': data.tenant.id,
                'first_name': getattr(data.tenant, 'first_name', None),
                'last_name': getattr(data.tenant, 'last_name', None),
                'company_name': getattr(data.tenant, 'company_name', None),
                'tenant_type': data.tenant.tenant_type.value if hasattr(data.tenant, 'tenant_type') else None
            }
        else:
            result['tenant'] = None
                
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


class SecurePhotoUrlResponse(BaseModel):
    """Response schema for secure, time-limited photo URLs"""
    secure_url: str
    expires_at: str  # ISO 8601 datetime string
    expires_in_seconds: int