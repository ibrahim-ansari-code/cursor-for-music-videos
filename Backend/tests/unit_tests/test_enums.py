"""
Unit tests for enum classes in models/enums.py

These tests cover enum functionality and edge cases.
"""

import pytest
from Backend.models.enums import TenantType, ExpenseCategory


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestTenantType:
    """Test TenantType enum functionality."""
    
    def test_tenant_type_values(self):
        """Test TenantType enum values."""
        assert TenantType.INDIVIDUAL == "Individual"
        assert TenantType.COMPANY == "Company"
    
    def test_tenant_type_missing_case_insensitive(self):
        """Test TenantType._missing_ method with case insensitive matching - Lines 33, 35-38."""
        # Test case insensitive matching
        assert TenantType._missing_("individual") == TenantType.INDIVIDUAL
        assert TenantType._missing_("INDIVIDUAL") == TenantType.INDIVIDUAL
        assert TenantType._missing_("Individual") == TenantType.INDIVIDUAL
        
        assert TenantType._missing_("company") == TenantType.COMPANY
        assert TenantType._missing_("COMPANY") == TenantType.COMPANY
        assert TenantType._missing_("Company") == TenantType.COMPANY
    
    def test_tenant_type_missing_invalid_value(self):
        """Test TenantType._missing_ method with invalid value."""
        # Test with invalid string
        assert TenantType._missing_("invalid") is None
        
        # Test with non-string value
        assert TenantType._missing_(123) is None
        assert TenantType._missing_(None) is None
        assert TenantType._missing_([]) is None
    
    def test_tenant_type_missing_optimization_path(self):
        """Test TenantType._missing_ optimization with value_lower - Line 36."""
        # This test specifically targets line 36 where value_lower is used
        # to ensure the optimization path is covered
        result = TenantType._missing_("INDIVIDUAL")
        assert result == TenantType.INDIVIDUAL
        
        result = TenantType._missing_("company")
        assert result == TenantType.COMPANY


class TestExpenseCategory:
    """Test ExpenseCategory enum functionality."""
    
    def test_expense_category_values(self):
        """Test ExpenseCategory enum values."""
        assert ExpenseCategory.MAINTENANCE == "maintenance"
        assert ExpenseCategory.UTILITIES == "utilities"
        assert ExpenseCategory.TAXES == "taxes"
        assert ExpenseCategory.INSURANCE == "insurance"
        assert ExpenseCategory.ADMINISTRATIVE == "administrative"
        assert ExpenseCategory.OTHER == "other"
    
    def test_expense_category_missing_case_insensitive_value(self):
        """Test ExpenseCategory._missing_ method with case insensitive value matching - Lines 56, 58-61."""
        # Test case insensitive matching by value
        assert ExpenseCategory._missing_("MAINTENANCE") == ExpenseCategory.MAINTENANCE
        assert ExpenseCategory._missing_("utilities") == ExpenseCategory.UTILITIES
        assert ExpenseCategory._missing_("TaXeS") == ExpenseCategory.TAXES
    
    def test_expense_category_missing_member_name_matching(self):
        """Test ExpenseCategory._missing_ method with member name matching - Lines 63-67."""
        # Test case insensitive matching by member name (e.g., "MAINTENANCE" maps to ExpenseCategory.MAINTENANCE)
        assert ExpenseCategory._missing_("MAINTENANCE") == ExpenseCategory.MAINTENANCE
        assert ExpenseCategory._missing_("utilities") == ExpenseCategory.UTILITIES
        
        # Test with invalid values that should return None
        assert ExpenseCategory._missing_("invalid_category") is None
        assert ExpenseCategory._missing_(123) is None
