"""
Tax Preferences API Module

Provides smart tax selection and preference management functionality.
"""

from .router import router
from .service import TaxPreferenceService, get_smart_tax_for_expense, get_smart_tax_for_invoice

__all__ = [
    "router",
    "TaxPreferenceService", 
    "get_smart_tax_for_expense",
    "get_smart_tax_for_invoice"
]