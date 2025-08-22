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
    lease_id: int
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
    lease_id: int
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

    model_config = ConfigDict(from_attributes=True)

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
