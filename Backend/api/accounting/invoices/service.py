"""
Service layer for invoice operations.

This module contains the core business logic for creating and retrieving invoices,
handling property ownership validation, and applying role-based access control.
"""

import logging
from datetime import date, datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from Backend.api.accounting.helpers import check_property_ownership
from Backend.models.accounting.common import PaymentStatus
from Backend.models.accounting.invoice import Invoice
from Backend.models.enums import UserType
from Backend.models.lease import Lease
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.datetime_utils import (
    date_to_utc_range, validate_business_datetime, validate_date_range
)

from .helpers import (
    infer_property_for_invoice,
    apply_tenant_invoice_filters,
    apply_landlord_invoice_filters,
    apply_admin_invoice_filters,
    build_invoice_response
)
from .schemas import InvoiceCreate, InvoiceResponse, InvoiceUpdate


logger = logging.getLogger(__name__)


async def create_invoice(
    invoice_data: InvoiceCreate,
    session: AsyncSession,
    current_user: User
) -> InvoiceResponse:
    """
    Creates a new invoice.
    
    Allows admin and landlord users to create invoices. Invoices can be created
    with or without tenant/property associations, supporting imports from external
    systems like QuickBooks or Stripe.

    Args:
        invoice_data: The invoice creation data.
        session: The database session.
        current_user: The user creating the invoice.

    Returns:
        The created invoice as an InvoiceResponse.

    Raises:
        HTTPException: For authorization, validation, or processing errors.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create invoices")

    # If tenant_id is provided without property_id, try to infer property
    final_property_id = invoice_data.property_id
    if invoice_data.tenant_id and not final_property_id:
        tenant_query = select(Tenant).options(
            selectinload(getattr(Tenant, "leases")).selectinload(getattr(Lease, "property")),
            selectinload(getattr(Tenant, "current_property"))
        ).where(col(Tenant.id) == invoice_data.tenant_id)
        tenant = (await session.execute(tenant_query)).scalar_one_or_none()

        if tenant:
            inferred_property_id = await infer_property_for_invoice(tenant, current_user)
            if inferred_property_id:
                final_property_id = inferred_property_id
                logger.info(f"Inferred property_id {final_property_id} for tenant {invoice_data.tenant_id}")

    # If property_id is set (original or inferred), verify ownership
    if final_property_id:
        await check_property_ownership(final_property_id, session, current_user)
        
    # Update invoice_data with final property_id if it was inferred
    if final_property_id != invoice_data.property_id:
        invoice_data = invoice_data.model_copy(update={"property_id": final_property_id})

    try:
        invoice_data_dict = invoice_data.model_dump(mode='python')
        
        # Validate dates
        if invoice_data_dict.get('issue_date') and isinstance(invoice_data_dict['issue_date'], datetime):
            invoice_data_dict['issue_date'] = validate_business_datetime(invoice_data_dict['issue_date'])
        if invoice_data_dict.get('due_date') and isinstance(invoice_data_dict['due_date'], datetime):
            invoice_data_dict['due_date'] = validate_business_datetime(invoice_data_dict['due_date'])
        
        issue = invoice_data_dict.get('issue_date')
        due = invoice_data_dict.get('due_date')
        if issue and due and due < issue:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Due date cannot be earlier than issue date."
            )
        
        new_invoice = Invoice(**invoice_data_dict)
        session.add(new_invoice)
        await session.commit()
        
        # Refresh with relationships loaded
        await session.refresh(new_invoice)
        if new_invoice.property_id:
            await session.refresh(new_invoice, ["property"])
        if new_invoice.tenant_id:
            await session.refresh(new_invoice, ["tenant"])
        
        logger.info("Invoice %s created for tenant %s, property %s by user %s", 
                    new_invoice.id, new_invoice.tenant_id, new_invoice.property_id, current_user.id)
        return InvoiceResponse(**build_invoice_response(new_invoice))
    except Exception as e:
        await session.rollback()
        logger.exception("Error creating invoice")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to create invoice."
        ) from e


async def get_invoices(
    session: AsyncSession,
    current_user: User,
    tenant_id: int | None = None,
    property_id: int | None = None,
    payment_status_filter: PaymentStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0
) -> list[InvoiceResponse]:
    """
    Retrieves a list of invoices filtered by user role and various criteria.

    Args:
        session: The database session.
        current_user: The user making the request.
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
    validate_date_range(start_date, end_date)

    query = select(Invoice).options(
        selectinload(getattr(Invoice, "property")),
        selectinload(getattr(Invoice, "tenant"))
    )
    filters = []

    if payment_status_filter:
        filters.append(col(Invoice.status) == payment_status_filter)
    if start_date:
        start_datetime, _ = date_to_utc_range(start_date, start_date)
        filters.append(col(Invoice.issue_date) >= start_datetime)
    if end_date:
        _, end_datetime = date_to_utc_range(end_date, end_date)
        filters.append(col(Invoice.issue_date) <= end_datetime)

    if current_user.user_type == UserType.TENANT:
        await apply_tenant_invoice_filters(filters, tenant_id, property_id, current_user, session)
    elif current_user.user_type == UserType.LANDLORD:
        can_proceed = await apply_landlord_invoice_filters(filters, property_id, tenant_id, current_user, session)
        if not can_proceed:
            logger.info("Landlord user %s has no accessible properties for invoice query", current_user.id)
            return []
    elif current_user.user_type == UserType.ADMIN:
        apply_admin_invoice_filters(filters, property_id, tenant_id)
    else:
        raise HTTPException(status_code=403, detail="Not authorized to access these invoices.")

    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(col(Invoice.issue_date).desc())
    query = query.limit(limit).offset(offset)
    
    invoices_orm = (await session.execute(query)).scalars().all()
    return [InvoiceResponse(**build_invoice_response(inv)) for inv in invoices_orm]


