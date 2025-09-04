"""
Provincial tax rates utility for Canada

This module provides tax rate constants and helper functions for
determining appropriate tax rates based on provincial location.
"""

from typing import Dict, Tuple, Optional, Any
from decimal import Decimal

# Provincial tax rates as of 2024
# Format: Province Code -> (Tax Name, Tax Rate as Decimal)
PROVINCIAL_TAX_RATES: Dict[str, Tuple[str, Decimal]] = {
    # Harmonized Sales Tax (HST) provinces
    "ON": ("HST", Decimal("13.00")),  # Ontario
    "NS": ("HST", Decimal("15.00")),  # Nova Scotia
    "NB": ("HST", Decimal("15.00")),  # New Brunswick
    "PE": ("HST", Decimal("15.00")),  # Prince Edward Island
    "NL": ("HST", Decimal("15.00")),  # Newfoundland and Labrador
    
    # GST + PST provinces  
    "BC": ("GST+PST", Decimal("12.00")),  # British Columbia (5% GST + 7% PST)
    "MB": ("GST+PST", Decimal("12.00")),  # Manitoba (5% GST + 7% PST)
    "SK": ("GST+PST", Decimal("11.00")),  # Saskatchewan (5% GST + 6% PST)
    
    # GST + QST
    "QC": ("GST+QST", Decimal("14.975")),  # Quebec (5% GST + 9.975% QST)
    
    # GST only
    "AB": ("GST", Decimal("5.00")),  # Alberta
    "YT": ("GST", Decimal("5.00")),  # Yukon
    "NT": ("GST", Decimal("5.00")),  # Northwest Territories  
    "NU": ("GST", Decimal("5.00")),  # Nunavut
}

# Alternative province name mappings for flexibility
PROVINCE_NAME_ALIASES: Dict[str, str] = {
    "ONTARIO": "ON",
    "BRITISH COLUMBIA": "BC", 
    "ALBERTA": "AB",
    "SASKATCHEWAN": "SK",
    "MANITOBA": "MB",
    "QUEBEC": "QC",
    "NEW BRUNSWICK": "NB",
    "NOVA SCOTIA": "NS",
    "PRINCE EDWARD ISLAND": "PE",
    "NEWFOUNDLAND AND LABRADOR": "NL",
    "YUKON": "YT",
    "NORTHWEST TERRITORIES": "NT",
    "NUNAVUT": "NU",
}


def get_provincial_tax_rate(province: str) -> Optional[Tuple[str, Decimal]]:
    """
    Get the tax rate for a given province.
    
    Args:
        province: Province code (e.g., 'ON', 'BC') or full name (case-insensitive)
        
    Returns:
        Tuple of (tax_name, tax_rate) or None if province not found
        
    Examples:
        >>> get_provincial_tax_rate('ON')
        ('HST', Decimal('13.00'))
        >>> get_provincial_tax_rate('ontario')
        ('HST', Decimal('13.00'))
        >>> get_provincial_tax_rate('BC')
        ('GST+PST', Decimal('12.00'))
    """
    if not province:
        return None
        
    # Normalize input
    province_upper = province.strip().upper()
    
    # Check direct province code match
    if province_upper in PROVINCIAL_TAX_RATES:
        return PROVINCIAL_TAX_RATES[province_upper]
    
    # Check alias mapping
    if province_upper in PROVINCE_NAME_ALIASES:
        province_code = PROVINCE_NAME_ALIASES[province_upper]
        return PROVINCIAL_TAX_RATES[province_code]
    
    return None


def get_default_tax_rate() -> Tuple[str, Decimal]:
    """
    Get the default tax rate when province is unknown.
    Uses Ontario HST as the default.
    
    Returns:
        Tuple of (tax_name, tax_rate)
    """
    return ("HST", Decimal("13.00"))


def is_valid_tax_rate(rate: Decimal) -> bool:
    """
    Validate if a tax rate is within reasonable bounds.
    
    Args:
        rate: Tax rate as decimal (percentage)
        
    Returns:
        True if rate is between 0 and 100%, False otherwise
    """
    return Decimal("0") <= rate <= Decimal("100.00")


def calculate_tax_amount(subtotal: Decimal, tax_rate: Decimal) -> Decimal:
    """
    Calculate tax amount from subtotal and tax rate.
    
    Args:
        subtotal: Pre-tax amount
        tax_rate: Tax rate as percentage (e.g., 13.00 for 13%)
        
    Returns:
        Tax amount rounded to 2 decimal places
    """
    if subtotal < 0 or tax_rate < 0:
        return Decimal("0.00")
        
    # Convert percentage to decimal and calculate
    tax_decimal = tax_rate / Decimal("100")
    tax_amount = subtotal * tax_decimal
    
    # Round to 2 decimal places
    return tax_amount.quantize(Decimal("0.01"))


def get_all_provinces_with_rates() -> Dict[str, Tuple[str, Decimal]]:
    """
    Get all available provinces and their tax rates.
    
    Returns:
        Dictionary mapping province codes to (tax_name, tax_rate) tuples
    """
    return PROVINCIAL_TAX_RATES.copy()


# Helper function for API responses
def format_tax_rate_response(province: str) -> Optional[Dict[str, Any]]:
    """
    Format provincial tax rate as API response dictionary.
    
    Args:
        province: Province code or name
        
    Returns:
        Dictionary with tax details or None if province not found
    """
    tax_data = get_provincial_tax_rate(province)
    if not tax_data:
        return None
        
    tax_name, tax_rate = tax_data
    return {
        "tax_name": tax_name,
        "tax_rate": float(tax_rate),
        "province": province.upper(),
        "source": "provincial_default"
    }