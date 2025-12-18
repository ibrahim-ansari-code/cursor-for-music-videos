from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator, ConfigDict, model_validator

from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.payment import PaymentMethod


class PaymentBase(BaseModel): # Not directly used by endpoints, but good for inheritance if needed
    amount: Decimal
    payment_date: datetime
    payment_method: PaymentMethod
    status: PaymentStatus
    transaction_reference: str | None = None
    description: str | None = None
    lease_id: int
    tenant_id: int | None = None

    @field_validator('transaction_reference', 'description', mode='before')
    @staticmethod
    def empty_str_to_none(v: str | None) -> str | None:
        """
        Converts an empty string to None.
        
        Args:
            v: The input string or None.
        
        Returns:
            None if the input is an empty string; otherwise, returns the original value.
        """
        if v == "":
            return None
        return v

class PaymentCreate(BaseModel):
    lease_id: int | None = None  # Optional - payments can exist without leases
    tenant_id: int | None = None  # Optional - payments can be made by non-tenants
    property_id: int | None = None  # Optional - for context/filtering only
    invoice_id: int | None = None  # Optional - link payment to specific invoice for allocation
    amount: Decimal
    payment_date: datetime | None = None
    payment_method: PaymentMethod | None = PaymentMethod.OTHER
    status: PaymentStatus | None = PaymentStatus.PENDING
    transaction_reference: str | None = None
    description: str | None = None
    tenant_name: str | None = None # Used for response, not directly for DB Payment object
    receipt_url: str | None = None
    reduction_amount: Decimal | None = None
    reduction_reason: str | None = None
    
    @field_validator('amount')
    @staticmethod
    def amount_must_be_positive(v: Decimal) -> Decimal:
        """Validate that amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    @field_validator('reduction_amount')
    @staticmethod
    def reduction_must_be_positive_if_present(v: Decimal | None) -> Decimal | None:
        """Validate that reduction amount is positive if provided."""
        if v is not None and v < 0:
            raise ValueError("Reduction amount must be zero or positive")
        return v
    
    @model_validator(mode='after')
    def validate_reduction_amount(self):
        """Validate that reduction amount doesn't exceed payment amount."""
        if self.reduction_amount is not None and self.amount is not None:
            if self.reduction_amount > self.amount:
                raise ValueError("Reduction amount cannot be greater than payment amount")
        if self.reduction_amount is not None and self.reduction_amount > 0 and not self.reduction_reason:
            raise ValueError("Reduction reason is required when reduction amount is provided")
        return self

class PaymentUpdate(BaseModel):
    amount: Decimal | None = None
    payment_date: datetime | None = None
    payment_method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    transaction_reference: str | None = None
    description: str | None = None
    receipt_url: str | None = None
    reduction_amount: Decimal | None = None
    reduction_reason: str | None = None
    
    @field_validator('amount')
    @staticmethod
    def amount_must_be_positive(v: Decimal | None) -> Decimal | None:
        """Validate that amount is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    @field_validator('reduction_amount')
    @staticmethod
    def reduction_must_be_positive_if_present(v: Decimal | None) -> Decimal | None:
        """Validate that reduction amount is positive if provided."""
        if v is not None and v < 0:
            raise ValueError("Reduction amount must be zero or positive")
        return v
    
    @model_validator(mode='after')
    def validate_reduction_amount(self):
        """Validate that reduction amount doesn't exceed payment amount."""
        if self.reduction_amount is not None and self.amount is not None:
            if self.reduction_amount > self.amount:
                raise ValueError("Reduction amount cannot be greater than payment amount")
        if self.reduction_amount is not None and self.reduction_amount > 0 and not self.reduction_reason:
            raise ValueError("Reduction reason is required when reduction amount is provided")
        return self

