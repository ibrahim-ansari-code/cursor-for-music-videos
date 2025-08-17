from fastapi import APIRouter

from .payments.router import router as payments_router
from .expenses.router import router as expenses_router
from .invoices.router import router as invoices_router
from .insights import router as insights_router
from .rent_tracker.router import router as rent_tracker_router

accounting_api_router = APIRouter()

accounting_api_router.include_router(payments_router, prefix="/payments", tags=["Accounting - Payments"])
accounting_api_router.include_router(expenses_router, prefix="/expenses", tags=["Accounting - Expenses"])
accounting_api_router.include_router(invoices_router, prefix="/invoices", tags=["Accounting - Invoices"])
accounting_api_router.include_router(insights_router, prefix="/insights", tags=["Accounting - Insights"])
accounting_api_router.include_router(rent_tracker_router, prefix="/rent-tracker", tags=["Accounting - Rent Tracker"])

__all__ = ["accounting_api_router"]
