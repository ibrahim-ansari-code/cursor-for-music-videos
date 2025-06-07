from fastapi import APIRouter

from .payments import router as payments_router
from .expenses import router as expenses_router
from .invoices import router as invoices_router
from .insights import router as insights_router
from .quickbooks_handler import router as quickbooks_router

accounting_api_router = APIRouter()

accounting_api_router.include_router(payments_router, prefix="/payments", tags=["Accounting - Payments"])
accounting_api_router.include_router(expenses_router, prefix="/expenses", tags=["Accounting - Expenses"])
accounting_api_router.include_router(invoices_router, prefix="/invoices", tags=["Accounting - Invoices"])
accounting_api_router.include_router(insights_router, prefix="/insights", tags=["Accounting - Insights"])
accounting_api_router.include_router(quickbooks_router, prefix="/quickbooks", tags=["Accounting - QuickBooks"])

__all__ = ["accounting_api_router"]
