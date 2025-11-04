"""
Batch processing utilities for payment CSV imports.
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from sqlmodel import col
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.accounting.common import PaymentStatus
from Backend.config import Settings

settings = Settings()


async def bulk_create_payments(
    payments_data: List[Dict[str, Any]], 
    session: AsyncSession
) -> List[int]:
    """
    Bulk insert payments using SQLAlchemy Core for performance.
    
    Args:
        payments_data: List of payment dictionaries ready for insertion
        session: Database session
    
    Returns:
        List of created payment IDs
    """
    if not payments_data:
        return []
    
    # Use SQLAlchemy Core insert for bulk operation  
    stmt = insert(Payment).values(payments_data).returning(col(Payment.id))
    result = await session.execute(stmt)
    
    # Get all inserted IDs
    payment_ids = [row[0] for row in result.fetchall()]
    
    return payment_ids


def prepare_payment_batch(
    csv_payments: List[Any],
    properties: Dict[str, Any],
    tenants: Dict[str, Any],
    active_leases: Dict[str, Any],
    current_user_id: str,
    current_user_type: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Prepare a batch of payments for bulk insertion.
    
    Args:
        csv_payments: List of CSV payment data objects
        properties: Dictionary of property names to property objects
        tenants: Dictionary of tenant names to tenant objects
        active_leases: Dictionary mapping tenant IDs to active lease IDs
        current_user_id: ID of the current user
        current_user_type: Type of the current user
    
    Returns:
        Tuple of (valid_payments, errors)
    """
    valid_payments = []
    errors = []
    
    for row_idx, csv_payment in enumerate(csv_payments, 1):
        try:
            # Determine tenant and lease
            tenant_id = None
            lease_id = None
            
            # Try to find tenant by name
            if csv_payment.tenant_name:
                tenant_name_lower = csv_payment.tenant_name.lower()
                if tenant_name_lower in tenants:
                    tenant_id = tenants[tenant_name_lower].id
                else:
                    raise ValueError(f"Tenant '{csv_payment.tenant_name}' not found")
            
            # Try to find property and get tenant from there
            if csv_payment.property_name and not tenant_id:
                property_name_lower = csv_payment.property_name.lower()
                if property_name_lower in properties:
                    prop = properties[property_name_lower]
                    # Look for active lease on this property
                    for tid, lid in active_leases.items():
                        # Need to check if lease is for this property
                        # This will be handled in the service function
                        pass
                    
                    if not property_name_lower in properties:
                        raise ValueError(f"Property '{csv_payment.property_name}' not found")
                    else:
                        raise ValueError(f"Property '{csv_payment.property_name}' has no active leases")
            
            # Validate tenant has active lease
            if tenant_id:
                # Support both string and int keys for robustness
                key_str = str(tenant_id)
                if key_str in active_leases:
                    lease_id = active_leases[key_str]
                elif tenant_id in active_leases:  # Fallback if mapping still uses ints
                    lease_id = active_leases[tenant_id]
                else:
                    tenant_name = csv_payment.tenant_name or f"Tenant ID {tenant_id}"
                    raise ValueError(f"Tenant '{tenant_name}' has no active lease")
            
            if not lease_id:
                raise ValueError("Could not determine lease for payment. Tenant name or property name required.")
            
            # Parse payment date
            payment_date = parse_flexible_date(csv_payment.payment_date) if csv_payment.payment_date else datetime.now(timezone.utc)
            
            # Normalize payment method and status
            payment_method = normalize_payment_method(csv_payment.payment_method)
            status = normalize_payment_status(csv_payment.status)
            
            # Validate reduction amount
            reduction_amount = float(csv_payment.reduction_amount) if csv_payment.reduction_amount else None
            if reduction_amount is not None and reduction_amount > float(csv_payment.amount):
                raise ValueError("Reduction amount cannot be greater than payment amount")
            
            if reduction_amount and reduction_amount > 0 and not csv_payment.reduction_reason:
                raise ValueError("Reduction reason is required when reduction amount is provided")
            
            # Prepare payment data for bulk insert
            payment_data = {
                "lease_id": lease_id,
                "tenant_id": tenant_id,
                "amount": float(csv_payment.amount),
                "payment_date": payment_date,
                "payment_method": payment_method.value,
                "status": status.value,
                "transaction_reference": csv_payment.transaction_reference,
                "description": csv_payment.description,
                "reduction_amount": reduction_amount,
                "reduction_reason": csv_payment.reduction_reason if reduction_amount else None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            valid_payments.append(payment_data)
            
        except Exception as e:
            errors.append({
                "row_number": row_idx,
                "error_message": str(e)
            })
    
    return valid_payments, errors


def parse_flexible_date(date_str: str) -> datetime:
    """Parse date string in various formats."""
    from dateutil import parser as date_parser
    
    if not date_str:
        raise ValueError("Date is required")
    
    try:
        # Try ISO format first
        if 'T' in date_str or date_str.count('-') == 2 and date_str[4] == '-':
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        
        # Try common formats
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Fall back to dateutil parser
        return date_parser.parse(date_str, dayfirst=False)
    except Exception:
        raise ValueError(f"Invalid date format: {date_str}")


def normalize_payment_method(method_str: Optional[str]) -> PaymentMethod:
    """Normalize payment method string to enum."""
    if not method_str:
        return PaymentMethod.OTHER
    
    method_map = {
        'credit card': PaymentMethod.CREDIT_CARD,
        'debit card': PaymentMethod.DEBIT_CARD,
        'bank transfer': PaymentMethod.BANK_TRANSFER,
        'wire transfer': PaymentMethod.WIRE_TRANSFER,
        'direct deposit': PaymentMethod.DIRECT_DEPOSIT,
        'interac e-transfer': PaymentMethod.INTERAC_E_TRANSFER,
        'cash': PaymentMethod.CASH,
        'check': PaymentMethod.CHECK,
        'cheque': PaymentMethod.CHECK,
        'bank draft': PaymentMethod.BANK_DRAFT,
        'paypal': PaymentMethod.PAYPAL,
        'internal transfer': PaymentMethod.INTERNAL_TRANSFER,
        'other': PaymentMethod.OTHER
    }
    
    method_lower = method_str.lower().strip()
    return method_map.get(method_lower, PaymentMethod.OTHER)


def normalize_payment_status(status_str: Optional[str]) -> PaymentStatus:
    """Normalize payment status string to enum."""
    if not status_str:
        return PaymentStatus.PENDING
    
    status_map = {
        'pending': PaymentStatus.PENDING,
        'paid': PaymentStatus.PAID,
        'failed': PaymentStatus.VOID,
        'overdue': PaymentStatus.OVERDUE,
        'cancelled': PaymentStatus.CANCELLED,
        'completed': PaymentStatus.PAID,
        'processing': PaymentStatus.PENDING,
        'partially_paid': PaymentStatus.PARTIAL,
        'partial': PaymentStatus.PARTIAL,
        'refunded': PaymentStatus.REFUNDED,
        'draft': PaymentStatus.DRAFT,
        'void': PaymentStatus.VOID,
        'uncollectible': PaymentStatus.UNCOLLECTIBLE
    }
    
    status_lower = status_str.lower().strip()
    return status_map.get(status_lower, PaymentStatus.PENDING)


async def check_duplicate_payments(
    payments_data: List[Dict[str, Any]], 
    session: AsyncSession
) -> List[int]:
    """
    Check for duplicate payments based on key fields.
    
    Args:
        payments_data: List of payment data to check
        session: Database session
    
    Returns:
        List of indices of duplicate payments
    """
    duplicate_indices = []
    
    # For each payment, check if a similar one exists
    # We consider a payment duplicate if it has the same:
    # - lease_id, amount, payment_date, and transaction_reference
    for idx, payment in enumerate(payments_data):
        query = select(col(Payment.id)).where(
            col(Payment.lease_id) == payment['lease_id'],
            col(Payment.amount) == payment['amount'],
            col(Payment.payment_date) == payment['payment_date']
        )
        
        # Only check transaction_reference if it's not None
        if payment.get('transaction_reference'):
            query = query.where(col(Payment.transaction_reference) == payment['transaction_reference'])
        
        existing = await session.execute(query.limit(1))
        
        if existing.scalar():
            duplicate_indices.append(idx)
    
    return duplicate_indices