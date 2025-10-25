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


class SecureReceiptUrlResponse(BaseModel):
    """Response schema for secure, time-limited receipt URLs"""
    secure_url: str
    expires_at: str  # ISO 8601 datetime string
    expires_in_seconds: int


# CSV Import schemas
class CSVExpenseData(BaseModel):
    """Schema for individual expense data from CSV"""
    category: str
    description: str | None = None
    expense_date: str  # Will be parsed as datetime
    subtotal_amount: Decimal
    total_tax_amount: Decimal | None = None
    payment_method: str | None = None
    property_name: str | None = None
    
    @field_validator('category')
    @classmethod
    def validate_category_length(cls, v):
        """Validate category length."""
        if v and len(v) > 100:
            raise ValueError('Category must be 100 characters or less')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description_length(cls, v):
        """Validate description length."""
        if v and len(v) > 500:
            raise ValueError('Description must be 500 characters or less')
        return v
    
    @field_validator('property_name')
    @classmethod
    def validate_property_name_length(cls, v):
        """Validate property name length."""
        if v and len(v) > 255:
            raise ValueError('Property name must be 255 characters or less')
        return v
    
    @field_validator('expense_date')
    @classmethod
    def validate_date_format(cls, v):
        """Validate date string follows expected formats."""
        if not v:
            raise ValueError('Expense date is required')
        
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


class CSVExpenseImportRequest(BaseModel):
    """Schema for CSV expense import request"""
    expenses: list[CSVExpenseData]


class CSVExpenseImportResult(BaseModel):
    """Schema for CSV expense import response"""
    total_rows: int
    successful_imports: int
    failed_imports: int
    errors: list[CSVImportError]
    created_expense_ids: list[int]
