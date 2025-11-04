"""
Batch processing utilities for expense CSV imports.
"""
from typing import List, Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select
from Backend.models.accounting.expense import Expense
from Backend.models.accounting.payment import PaymentMethod
from Backend.config import Settings
from sqlmodel import col

settings = Settings()


async def bulk_create_expenses(
    expenses_data: List[Dict[str, Any]], 
    session: AsyncSession
) -> List[int]:
    """
    Bulk insert expenses using SQLAlchemy Core for performance.
    
    Args:
        expenses_data: List of expense dictionaries ready for insertion
        session: Database session
    
    Returns:
        List of created expense IDs
    """
    if not expenses_data:
        return []
    
    # Use SQLAlchemy Core insert for bulk operation  
    stmt = insert(Expense).values(expenses_data).returning(col(Expense.id))
    result = await session.execute(stmt)
    
    # Get all inserted IDs
    expense_ids = [row[0] for row in result.fetchall()]
    
    return expense_ids


def prepare_expense_batch(
    csv_expenses: List[Any],
    properties: Dict[str, Any],
    current_user_id: str,
    current_user_type: str
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Prepare a batch of expenses for bulk insertion.
    
    Args:
        csv_expenses: List of CSV expense data objects
        properties: Dictionary of property names to property objects
        current_user_id: ID of the current user
        current_user_type: Type of the current user
    
    Returns:
        Tuple of (valid_expenses, errors)
    """
    valid_expenses = []
    errors = []
    
    for row_idx, csv_expense in enumerate(csv_expenses, 1):
        try:
            # Determine property_id
            property_id = None
            if csv_expense.property_name:
                property_name_lower = csv_expense.property_name.lower()
                if property_name_lower in properties:
                    property_id = properties[property_name_lower].id
                else:
                    raise ValueError(f"Property '{csv_expense.property_name}' not found")
            
            if not property_id:
                # If no property specified and landlord has only one property, use it
                if current_user_type == "LANDLORD" and len(properties) == 1:
                    property_id = list(properties.values())[0].id
                else:
                    if current_user_type == "ADMIN":
                        raise ValueError("Property name is required for admin imports")
                    else:
                        raise ValueError("Property name is required or account must have a single property for auto-assignment")
            
            # Parse and validate expense date
            expense_date = parse_flexible_date(csv_expense.expense_date)
            
            # Normalize payment method
            payment_method = normalize_payment_method(csv_expense.payment_method)
            
            # Prepare expense data for bulk insert
            expense_data = {
                "property_id": property_id,
                "category": csv_expense.category,
                "description": csv_expense.description or "",
                "expense_date": expense_date,
                "subtotal_amount": float(csv_expense.subtotal_amount),
                "total_tax_amount": float(csv_expense.total_tax_amount or Decimal('0.00')),
                "payment_method": payment_method.value,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            valid_expenses.append(expense_data)
            
        except Exception as e:
            errors.append({
                "row_number": row_idx,
                "error_message": str(e)
            })
    
    return valid_expenses, errors


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


async def check_duplicate_expenses(
    expenses_data: List[Dict[str, Any]], 
    session: AsyncSession
) -> List[int]:
    """
    Check for duplicate expenses based on key fields.
    
    Args:
        expenses_data: List of expense data to check
        session: Database session
    
    Returns:
        List of indices of duplicate expenses
    """
    duplicate_indices = []
    
    # For each expense, check if a similar one exists
    # We consider an expense duplicate if it has the same:
    # - property_id, category, amount, and date
    for idx, expense in enumerate(expenses_data):
        existing = await session.execute(
            select(col(Expense.id)).where(
                col(Expense.property_id) == expense['property_id'],
                col(Expense.category) == expense['category'],
                col(Expense.subtotal_amount) == expense['subtotal_amount'],
                col(Expense.expense_date) == expense['expense_date']
            ).limit(1)
        )
        
        if existing.scalar():
            duplicate_indices.append(idx)
    
    return duplicate_indices