"""Payment Method webhook event handlers"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from Backend.models.tenant_payment_method import TenantPaymentMethod
from Backend.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)


async def handle_payment_method_attached(
    payment_method: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle payment method attached to customer."""
    pm_id = payment_method.get("id")
    customer_id = payment_method.get("customer")
    
    if not pm_id or not customer_id:
        return
    
    # Check if we have this payment method
    existing = await session.scalar(
        select(TenantPaymentMethod).where(
            col(TenantPaymentMethod.stripe_payment_method_id) == pm_id
        )
    )
    
    if existing:
        logger.debug(f"Payment method {pm_id} already exists")
        return
    
    logger.info(
        f"Payment method attached | "
        f"pm_id={pm_id} | "
        f"customer_id={customer_id}"
    )
    
    # Note: Payment method records are created when SetupIntent succeeds
    # This event is just for logging/monitoring


async def handle_payment_method_updated(
    payment_method: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle payment method updates (card expiry, billing details, etc.)."""
    pm_id = payment_method.get("id")
    
    if not pm_id:
        return
    
    pm_record = await session.scalar(
        select(TenantPaymentMethod).where(
            col(TenantPaymentMethod.stripe_payment_method_id) == pm_id
        )
    )
    
    if not pm_record:
        return
    
    # Update card expiry if changed
    pm_type = payment_method.get("type")
    if pm_type == "card":
        card_data = payment_method.get("card", {})
        exp_month = card_data.get("exp_month")
        exp_year = card_data.get("exp_year")
        
        if exp_month and exp_year:
            pm_record.card_exp_month = str(exp_month)
            pm_record.card_exp_year = str(exp_year)
            pm_record.updated_at = utc_now()
            
            session.add(pm_record)
            await session.commit()
            
            logger.info(
                f"Updated card expiry | "
                f"pm_id={pm_id} | "
                f"exp={exp_month}/{exp_year}"
            )


async def handle_payment_method_detached(
    payment_method: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle payment method detached from customer."""
    pm_id = payment_method.get("id")
    
    if not pm_id:
        return
    
    pm_record = await session.scalar(
        select(TenantPaymentMethod).where(
            col(TenantPaymentMethod.stripe_payment_method_id) == pm_id
        )
    )
    
    if not pm_record:
        return
    
    # Mark as detached (soft delete - keep for audit trail)
    pm_record.is_default = False
    pm_record.updated_at = utc_now()
    
    session.add(pm_record)
    await session.commit()
    
    logger.info(f"Payment method detached | pm_id={pm_id}")


async def handle_setup_intent_succeeded(
    setup_intent: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Handle successful SetupIntent (payment method saved)."""
    si_id = setup_intent.get("id")
    pm_id = setup_intent.get("payment_method")
    customer_id = setup_intent.get("customer")
    
    if not all([si_id, pm_id, customer_id]):
        return
    
    logger.info(
        f"SetupIntent succeeded | "
        f"si_id={si_id} | "
        f"pm_id={pm_id} | "
        f"customer_id={customer_id}"
    )
    
    # Note: Payment method records are created in service.py when SetupIntent succeeds
    # This event is just for logging/monitoring

