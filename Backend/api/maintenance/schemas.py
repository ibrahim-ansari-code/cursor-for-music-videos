from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator
from sqlalchemy import inspect

from Backend.models.enums import MaintenancePriority, MaintenanceStatus


class MaintenanceRequestCreate(BaseModel):
    issue_title: str
    description: str | None = None
    property_id: int | None = None  # Optional - auto-inferred for tenants
    unit_id: int | None = None
    tenant_id: int | None = None  # Optional - auto-inferred for tenants
    priority: MaintenancePriority
    scheduled_date: date | None = None
    estimated_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    photos: list[str] | None = None
    assigned_to: str | None = None
    preferred_time: str | None = None
    vendor_id: int | None = None
    notify_tenant: bool = False


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
    preferred_time: str | None = None
    vendor_id: int | None = None
    notify_tenant: bool | None = None


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


class VendorContactInfo(BaseModel):
    """Basic vendor contact information for maintenance request responses"""
    id: int
    company_name: str
    contact_person: str | None = None
    trade_category: str
    phone: str
    email: str | None = None


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
    preferred_time: str | None
    vendor_id: int | None
    vendor: VendorContactInfo | None
    notify_tenant: bool

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
            'preferred_time': getattr(data, 'preferred_time', None),
            'vendor_id': getattr(data, 'vendor_id', None),
            'notify_tenant': getattr(data, 'notify_tenant', False),
        }
        
        # Handle nested relationships (check if loaded to avoid lazy-loading)
        try:
            insp = inspect(data)
        except Exception:
            # Not a SQLAlchemy-instrumented object, return as-is
            return data
        
        # Property relationship
        if 'property' not in insp.unloaded:
            prop = data.property
            if prop is not None:
                result['property'] = {
                    'id': prop.id,
                    'name': prop.name
                }
            else:
                result['property'] = None
        else:
            result['property'] = None
            
        # Unit relationship
        if 'unit' not in insp.unloaded:
            unit = data.unit
            if unit is not None:
                result['unit'] = {
                    'id': unit.id,
                    'name': unit.name
                }
            else:
                result['unit'] = None
        else:
            result['unit'] = None
            
        # Tenant relationship
        if 'tenant' not in insp.unloaded:
            tenant = data.tenant
            if tenant is not None:
                result['tenant'] = {
                    'id': tenant.id,
                    'first_name': getattr(tenant, 'first_name', None),
                    'last_name': getattr(tenant, 'last_name', None),
                    'company_name': getattr(tenant, 'company_name', None),
                    'tenant_type': tenant.tenant_type.value if hasattr(tenant, 'tenant_type') else None
                }
            else:
                result['tenant'] = None
        else:
            result['tenant'] = None
            
        # Vendor relationship
        if 'vendor' not in insp.unloaded:
            vendor = data.vendor
            if vendor is not None:
                result['vendor'] = {
                    'id': vendor.id,
                    'company_name': vendor.company_name,
                    'contact_person': getattr(vendor, 'contact_person', None),
                    'trade_category': vendor.trade_category,
                    'phone': vendor.phone,
                    'email': getattr(vendor, 'email', None)
                }
            else:
                result['vendor'] = None
        else:
            result['vendor'] = None
                
        return result


class MaintenanceSummaryResponse(BaseModel):
    total_requests: int
    new: int
    pending: int
    in_progress: int
    completed: int
    scheduled: int
    cancelled: int


class MaintenancePhotoUploadResponse(BaseModel):
    photo_url: str


class MaintenanceRequestBulkDelete(BaseModel):
    request_ids: list[int]


class SecurePhotoUrlResponse(BaseModel):
    """Response schema for secure, time-limited photo URLs"""
    secure_url: str
    expires_at: str  # ISO 8601 datetime string
    expires_in_seconds: int


class NotifyVendorRequest(BaseModel):
    """Request schema for manually notifying vendor with optional custom message"""
    custom_message: str | None = None


class NotifyVendorResponse(BaseModel):
    """Response schema for vendor notification endpoint"""
    success: bool
    message: str
    vendor_email: str | None = None
