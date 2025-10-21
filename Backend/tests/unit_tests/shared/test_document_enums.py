"""
Unit tests for Document-related Enums - Strategic Coverage
Tests DocumentCategory and DocumentStatus enums.
"""

import pytest
from Backend.models.enums import DocumentCategory, DocumentStatus

pytestmark = pytest.mark.unit


# ============================================================================
# DocumentCategory ENUM TESTS (Covers enums.py lines 186-197)
# ============================================================================

def test_document_category_all_values():
    """Test all 14 document categories are defined - covers lines 186-196."""
    expected_categories = [
        "lease_agreements",
        "lease_addendums",
        "condition_inspections",
        "province_forms",
        "commercial_files",
        "applications_kyc",
        "insurance_risk",
        "financial_payments",
        "maintenance_work",
        "legal_notices",
        "communications",
        "move_in_out",
        "privacy_security",
        "health_safety"
    ]

    for category_value in expected_categories:
        # Test each category exists
        category = DocumentCategory(category_value)
        assert category.value == category_value


def test_document_category_case_insensitive():
    """Test case-insensitive enum matching - covers lines 188-191."""
    # Test uppercase
    cat1 = DocumentCategory("LEASE_AGREEMENTS")
    assert cat1 == DocumentCategory.LEASE_AGREEMENTS

    # Test mixed case
    cat2 = DocumentCategory("Insurance_Risk")
    assert cat2 == DocumentCategory.INSURANCE_RISK


def test_document_category_invalid():
    """Test invalid category raises error - covers line 193."""
    with pytest.raises(ValueError):
        DocumentCategory("nonexistent_category")


def test_document_category_enum_values():
    """Test specific category values."""
    assert DocumentCategory.INSURANCE_RISK.value == "insurance_risk"
    assert DocumentCategory.LEGAL_NOTICES.value == "legal_notices"
    assert DocumentCategory.HEALTH_SAFETY.value == "health_safety"


# ============================================================================
# DocumentStatus ENUM TESTS (Covers enums.py lines 217-228)
# ============================================================================

def test_document_status_all_values():
    """Test all 4 document statuses are defined - covers lines 217-227."""
    expected_statuses = ["pending", "verified", "rejected", "expired"]

    for status_value in expected_statuses:
        status = DocumentStatus(status_value)
        assert status.value == status_value


def test_document_status_case_insensitive():
    """Test case-insensitive status matching - covers lines 219-222."""
    # Test uppercase
    status1 = DocumentStatus("PENDING")
    assert status1 == DocumentStatus.PENDING

    # Test mixed case
    status2 = DocumentStatus("Verified")
    assert status2 == DocumentStatus.VERIFIED


def test_document_status_invalid():
    """Test invalid status raises error - covers line 224."""
    with pytest.raises(ValueError):
        DocumentStatus("invalid_status")


def test_document_status_enum_values():
    """Test specific status values."""
    assert DocumentStatus.PENDING.value == "pending"
    assert DocumentStatus.VERIFIED.value == "verified"
    assert DocumentStatus.REJECTED.value == "rejected"
    assert DocumentStatus.EXPIRED.value == "expired"


def test_document_status_equality():
    """Test status equality comparisons."""
    status1 = DocumentStatus.PENDING
    status2 = DocumentStatus("pending")

    assert status1 == status2
    assert status1 != DocumentStatus.VERIFIED
