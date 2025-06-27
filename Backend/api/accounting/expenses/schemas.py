"""
API-specific schemas for expense endpoints.

These schemas are used for request/response handling in the expense API endpoints
and are separate from the core expense models defined in Backend/models/accounting/expense.py
"""

from decimal import Decimal
from pydantic import BaseModel

from Backend.models.accounting.expense import TaxDetailItem, ExpenseResponse


class ExpenseReceiptParseDetails(BaseModel):
    expense_date: str | None = None  # LLM might return it as expense_date
    payment_date: str | None = None  # LLM might return it as payment_date
    subtotal_amount: Decimal
    total_tax_amount: Decimal
    total_amount: Decimal
    currency: str | None = None
    tax_details: list[TaxDetailItem] = []  # Individual tax line items
    # Payment method is actually useful for expense tracking
    payment_method: str | None = None
    description_notes: str | None = None
    raw_text_preview: str | None = None


class ExpenseReceiptParseResponse(BaseModel):
    receipt_url: str
    parsed_details: ExpenseReceiptParseDetails
    message: str | None = None


class PaginatedExpensesResponse(BaseModel):
    items: list[ExpenseResponse]
    has_more: bool