class PaymentResponse(BaseModel):
    id: int
    lease_id: int | None = None  # Optional - some payments may not have lease_id
    tenant_id: int | None = None
    amount: Decimal
    payment_date: datetime | None = None
    payment_method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    transaction_reference: str | None = None
    description: str | None = None
    receipt_url: str | None = None
    reduction_amount: Decimal | None = None
    reduction_reason: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    tenant_name: str | None = None
    property_name: str | None = None
    # Integration metadata
    quickbooks_id: str | None = None
    stripe_payment_intent_id: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def convert_nested_objects(cls, data):
        """
        Convert SQLModel ORM objects to Pydantic schema objects for nested relationships.
        
        Handles conversion of:
        - Lease ORM object → Extract property_name and tenant_name
        - Tenant ORM object → Extract tenant_name
        
        This allows seamless use of model_validate() with ORM objects from database queries.
        Payment gets property info through the lease relationship, not directly.
        """
        if isinstance(data, dict):
            return data
            
        # Convert the SQLModel object to a dictionary
        result = {}
        for field in cls.model_fields:
            value = getattr(data, field, None)
            result[field] = value
        
        # Extract tenant_name from tenant relationship if available
        if hasattr(data, 'tenant') and data.tenant is not None:
            tenant = data.tenant
            if hasattr(tenant, 'tenant_type'):
                # Handle both Individual and Company tenants
                if tenant.tenant_type.value == 'Company':
                    result['tenant_name'] = tenant.company_name or 'Company Tenant'
                else:
                    first = getattr(tenant, 'first_name', '') or ''
                    last = getattr(tenant, 'last_name', '') or ''
                    result['tenant_name'] = f"{first} {last}".strip() or 'Tenant'
            
        # Extract property_name from lease.property relationship if available
        if hasattr(data, 'lease') and data.lease is not None:
            lease = data.lease
            if hasattr(lease, 'property') and lease.property is not None:
                result['property_name'] = lease.property.name
                
        return result

class PaginatedPaymentsResponse(BaseModel):
    items: list[PaymentResponse]
    has_more: bool

class PaymentReceiptParseDetails(BaseModel):
    payment_date: str | None = None  # String format from LLM parsing (ISO format: YYYY-MM-DD)
    subtotal_amount: Decimal | None = None
    total_amount: Decimal | None = None
    currency: str | None = None
    payment_method: str | None = None  # String format from LLM, converted to enum later
    description_notes: str | None = None
    raw_text_preview: str | None = None

class PaymentReceiptParseResponse(BaseModel):
    receipt_url: str
    parsed_details: PaymentReceiptParseDetails
    message: str | None = None


# CSV Import schemas
class CSVPaymentData(BaseModel):
    """Schema for individual payment data from CSV"""
    amount: Decimal
    payment_date: str  # Will be parsed as datetime
    payment_method: str | None = None
    status: str | None = None
    transaction_reference: str | None = None
    description: str | None = None
    tenant_name: str | None = None
    property_name: str | None = None
    reduction_amount: Decimal | None = None
    reduction_reason: str | None = None
    
    @field_validator('transaction_reference')
    @staticmethod
    def validate_transaction_ref_length(v: str | None) -> str | None:
        if v and len(v) > 255:
            raise ValueError('Transaction reference must be 255 characters or less')
        return v
    
    @field_validator('description', 'reduction_reason')
    @staticmethod
    def validate_description_length(v: str | None) -> str | None:
        if v and len(v) > 500:
            raise ValueError('Field must be 500 characters or less')
        return v
    
    @field_validator('tenant_name', 'property_name')
    @staticmethod
    def validate_name_length(v: str | None) -> str | None:
        if v and len(v) > 255:
            raise ValueError('Name must be 255 characters or less')
        return v
    
    @field_validator('amount')
    @staticmethod
    def amount_must_be_positive(v: Decimal) -> Decimal:
        """Validate that amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    @field_validator('reduction_amount')
    @staticmethod
    def reduction_must_be_positive_if_present(v: Decimal | None) -> Decimal | None:
        """Validate that reduction amount is positive if provided."""
        if v is not None and v < 0:
            raise ValueError("Reduction amount must be zero or positive")
        return v
    
    @field_validator('payment_date')
    @staticmethod
    def validate_date_format(v: str) -> str:
        """Validate date string follows expected formats."""
        if not v:
            raise ValueError('Payment date is required')
        
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


class CSVPaymentImportRequest(BaseModel):
    """Schema for CSV payment import request"""
    payments: list[CSVPaymentData]


class CSVPaymentImportResult(BaseModel):
    """Schema for CSV payment import response"""
    total_rows: int
    successful_imports: int
    failed_imports: int
    errors: list[CSVImportError]
    created_payment_ids: list[int]


class SecureReceiptUrlResponse(BaseModel):
    """Response schema for secure, time-limited receipt URLs"""
    secure_url: str
    expires_at: str  # ISO 8601 datetime string
    expires_in_seconds: int
