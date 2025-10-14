"""
Pydantic models for the Invoices API, defining the data structures for
request and response bodies.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field
from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.invoice_tax_detail import (
    InvoiceTaxDetailCreate, InvoiceTaxDetailResponse
)

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
    
    # Tax support fields
    subtotal_amount: Optional[Decimal] = None
    total_tax_amount: Optional[Decimal] = None
    taxes: Optional[List[InvoiceTaxDetailCreate]] = None

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v
    
    @field_validator('subtotal_amount')
    @classmethod 
    def subtotal_must_be_positive_if_provided(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Subtotal must be greater than 0')
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


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    id: int
    invoice_number: str
    amount: Decimal
    description: str
    issue_date: datetime
    due_date: datetime
    status: PaymentStatus = PaymentStatus.PENDING
    property_id: int | None = None
    tenant_id: int | None = None
    
    # Tax details
    subtotal_amount: Optional[Decimal] = None
    total_tax_amount: Optional[Decimal] = None
    taxes: List[InvoiceTaxDetailResponse] = Field(default_factory=list)
    
    # Metadata
    quickbooks_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    property: Optional[PropertyInfo] = None
    tenant: Optional[TenantInfo] = None

    @model_validator(mode='before')
    @classmethod
    def convert_nested_objects(cls, data):
        """
        Convert SQLModel ORM objects to Pydantic schema objects for nested relationships.
        
        Handles conversion of:
        - Property ORM object → PropertyInfo schema
        - Tenant ORM object → TenantInfo schema
        
        This allows seamless use of model_validate() with ORM objects from database queries.
        """
        if isinstance(data, dict):
            return data
            
        # Convert the SQLModel object to a dictionary
        result = {}
        for field in cls.model_fields:
            value = getattr(data, field, None)
            
            # Handle nested property object
            if field == 'property' and value is not None:
                result[field] = {
                    'id': value.id,
                    'name': value.name
                }
            # Handle nested tenant object
            elif field == 'tenant' and value is not None:
                # TenantInfo expects 'full_name' not first/last
                if hasattr(value, 'tenant_type'):
                    if value.tenant_type.value == 'Company':
                        full_name = value.company_name or 'Company Tenant'
                    else:
                        first = getattr(value, 'first_name', '') or ''
                        last = getattr(value, 'last_name', '') or ''
                        full_name = f"{first} {last}".strip() or 'Tenant'
                else:
                    full_name = 'Unknown Tenant'
                    
                result[field] = {
                    'id': value.id,
                    'full_name': full_name
                }
            else:
                result[field] = value
                
        return result


# === CSV Import Models ===
class CSVInvoiceData(BaseModel):
    """Schema for invoice data from CSV import"""
    invoice_number: str
    amount: Decimal
    description: str
    issue_date: str  # Will be parsed to datetime
    due_date: str    # Will be parsed to datetime
    status: str = PaymentStatus.PENDING.value
    property_name: Optional[str] = None
    tenant_name: Optional[str] = None

    @field_validator('invoice_number')
    @classmethod
    def validate_invoice_number_length(cls, v):
        if v and len(v) > 100:
            raise ValueError('Invoice number must be 100 characters or less')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description_length(cls, v):
        if v and len(v) > 500:
            raise ValueError('Description must be 500 characters or less')
        return v
    
    @field_validator('property_name', 'tenant_name')
    @classmethod
    def validate_name_length(cls, v):
        if v and len(v) > 255:
            raise ValueError('Name must be 255 characters or less')
        return v

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v
    
    @field_validator('issue_date', 'due_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date string follows expected formats."""
        if not v:
            raise ValueError('Date is required')
        
        # Check for common date formats
        import re
        valid_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY or DD/MM/YYYY
            r'^\d{2}-\d{2}-\d{4}$',  # MM-DD-YYYY or DD-MM-YYYY
        ]
        
        if not any(re.match(pattern, v) for pattern in valid_patterns):
            raise ValueError(f'Date format not recognized. Expected formats: YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY')
        
        return v


class CSVImportError(BaseModel):
    """Schema for CSV import error details"""
    row_number: int
    error_message: str


class CSVImportRequest(BaseModel):
    """Request schema for CSV import"""
    invoices: list[CSVInvoiceData]


class CSVImportResult(BaseModel):
    """Result schema for CSV import"""
    total_rows: int
    successful_imports: int
    failed_imports: int
    errors: list[CSVImportError]
    created_invoice_ids: list[int]
