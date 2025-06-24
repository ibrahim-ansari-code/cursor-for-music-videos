"""
LLM utilities package for Brikli Backend.

This package provides Azure OpenAI integration for document parsing and analysis.
"""

# Export the public API
from .client import get_client, test_azure_openai_connection
from .exceptions import PaymentReceiptAnalysisError
from .lease_parser import analyze_lease_text
from .receipt_parser import (
    analyze_expense_receipt_content,
    analyze_payment_receipt_content,
)

__all__ = [
    'get_client',
    'test_azure_openai_connection',
    'analyze_payment_receipt_content',
    'analyze_expense_receipt_content',
    'analyze_lease_text',
    'PaymentReceiptAnalysisError'
]
