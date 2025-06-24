
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator, ConfigDict

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
    
    @field_validator('amount')
    @staticmethod
    def amount_must_be_positive(v: Decimal) -> Decimal:
        """Validate that amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

class PaymentUpdate(BaseModel):
    amount: Decimal | None = None
    payment_date: datetime | None = None
    payment_method: PaymentMethod | None = None
    status: PaymentStatus | None = None
    transaction_reference: str | None = None
    description: str | None = None
    receipt_url: str | None = None
    
    @field_validator('amount')
    @staticmethod
    def amount_must_be_positive(v: Decimal | None) -> Decimal | None:
        """Validate that amount is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Amount must be positive")
        return v

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
