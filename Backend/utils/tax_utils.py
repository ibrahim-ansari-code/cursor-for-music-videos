"""Tax calculation and validation utilities for accounting operations."""
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)


def quantize_2dp(value: Any) -> Decimal:
    """
    Quantize a Decimal value to two decimal places using ROUND_HALF_UP.
    
    Args:
        value: Value to quantize (can be Decimal, str, int, float)
        
    Returns:
        Decimal value quantized to 2 decimal places
    """
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def validate_tax_rate(tax_rate: Any) -> Decimal:
    """
    Validates and converts a tax rate to Decimal.
    
    Args:
        tax_rate: Tax rate value to validate
        
    Returns:
        Validated tax rate as Decimal
        
    Raises:
        ValueError: If tax rate is invalid or out of bounds
    """
    try:
        tax_rate_decimal = Decimal(str(tax_rate))
    except (ValueError, TypeError, InvalidOperation) as e:
        raise ValueError(f"Tax rate must be a valid number, got: '{tax_rate}'") from e
    
    if not (Decimal('0.00') <= tax_rate_decimal <= Decimal('100.00')):
        raise ValueError(f"Tax rate must be between 0 and 100, got: {tax_rate_decimal}")
    
    return tax_rate_decimal


def validate_tax_amount(tax_amount: Any) -> Decimal:
    """
    Validates and converts a tax amount to Decimal.
    
    Args:
        tax_amount: Tax amount value to validate
        
    Returns:
        Validated tax amount as Decimal
        
    Raises:
        ValueError: If tax amount is invalid or negative
    """
    try:
        tax_amount_decimal = quantize_2dp(tax_amount)
    except (ValueError, TypeError, InvalidOperation) as e:
        raise ValueError(f"Tax amount must be a valid number, got: '{tax_amount}'") from e
    
    if tax_amount_decimal < Decimal('0.00'):
        raise ValueError(f"Tax amount must be non-negative, got: {tax_amount_decimal}")
    
    return tax_amount_decimal


def calculate_tax_amount(subtotal: Decimal, tax_rate: Decimal) -> Decimal:
    """
    Calculates tax amount from subtotal and tax rate.
    
    Args:
        subtotal: Subtotal amount
        tax_rate: Tax rate as percentage (0-100)
        
    Returns:
        Calculated tax amount, quantized to 2 decimal places
    """
    return quantize_2dp((subtotal * tax_rate) / Decimal("100"))


def validate_and_process_tax_details(tax_details_list: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], Decimal]:
    """
    Validates and processes tax details from LLM-parsed receipt data.

    Validates that tax_rate and tax_amount are valid numeric values within acceptable ranges:
    - Tax amounts must be non-negative decimal values
    - Tax rates must be between 0.00 and 100.00 (percentage)
    - Tax names must be non-empty strings

    Invalid items are logged and skipped rather than causing the entire process to fail.

    Args:
        tax_details_list: List of tax detail items from LLM parsing

    Returns:
        Tuple of (validated_tax_details, total_tax_from_details)
    """
    validated_tax_details = []
    total_tax_from_details = Decimal('0.00')

    if not tax_details_list or not isinstance(tax_details_list, list):
        return validated_tax_details, total_tax_from_details

    for tax_item in tax_details_list:
        if not isinstance(tax_item, dict) or not all(key in tax_item for key in ['tax_name', 'tax_rate', 'tax_amount']):
            logger.warning("Tax detail item missing required fields: %s", tax_item)
            continue

        try:
            # Validate tax rate
            tax_rate_raw = tax_item.get('tax_rate', '0.00')
            tax_rate_decimal = validate_tax_rate(tax_rate_raw)
            
            # Validate tax amount
            tax_amount_raw = tax_item.get('tax_amount', '0.00')
            tax_amount = validate_tax_amount(tax_amount_raw)

            # Validate tax name is not empty
            tax_name = str(tax_item.get('tax_name', 'Tax')).strip()
            if not tax_name:
                tax_name = 'Tax'

            # Add to totals and validated list
            total_tax_from_details += tax_amount

            validated_tax_details.append({
                'tax_name': tax_name,
                'tax_rate': quantize_2dp(tax_rate_decimal),
                'tax_amount': tax_amount
            })

        except ValueError as e:
            logger.warning("Skipping invalid tax item: %s - Error: %s", tax_item, str(e))
            continue
        except (TypeError, ArithmeticError) as e:
            logger.warning("Skipping invalid tax item with values: %s - Error: %s", tax_item, str(e))
            continue

    return validated_tax_details, total_tax_from_details


def calculate_fallback_tax_amount(total: Decimal, subtotal: Decimal, total_tax_from_details: Decimal) -> Decimal:
    """
    Calculates tax amount using fallback method when tax details are not available.

    Args:
        total: Total amount from receipt
        subtotal: Subtotal amount from receipt
        total_tax_from_details: Total tax calculated from individual tax line items

    Returns:
        Calculated tax amount
    """
    if total_tax_from_details > Decimal('0.00'):
        return total_tax_from_details
    else:
        return quantize_2dp(max(Decimal('0.00'), total - subtotal))


def finalize_parsed_receipt_data(parsed_data_dict: dict[str, Any], subtotal: Decimal, total: Decimal) -> dict[str, Any]:
    """
    Finalizes the parsed receipt data by processing tax details and ensuring all amounts are properly quantized.

    Args:
        parsed_data_dict: Dictionary containing parsed receipt data
        subtotal: Subtotal amount from receipt
        total: Total amount from receipt

    Returns:
        Updated parsed data dictionary with processed tax details
    """
    # Process tax_details if provided by LLM
    tax_details_list = parsed_data_dict.get('tax_details', [])
    validated_tax_details, total_tax_from_details = validate_and_process_tax_details(
        tax_details_list)

    # Update tax details in the dictionary
    parsed_data_dict['tax_details'] = validated_tax_details

    # Calculate total_tax_amount: use sum from tax_details if available, otherwise fallback to total - subtotal
    calculated_tax_amount = calculate_fallback_tax_amount(
        total, subtotal, total_tax_from_details)

    # Ensure total_amount has a default if missing
    parsed_data_dict.setdefault('total_amount', quantize_2dp(total))

    # Use setdefault after quantizing to avoid double quantization
    parsed_data_dict.setdefault('total_tax_amount', calculated_tax_amount)

    return parsed_data_dict 