"""
Pydantic models for the Invoices API, defining the data structures for
request and response bodies.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator
from Backend.models.accounting.common import PaymentStatus

# === API Models for Invoices ===
class InvoiceBase(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    invoice_number: str
    amount: Decimal
    description: str
    issue_date: datetime
    due_date: datetime
    status: PaymentStatus = PaymentStatus.PENDING
    property_id: int | None = None
    tenant_id: int | None = None

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v

    @field_validator('due_date')
    @classmethod
    def due_date_must_not_be_earlier_than_issue_date(cls, v, info):
        if 'issue_date' in info.data and v < info.data['issue_date']:
            raise ValueError('Due date cannot be earlier than issue date')
        return v


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    
    amount: Decimal | None = None
    description: str | None = None
    issue_date: datetime | None = None
    due_date: datetime | None = None
    status: PaymentStatus | None = None

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v

    @field_validator('due_date')
    @classmethod
    def due_date_must_not_be_earlier_than_issue_date(cls, v, info):
        # Skip validation if due_date is None
        if v is None:
            return v
        
        # Skip validation if issue_date is not provided or is None
        if 'issue_date' not in info.data or info.data['issue_date'] is None:
            return v
        
        # Validate that due_date is not earlier than issue_date
        if v < info.data['issue_date']:
            raise ValueError('Due date cannot be earlier than issue date')
        
        return v


class PropertyInfo(BaseModel):
    """Minimal property information for invoice responses"""
    id: int
    name: str


class TenantInfo(BaseModel):
    """Minimal tenant information for invoice responses"""
    id: int
    full_name: str


class InvoiceResponse(InvoiceBase):
    id: int
    quickbooks_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    property: Optional[PropertyInfo] = None
    tenant: Optional[TenantInfo] = None

    model_config = ConfigDict(from_attributes=True)