async def get_invoice_by_id(
    invoice_id: int,
    session: AsyncSession,
    current_user: User
) -> InvoiceResponse:
    """
    Retrieves a specific invoice by ID.

    Args:
        invoice_id: The ID of the invoice to retrieve.
        session: The database session.
        current_user: The user making the request.

    Returns:
        The invoice details.

    Raises:
        HTTPException: If invoice not found or user not authorized.
    """
    query = select(Invoice).options(
        selectinload(getattr(Invoice, "property")),
        selectinload(getattr(Invoice, "tenant"))
    ).where(col(Invoice.id) == invoice_id)
    
    invoice = (await session.execute(query)).scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    # Check authorization
    if current_user.user_type == UserType.TENANT:
        tenant_query = select(Tenant).where(col(Tenant.user_id) == current_user.id)
        user_tenant = await session.scalar(tenant_query)
        if not user_tenant or invoice.tenant_id != user_tenant.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this invoice")
    elif current_user.user_type == UserType.LANDLORD:
        if invoice.property_id:
            await check_property_ownership(invoice.property_id, session, current_user)
        # Allow landlords to access invoices with NULL property_id (unassigned invoices)
        # No else clause needed - if property_id is NULL, access is allowed
    
    return InvoiceResponse(**build_invoice_response(invoice))


