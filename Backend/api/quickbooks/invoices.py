import asyncio
import logging
from datetime import datetime, UTC
from typing import Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from Backend.models.user import User
from Backend.models.tenant import Tenant
from Backend.models.accounting.integration import IntegrationStatus, IntegrationType
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.lease import Lease
from .utils import (
    get_user_integration, 
    get_apideck_client, 
    normalize_qb_datetime, 
    resolve_tenant_and_lease_from_qb_object
)

logger = logging.getLogger(__name__)

STATUS_MAPPING = {
    "draft": PaymentStatus.DRAFT,
    "open": PaymentStatus.PENDING,
    "paid": PaymentStatus.PAID,
    "void": PaymentStatus.VOID,
    "uncollectible": PaymentStatus.UNCOLLECTIBLE,
    "deleted": PaymentStatus.VOID,
}


async def _is_duplicate_invoice(session: AsyncSession, qb_invoice_id: str) -> bool:
    """Checks if a QuickBooks invoice has already been synced."""
    existing_invoice_query = select(Invoice).where(Invoice.quickbooks_id == qb_invoice_id)
    return await session.scalar(existing_invoice_query) is not None


def _build_brikli_invoice(qb_invoice: Any, lease: Lease, tenant: Tenant) -> Invoice:
    """Constructs a Brikli Invoice object from a QuickBooks invoice record."""
    qb_invoice_id = getattr(qb_invoice, 'id', None)
    if not qb_invoice_id:
        raise ValueError("QuickBooks invoice missing required 'id' field")
    
    raw_status = getattr(qb_invoice, 'status', None) or 'draft'
    invoice_status = STATUS_MAPPING.get(raw_status.lower(), PaymentStatus.DRAFT)

    return Invoice(
        invoice_number=getattr(qb_invoice, 'number', f"QB-{qb_invoice_id}"),
        amount=Decimal(str(getattr(qb_invoice, 'total', 0))),
        description=f"Invoice synced from QuickBooks. QB ID: {qb_invoice_id}",
        issue_date=normalize_qb_datetime(getattr(qb_invoice, 'invoice_date', None)),
        due_date=normalize_qb_datetime(getattr(qb_invoice, 'due_date', None)),
        status=invoice_status,
        property_id=lease.property_id,
        tenant_id=tenant.id,
        quickbooks_id=qb_invoice_id,
        last_synced_at=datetime.now(UTC)
    )


async def _process_single_invoice(session: AsyncSession, qb_invoice: Any) -> bool:
    """
    Processes a single QuickBooks invoice: checks for duplicates, resolves tenant/lease, 
    creates invoice record, and adds to session.
    
    Returns:
        True if invoice was successfully processed and added to session, False otherwise.
    """
    qb_invoice_id = getattr(qb_invoice, 'id', None)
    if not qb_invoice_id:
        return False
        
    # Skip if already synced
    if await _is_duplicate_invoice(session, qb_invoice_id):
        return False
        
    # Resolve tenant and lease using utility function
    tenant, lease = await resolve_tenant_and_lease_from_qb_object(session, qb_invoice)
    
    if not (tenant and lease):
        return False
        
    # Create and add invoice to session
    try:
        new_brikli_invoice = _build_brikli_invoice(qb_invoice, lease, tenant)
        session.add(new_brikli_invoice)
        return True
    except ValueError as e:
        logger.warning("Skipping invalid invoice: %s", str(e))
        return False


async def _process_invoices_batch(session: AsyncSession, invoices_response: Any) -> int:
    """
    Processes a batch of invoices from QuickBooks API response.
    
    Returns:
        Number of new invoices successfully processed and added to session.
    """
    new_invoices_count = 0
    
    if not (invoices_response and hasattr(invoices_response, '__iter__')):
        return new_invoices_count

    for page in invoices_response:
        if not hasattr(page, 'data'):
            continue

        for qb_invoice in getattr(page, 'data', []):
            if await _process_single_invoice(session, qb_invoice):
                new_invoices_count += 1
    
    return new_invoices_count


async def _pull_invoices_from_quickbooks(user: User, session: AsyncSession) -> dict[str, Any]:
    """
    Synchronizes recent invoices from QuickBooks to the local database for the specified user.
    
    Fetches invoices from QuickBooks using the user's integration, skipping those already present in the database. Associates each new invoice with the corresponding tenant and active lease, mapping QuickBooks status to the internal payment status. Returns a summary containing the number of invoices synced and any errors encountered.
    
    Returns:
        A dictionary with the count of synced invoices under 'synced_count' and a list of error messages under 'errors'.
    """
    integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)
    if not integration or integration.status != IntegrationStatus.CONNECTED or not integration.apideck_consumer_id:
        logger.warning("QuickBooks not connected for user %s. Skipping invoice sync.", user.id)
        return {"synced_count": 0, "errors": ["QuickBooks connection not found or inactive."]}

    apideck_client = get_apideck_client(integration.apideck_consumer_id)
    errors = []

    try:
        # Fetch invoices from QuickBooks
        invoices_response = await asyncio.to_thread(
            apideck_client.accounting.invoices.list, 
            service_id="quickbooks"
        )
        
        # Process the batch of invoices
        new_invoices_count = await _process_invoices_batch(session, invoices_response)
    
    except Exception as e:
        logger.error(f"Error pulling invoices from QuickBooks for user {user.id}: {e}", exc_info=True)
        errors.append(f"An unexpected error occurred: {str(e)}")
        new_invoices_count = 0

    # Commit changes and update sync timestamp if any invoices were processed
    if new_invoices_count > 0:
        integration.last_synced_at = datetime.now(UTC)
        await session.commit()
        logger.info(f"Synced {new_invoices_count} invoices from QuickBooks for user {user.id}")
    
    return {"synced_count": new_invoices_count, "errors": errors}
