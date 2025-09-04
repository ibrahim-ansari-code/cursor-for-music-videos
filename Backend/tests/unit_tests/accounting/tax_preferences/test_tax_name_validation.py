"""
Unit tests for Canadian tax name validation.

Tests the validate_canadian_tax_name function and its integration
with tax preference schemas.
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from Backend.utils.tax_utils import validate_canadian_tax_name
from Backend.api.accounting.tax_preferences.schemas import TaxPreferenceCreate
from Backend.models.accounting.invoice_tax_detail import InvoiceTaxDetailCreate
from Backend.models.accounting.expense import ExpenseTaxDetailCreate

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestCanadianTaxNameValidation:
    """Test cases for Canadian tax name validation function."""

    def test_valid_single_taxes(self):
        """Test validation of valid single tax types."""
        valid_taxes = ['HST', 'GST', 'PST', 'QST']
        
        for tax in valid_taxes:
            # Test uppercase
            assert validate_canadian_tax_name(tax) == tax
            
            # Test lowercase (should be normalized to uppercase)
            assert validate_canadian_tax_name(tax.lower()) == tax
            
            # Test mixed case
            assert validate_canadian_tax_name(tax.title()) == tax

    def test_valid_combined_taxes(self):
        """Test validation of valid combined tax types."""
        valid_combined = [
            ('GST+PST', 'GST+PST'),
            ('GST+QST', 'GST+QST'),
            ('gst+pst', 'GST+PST'),  # lowercase normalization
            ('Gst+Pst', 'GST+PST'),  # mixed case normalization
        ]
        
        for input_tax, expected in valid_combined:
            assert validate_canadian_tax_name(input_tax) == expected

    def test_tax_name_variations_normalization(self):
        """Test normalization of common tax name variations."""
        variations = [
            ('GST/PST', 'GST+PST'),
            ('GST & PST', 'GST+PST'),
            ('GST AND PST', 'GST+PST'),
            ('GST_PST', 'GST+PST'),
            ('gst/pst', 'GST+PST'),  # lowercase
            ('gst & pst', 'GST+PST'),
            ('GST/QST', 'GST+QST'),
            ('GST & QST', 'GST+QST'),
            ('GST AND QST', 'GST+QST'),
            ('GST_QST', 'GST+QST'),
        ]
        
        for variation, expected in variations:
            assert validate_canadian_tax_name(variation) == expected

    def test_custom_tax_names_allowed(self):
        """Test that reasonable custom tax names are allowed."""
        custom_taxes = [
            'MUNICIPAL TAX',
            'LUXURY TAX',
            'EXCISE TAX',
            'TAX-FREE',
            'VAT',
            'SALES TAX',
            'TAX123',
        ]
        
        for tax in custom_taxes:
            # Should not raise an exception and normalize to uppercase
            result = validate_canadian_tax_name(tax)
            assert result == tax.upper()

    def test_invalid_tax_names(self):
        """Test rejection of invalid tax name formats."""
        invalid_taxes = [
            '',  # empty string
            '   ',  # only whitespace
            None,  # None type
            123,  # not a string
            'TAX@NAME',  # invalid character @
            'TAX#SPECIAL',  # invalid character #
            'TAX$MONEY',  # invalid character $
            'TAX(BRACKET)',  # invalid characters ()
            'A' * 51,  # too long (> 50 characters)
        ]
        
        for invalid_tax in invalid_taxes:
            with pytest.raises(ValueError):
                validate_canadian_tax_name(invalid_tax)

    def test_whitespace_handling(self):
        """Test proper handling of whitespace in tax names."""
        # Leading/trailing whitespace should be stripped
        assert validate_canadian_tax_name('  HST  ') == 'HST'
        assert validate_canadian_tax_name('\tGST\n') == 'GST'
        
        # Internal spaces should be preserved
        assert validate_canadian_tax_name('SALES TAX') == 'SALES TAX'
        assert validate_canadian_tax_name(' MUNICIPAL TAX ') == 'MUNICIPAL TAX'

    def test_edge_case_lengths(self):
        """Test edge cases for tax name length validation."""
        # Exactly at the limit (50 characters)
        long_but_valid = 'A' * 50
        assert validate_canadian_tax_name(long_but_valid) == long_but_valid
        
        # One character over the limit
        too_long = 'A' * 51
        with pytest.raises(ValueError, match="too long"):
            validate_canadian_tax_name(too_long)


class TestTaxNameValidationIntegration:
    """Test integration of tax name validation with schemas."""

    def test_tax_preference_create_valid_names(self):
        """Test TaxPreferenceCreate with valid tax names."""
        valid_data = [
            {'tax_name': 'HST', 'tax_rate': Decimal('13.00')},
            {'tax_name': 'GST+PST', 'tax_rate': Decimal('12.00')},
            {'tax_name': 'gst+pst', 'tax_rate': Decimal('12.00')},  # should normalize
            {'tax_name': 'GST/PST', 'tax_rate': Decimal('12.00')},  # should normalize
        ]
        
        for data in valid_data:
            # Should not raise an exception
            pref = TaxPreferenceCreate(**data)
            assert pref.tax_name.isupper()  # Should be normalized to uppercase

    def test_tax_preference_create_invalid_names(self):
        """Test TaxPreferenceCreate with invalid tax names."""
        invalid_data = [
            {'tax_name': '', 'tax_rate': Decimal('13.00')},
            {'tax_name': 'TAX@INVALID', 'tax_rate': Decimal('13.00')},
            {'tax_name': 'A' * 51, 'tax_rate': Decimal('13.00')},  # too long
        ]
        
        for data in invalid_data:
            with pytest.raises(ValidationError):
                TaxPreferenceCreate(**data)

    def test_invoice_tax_detail_create_validation(self):
        """Test InvoiceTaxDetailCreate with tax name validation."""
        # Valid case
        valid_detail = InvoiceTaxDetailCreate(
            tax_name='GST+PST',
            tax_rate=Decimal('12.00')
        )
        assert valid_detail.tax_name == 'GST+PST'
        
        # Invalid case
        with pytest.raises(ValidationError):
            InvoiceTaxDetailCreate(
                tax_name='INVALID@TAX',
                tax_rate=Decimal('12.00')
            )

    def test_expense_tax_detail_create_validation(self):
        """Test ExpenseTaxDetailCreate with tax name validation."""
        # Valid case with normalization
        valid_detail = ExpenseTaxDetailCreate(
            tax_name='gst/pst',  # should normalize to GST+PST
            tax_rate=Decimal('12.00')
        )
        assert valid_detail.tax_name == 'GST+PST'
        
        # Invalid case
        with pytest.raises(ValidationError):
            ExpenseTaxDetailCreate(
                tax_name='TAX#SPECIAL',
                tax_rate=Decimal('12.00')
            )

    def test_case_insensitive_validation(self):
        """Test that validation works with different cases."""
        test_cases = [
            'hst',
            'HST', 
            'Hst',
            'gSt+PsT',
            'GST+PST',
            'gst & pst'
        ]
        
        for test_case in test_cases:
            # Should not raise an exception
            result = validate_canadian_tax_name(test_case)
            assert result.isupper()  # Should be normalized to uppercase
