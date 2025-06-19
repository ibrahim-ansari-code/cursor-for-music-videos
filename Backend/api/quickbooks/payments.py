import asyncio
import logging
from datetime import datetime, UTC
from decimal import Decimal
from typing import Any


from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, col

from Backend.models.user import User
from Backend.models.tenant import Tenant
from Backend.models.accounting.common import IntegrationType
from Backend.models.accounting.integration import IntegrationStatus
from Backend.models.accounting.payment import Payment, PaymentMethod, PaymentStatus
from Backend.models.lease import Lease
from .utils import (
    get_user_integration,
    get_apideck_client,
    normalize_qb_datetime,
    resolve_tenant_and_lease_from_qb_object,
    is_already_synced,
)

logger = logging.getLogger(__name__)


def _build_payment(qb_payment: Any, lease: Lease, tenant: Tenant) -> Payment:
    """Constructs a Brikli Payment object from a QuickBooks payment record."""
    qb_payment_id = getattr(qb_payment, 'id')
    return Payment(
        amount=Decimal(str(getattr(qb_payment, 'total_amount', 0))),
        payment_date=normalize_qb_datetime(getattr(qb_payment, 'transaction_date', None)),
        status=PaymentStatus.PAID,
        description=f"Payment synced from QuickBooks. QB ID: {qb_payment_id}",
        payment_method=PaymentMethod.OTHER,
        lease_id=lease.id,
        tenant_id=tenant.id,
        quickbooks_id=qb_payment_id,
        last_synced_at=datetime.now(UTC)
    )


async def _pull_payments_from_quickbooks(user: User, session: AsyncSession) -> dict[str, Any]:
    """
    Synchronizes recent payments from QuickBooks into the Brikli database for the given user.
    
    Checks for an active QuickBooks integration, retrieves payments via Apideck, and for each new payment, associates it with the corresponding Brikli tenant and active lease before creating a new payment record. Returns a summary with the number of payments synced and any errors encountered.
    
    Returns:
        A dictionary containing the count of newly synced payments under 'synced_count' and a list of error messages under 'errors'.
    """
    integration = await get_user_integration(user, session, IntegrationType.QUICKBOOKS)
    if not integration or integration.status != IntegrationStatus.CONNECTED or not integration.apideck_consumer_id:
        logger.warning("QuickBooks not connected for user %s. Skipping payment sync.", user.id)
        return {"synced_count": 0, "errors": ["QuickBooks connection not found or inactive."]}
    
    apideck_client = get_apideck_client(integration.apideck_consumer_id)
    new_payments_count = 0
    errors = []

    try:
        # Fetch payments from Apideck in a separate thread
        payments_response = await asyncio.to_thread(apideck_client.accounting.payments.list, service_id="quickbooks")
        
        if not (payments_response and hasattr(payments_response, '__iter__')):
            return {"synced_count": 0, "errors": errors}

        for page in payments_response:
            if not hasattr(page, 'data'):
                continue
            
            qb_payments = getattr(page, 'data', [])
            if not qb_payments:
                continue
            
            # --- N+1 Query Fix ---
            # 1. Get all QB payment IDs from the current page
            qb_payment_ids = [
                getattr(payment, 'id', None) for payment in qb_payments if getattr(payment, 'id', None)
            ]
            
            # 2. Pre-fetch all existing payment IDs from the database in a single query
            existing_payments_query = select(Payment.quickbooks_id).where(
                col(Payment.quickbooks_id).in_(qb_payment_ids)
            )
            existing_ids_result = await session.execute(existing_payments_query)
            existing_ids = {row[0] for row in existing_ids_result}
            # --- End N+1 Query Fix ---
            
            for qb_payment in qb_payments:
                qb_payment_id = getattr(qb_payment, 'id', None)
                if not qb_payment_id:
                    continue
                    
                # 3. Check against the pre-fetched set instead of a DB call per item
                if qb_payment_id in existing_ids:
                    continue
                    
                tenant, lease = await resolve_tenant_and_lease_from_qb_object(session, qb_payment)
                
                if not (tenant and lease):
                    continue
                    
                new_payment = _build_payment(qb_payment, lease, tenant)
                session.add(new_payment)
                new_payments_count += 1
    
    except Exception:
        logger.exception("Error pulling payments from QuickBooks for user %s", user.id)
        errors.append("An unexpected error occurred during payment sync.")

    if new_payments_count > 0:
        await session.commit()
    
    return {"synced_count": new_payments_count, "errors": errors}