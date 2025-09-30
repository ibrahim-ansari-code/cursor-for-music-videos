"""
QuickBooks Integration Validators

Comprehensive validation functions for QuickBooks data and operations.
"""

import re
import logging
from typing import Any, Optional
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


def validate_quickbooks_id(qb_id: str) -> bool:
    """
    Validates a QuickBooks ID format.

    QuickBooks IDs are typically numeric strings but can have various formats.
    This function ensures the ID is valid and safe to use.

    Args:
        qb_id: The QuickBooks ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not qb_id or not isinstance(qb_id, str):
        return False

    # Remove whitespace
    qb_id = qb_id.strip()

    # Check minimum length
    if len(qb_id) < 1 or len(qb_id) > 100:
        return False

    # QuickBooks IDs should be alphanumeric with possible hyphens/underscores
    # They should not contain special characters that could indicate injection attempts
    if not re.match(r'^[a-zA-Z0-9\-_]+$', qb_id):
        logger.warning(f"Invalid QuickBooks ID format: {qb_id}")
        return False

    return True


def validate_account_id(account_id: str) -> bool:
    """
    Validates a QuickBooks account ID.

    Account IDs in QuickBooks are typically numeric but stored as strings.

    Args:
        account_id: The account ID to validate

    Returns:
        True if valid, False otherwise
    """
    if not account_id or not isinstance(account_id, str):
        return False

    # Account IDs are typically numeric
    if not re.match(r'^\d+$', account_id.strip()):
        logger.warning(f"Invalid QuickBooks account ID: {account_id}")
        return False

    return True


def validate_invoice_data(invoice_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validates invoice data before syncing to QuickBooks.

    Args:
        invoice_data: Dictionary containing invoice information

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Required fields
    if not invoice_data.get("customer_id"):
        errors.append("Customer ID is required")
    elif not validate_quickbooks_id(invoice_data["customer_id"]):
        errors.append("Invalid customer ID format")

    # Validate amounts
    if "total_amount" in invoice_data:
        try:
            amount = float(invoice_data["total_amount"])
            if amount < 0:
                errors.append("Total amount cannot be negative")
            if amount > 999999999:
                errors.append("Total amount exceeds maximum allowed value")
        except (ValueError, TypeError):
            errors.append("Total amount must be a valid number")

    # Validate dates
    if "invoice_date" in invoice_data:
        if not validate_date(invoice_data["invoice_date"]):
            errors.append("Invalid invoice date format")

    if "due_date" in invoice_data:
        if not validate_date(invoice_data["due_date"]):
            errors.append("Invalid due date format")

    # Validate line items if present
    if "line_items" in invoice_data:
        if not isinstance(invoice_data["line_items"], list):
            errors.append("Line items must be a list")
        elif len(invoice_data["line_items"]) == 0:
            errors.append("At least one line item is required")
        else:
            for idx, item in enumerate(invoice_data["line_items"]):
                if not isinstance(item, dict):
                    errors.append(f"Line item {idx + 1} must be a dictionary")
                    continue
                if not item.get("description"):
                    errors.append(f"Line item {idx + 1} missing description")
                if "total_amount" in item:
                    try:
                        float(item["total_amount"])
                    except (ValueError, TypeError):
                        errors.append(f"Line item {idx + 1} has invalid amount")

    return len(errors) == 0, errors


def validate_expense_data(expense_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validates expense data before syncing to QuickBooks.

    Args:
        expense_data: Dictionary containing expense information

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Validate account IDs
    if "account_id" in expense_data:
        if not validate_account_id(str(expense_data["account_id"])):
            errors.append("Invalid account ID")

    if "bank_account_id" in expense_data:
        if not validate_account_id(str(expense_data["bank_account_id"])):
            errors.append("Invalid bank account ID")

    # Validate amounts
    if "total_amount" in expense_data:
        try:
            amount = float(expense_data["total_amount"])
            if amount < 0:
                errors.append("Total amount cannot be negative")
            if amount > 999999999:
                errors.append("Total amount exceeds maximum allowed value")
        except (ValueError, TypeError):
            errors.append("Total amount must be a valid number")

    # Validate expense date
    if "expense_date" in expense_data:
        if not validate_date(expense_data["expense_date"]):
            errors.append("Invalid expense date format")

    # Validate payment type
    valid_payment_types = ["cash", "check", "credit_card", "bank_transfer", "other"]
    if "payment_type" in expense_data:
        if expense_data["payment_type"] not in valid_payment_types:
            errors.append(f"Invalid payment type. Must be one of: {', '.join(valid_payment_types)}")

    return len(errors) == 0, errors


def validate_customer_data(customer_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validates customer/tenant data before syncing to QuickBooks.

    Args:
        customer_data: Dictionary containing customer information

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Name validation
    if not customer_data.get("first_name") and not customer_data.get("last_name"):
        errors.append("Customer must have at least a first or last name")

    # Email validation
    if "email" in customer_data and customer_data["email"]:
        if not validate_email(customer_data["email"]):
            errors.append("Invalid email address format")

    # Phone validation
    if "phone" in customer_data and customer_data["phone"]:
        if not validate_phone(customer_data["phone"]):
            errors.append("Invalid phone number format")

    # QuickBooks ID validation if present
    if "quickbooks_id" in customer_data and customer_data["quickbooks_id"]:
        if not validate_quickbooks_id(customer_data["quickbooks_id"]):
            errors.append("Invalid QuickBooks ID format")

    return len(errors) == 0, errors


def validate_date(date_value: Any) -> bool:
    """
    Validates a date value.

    Args:
        date_value: The date to validate (string, datetime, or date object)

    Returns:
        True if valid, False otherwise
    """
    if not date_value:
        return True  # Optional dates are allowed

    if isinstance(date_value, datetime):
        return True

    if isinstance(date_value, str):
        # Try common date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ'
        ]
        for fmt in formats:
            try:
                datetime.strptime(date_value, fmt)
                return True
            except ValueError:
                continue

    return False


def validate_email(email: str) -> bool:
    """
    Validates an email address format.

    Args:
        email: The email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email or not isinstance(email, str):
        return False

    # Basic email validation regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """
    Validates a phone number format.

    Args:
        phone: The phone number to validate

    Returns:
        True if valid, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False

    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone)

    # Check if it's a valid phone number (digits only, 10-15 digits)
    if not re.match(r'^\+?\d{10,15}$', cleaned):
        return False

    return True


def sanitize_for_quickbooks(text: str, max_length: int = 4000) -> str:
    """
    Sanitizes text for safe use in QuickBooks.

    Args:
        text: The text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1F\x7F]', '', text)

    # Replace problematic characters
    sanitized = sanitized.replace('\n', ' ').replace('\r', ' ')

    # Trim to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length-3] + "..."

    return sanitized.strip()