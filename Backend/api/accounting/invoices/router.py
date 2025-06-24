"""
FastAPI router for invoice endpoints.

This module defines the API endpoints for invoice operations, delegating all
business logic to the service layer.
"""
import logging
from datetime import date

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.accounting.common import PaymentStatus
from Backend.models.user import User

from . import service
from .schemas import InvoiceCreate, InvoiceResponse, InvoiceUpdate


logger = logging.getLogger(__name__)
router = APIRouter()


# ===== CREATE =====
@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> InvoiceResponse:
    """
    Creates a new invoice.
    
    Invoices can be created with or without tenant/property associations.
    This flexibility allows for importing invoices from external systems
    like QuickBooks or Stripe.

    Args:
        invoice_data: The invoice creation data.

    Returns:
        The created invoice as an InvoiceResponse.
    """
    return await service.create_invoice(invoice_data, session, current_user)


# ===== READ =====
@router.get("", response_model=list[InvoiceResponse])
async def get_invoices(
    tenant_id: int | None = None,
    property_id: int | None = None,
    payment_status_filter: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[InvoiceResponse]:
    """
    Retrieves a list of invoices filtered by user role and various criteria.

    Args:
        tenant_id: Optional tenant ID to filter invoices.
        property_id: Optional property ID to filter invoices.
        payment_status_filter: Optional payment status to filter invoices.
        start_date: Optional start date for filtering by issue date.
        end_date: Optional end date for filtering by issue date.
        limit: Maximum number of results to return.
        offset: Number of results to skip for pagination.

    Returns:
        A list of invoices matching the applied filters.
    """
    return await service.get_invoices(
        session=session,
        current_user=current_user,
        tenant_id=tenant_id,
        property_id=property_id,
        payment_status_filter=payment_status_filter,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> InvoiceResponse:
    """
    Retrieves a specific invoice by ID.

    Args:
        invoice_id: The ID of the invoice to retrieve.

    Returns:
        The invoice details.
    """
    return await service.get_invoice_by_id(invoice_id, session, current_user)


# ===== UPDATE =====
@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    invoice_data: InvoiceUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> InvoiceResponse:
    """
    Updates an existing invoice.

    Args:
        invoice_id: The ID of the invoice to update.
        invoice_data: The fields to update.

    Returns:
        The updated invoice.
    """
    return await service.update_invoice(invoice_id, invoice_data, session, current_user)


# ===== DELETE =====
@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Deletes an invoice.

    Args:
        invoice_id: The ID of the invoice to delete.
    """
    await service.delete_invoice(invoice_id, session, current_user)


# ===== UTILITY ENDPOINTS =====
@router.post("/mark-paid/{invoice_id}", response_model=InvoiceResponse)
async def mark_invoice_paid(
    invoice_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> InvoiceResponse:
    """
    Marks an invoice as paid.

    Args:
        invoice_id: The ID of the invoice to mark as paid.

    Returns:
        The updated invoice.
    """
    return await service.mark_invoice_paid(invoice_id, session, current_user)