async def update_invoice(
    invoice_id: int,
    invoice_data: InvoiceUpdate,
    session: AsyncSession,
    current_user: User
) -> InvoiceResponse:
    """
    Updates an existing invoice.

    Args:
        invoice_id: The ID of the invoice to update.
        invoice_data: The fields to update.
        session: The database session.
        current_user: The user making the request.

    Returns:
        The updated invoice.

    Raises:
        HTTPException: If invoice not found or user not authorized.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update invoices")
    
    # Get existing invoice
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    # Check ownership if landlord and invoice has a property
    if current_user.user_type == UserType.LANDLORD and invoice.property_id:
        await check_property_ownership(invoice.property_id, session, current_user)
    # TODO: For invoices with NULL property_id, add created_by_user_id field to Invoice model
    # to ensure landlords can only update invoices they created
    
    # Update fields
    update_dict = invoice_data.model_dump(exclude_unset=True)
    
    # Validate dates if provided
    if 'issue_date' in update_dict and update_dict['issue_date']:
        update_dict['issue_date'] = validate_business_datetime(update_dict['issue_date'])
    if 'due_date' in update_dict and update_dict['due_date']:
        update_dict['due_date'] = validate_business_datetime(update_dict['due_date'])
    
    # Check date logic
    issue_date = update_dict.get('issue_date', invoice.issue_date)
    due_date = update_dict.get('due_date', invoice.due_date)
    if issue_date and due_date and due_date < issue_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Due date cannot be earlier than issue date."
        )
    
    # Apply updates
    for key, value in update_dict.items():
        setattr(invoice, key, value)
    
    invoice.updated_at = datetime.now(UTC)
    
    await session.commit()
    
    # Refresh with relationships loaded
    await session.refresh(invoice)
    if invoice.property_id:
        await session.refresh(invoice, ["property"])
    if invoice.tenant_id:
        await session.refresh(invoice, ["tenant"])
    
    logger.info("Invoice %s updated by user %s", invoice_id, current_user.id)
    return InvoiceResponse(**build_invoice_response(invoice))


async def delete_invoice(
    invoice_id: int,
    session: AsyncSession,
    current_user: User
) -> None:
    """
    Deletes an invoice.

    Args:
        invoice_id: The ID of the invoice to delete.
        session: The database session.
        current_user: The user making the request.

    Raises:
        HTTPException: If invoice not found or user not authorized.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete invoices")
    
    # Get existing invoice
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    # Check ownership if landlord and invoice has a property
    if current_user.user_type == UserType.LANDLORD and invoice.property_id:
        await check_property_ownership(invoice.property_id, session, current_user)
    # Allow landlords to delete invoices with NULL property_id
    
    # Delete the invoice
    await session.delete(invoice)
    await session.commit()
    
    logger.info("Invoice %s deleted by user %s", invoice_id, current_user.id)


async def mark_invoice_paid(
    invoice_id: int,
    session: AsyncSession,
    current_user: User
) -> InvoiceResponse:
    """
    Marks an invoice as paid.

    Args:
        invoice_id: The ID of the invoice to mark as paid.
        session: The database session.
        current_user: The user making the request.

    Returns:
        The updated invoice.

    Raises:
        HTTPException: If invoice not found or user not authorized.
    """
    if current_user.user_type not in [UserType.ADMIN, UserType.LANDLORD]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update invoice status")
    
    # Get existing invoice
    invoice = await session.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    
    # Check ownership if landlord and invoice has a property
    if current_user.user_type == UserType.LANDLORD and invoice.property_id:
        await check_property_ownership(invoice.property_id, session, current_user)
    # TODO: For invoices with NULL property_id, add created_by_user_id field to Invoice model
    # to ensure landlords can only update invoices they created
    
    # Validate that invoice is not already paid
    if invoice.status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is already marked as paid"
        )
    
    # Update status
    invoice.status = PaymentStatus.PAID
    invoice.updated_at = datetime.now(UTC)
    
    await session.commit()
    
    # Refresh with relationships loaded
    await session.refresh(invoice)
    if invoice.property_id:
        await session.refresh(invoice, ["property"])
    if invoice.tenant_id:
        await session.refresh(invoice, ["tenant"])
    
    logger.info("Invoice %s marked as paid by user %s", invoice_id, current_user.id)
    return InvoiceResponse(**build_invoice_response(invoice))


# Export all service functions
__all__ = [
    "create_invoice",
    "get_invoices", 
    "get_invoice_by_id",
    "update_invoice",
    "delete_invoice",
    "mark_invoice_paid"
]
