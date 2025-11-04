"""
Batch processing utilities for invoice CSV imports.
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from sqlmodel import col
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.config import Settings

settings = Settings()


async def bulk_create_invoices(
    invoices_data: List[Dict[str, Any]], 
    session: AsyncSession
) -> List[int]:
    """
    Bulk insert invoices using SQLAlchemy Core for performance.
    
    Args:
        invoices_data: List of invoice dictionaries ready for insertion
        session: Database session
    
    Returns:
        List of created invoice IDs
    """
    if not invoices_data:
        return []
    
    # Use SQLAlchemy Core insert for bulk operation  
    stmt = insert(Invoice).values(invoices_data).returning(col(Invoice.id))
    result = await session.execute(stmt)
    
    # Get all inserted IDs
    invoice_ids = [row[0] for row in result.fetchall()]
    
    return invoice_ids


def prepare_invoice_batch(
    csv_invoices: List[Any],
    properties: Dict[str, Any],
    tenants: Dict[str, Any],
    current_user_id: str,
    current_user_type: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Prepare a batch of invoices for bulk insertion.
    
    Args:
        csv_invoices: List of CSV invoice data objects
        properties: Dictionary of property names to property objects
        tenants: Dictionary of tenant names to tenant objects
        current_user_id: ID of the current user
        current_user_type: Type of the current user
    
    Returns:
        Tuple of (valid_invoices, errors)
    """
    valid_invoices = []
    errors = []
    
    for row_idx, csv_invoice in enumerate(csv_invoices, 1):
        try:
            # Determine property_id
            property_id = None
            if csv_invoice.property_name:
                property_name_lower = csv_invoice.property_name.lower()
                if property_name_lower in properties:
                    property_id = properties[property_name_lower].id
                else:
                    raise ValueError(f"Property '{csv_invoice.property_name}' not found")
            
            if not property_id:
                # If no property specified and landlord has only one property, use it
                if current_user_type == "LANDLORD" and len(properties) == 1:
                    property_id = list(properties.values())[0].id
                else:
                    if current_user_type == "ADMIN":
                        raise ValueError("Property name is required for admin imports")
                    else:
                        raise ValueError("Property name is required or account must have a single property for auto-assignment")
            
            # Determine tenant_id if tenant_name is provided
            tenant_id = None
            if csv_invoice.tenant_name:
                tenant_name_lower = csv_invoice.tenant_name.lower()
                if tenant_name_lower in tenants:
                    tenant_id = tenants[tenant_name_lower].id
                else:
                    raise ValueError(f"Tenant '{csv_invoice.tenant_name}' not found")
            
            # Parse dates
            issue_date = parse_flexible_date(csv_invoice.issue_date)
            due_date = parse_flexible_date(csv_invoice.due_date)
            
            # Validate due date is not before issue date
            if due_date < issue_date:
                raise ValueError("Due date cannot be earlier than issue date")
            
            # Parse status
            status = normalize_payment_status(csv_invoice.status)
            
            # Prepare invoice data for bulk insert
            invoice_data = {
                "invoice_number": csv_invoice.invoice_number,
                "amount": float(csv_invoice.amount),
                "description": csv_invoice.description,
                "issue_date": issue_date,
                "due_date": due_date,
                "status": status.value,
                "property_id": property_id,
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            valid_invoices.append(invoice_data)
            
        except Exception as e:
            errors.append({
                "row_number": row_idx,
                "error_message": str(e)
            })
    
    return valid_invoices, errors


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


async def check_duplicate_invoices(
    invoices_data: List[Dict[str, Any]], 
    session: AsyncSession
) -> List[int]:
    """
    Check for duplicate invoices based on invoice number.
    
    Args:
        invoices_data: List of invoice data to check
        session: Database session
    
    Returns:
        List of indices of duplicate invoices
    """
    duplicate_indices = []
    
    # Check for duplicates by invoice number (must be unique)
    for idx, invoice in enumerate(invoices_data):
        existing = await session.execute(
            select(col(Invoice.id)).where(
                col(Invoice.invoice_number) == invoice['invoice_number']
            ).limit(1)
        )
        
        if existing.scalar():
            duplicate_indices.append(idx)
    
    return duplicate_indices