"""
API-specific schemas for expense endpoints.

These schemas are used for request/response handling in the expense API endpoints
and are separate from the core expense models defined in Backend/models/accounting/expense.py
"""

from decimal import Decimal
from pydantic import BaseModel, field_validator

from Backend.models.accounting.expense import TaxDetailItem, ExpenseResponse
from Backend.models.accounting.payment import PaymentMethod


class ExpenseReceiptParseDetails(BaseModel):
    expense_date: str | None = None  # LLM might return it as expense_date
    payment_date: str | None = None  # LLM might return it as payment_date
    subtotal_amount: Decimal
    total_tax_amount: Decimal
    total_amount: Decimal
    currency: str | None = None
    tax_details: list[TaxDetailItem] = []  # Individual tax line items
    # Payment method is actually useful for expense tracking
    payment_method: PaymentMethod | None = None
    # Enhanced fields for better expense categorization
    vendor_name: str | None = None
    expense_category: str | None = None
    description_notes: str | None = None
    raw_text_preview: str | None = None

    @field_validator('payment_method', mode='before')
    @classmethod
    def validate_payment_method(cls, v) -> PaymentMethod | None:
        """Validate and convert payment method strings to enum values"""
        if v is None:
            return None
        
        if isinstance(v, PaymentMethod):
            return v
            
        if isinstance(v, str):
            # Try exact match first
            for method in PaymentMethod:
                if method.value == v:
                    return method
            
            # Try case-insensitive match
            v_lower = v.lower().strip()
            for method in PaymentMethod:
                if method.value.lower() == v_lower:
                    return method
            
            # If no match found, default to OTHER
            return PaymentMethod.OTHER
            
        return PaymentMethod.OTHER


class ExpenseReceiptParseResponse(BaseModel):
    receipt_url: str
    parsed_details: ExpenseReceiptParseDetails
    message: str | None = None


class PaginatedExpensesResponse(BaseModel):
    items: list[ExpenseResponse]
    has_more: bool
