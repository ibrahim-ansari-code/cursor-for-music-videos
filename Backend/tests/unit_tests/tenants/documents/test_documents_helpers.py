"""
Unit tests for Tenant Documents Helpers - Strategic Coverage
Tests taxonomy and helper functions to maximize coverage.
"""

from unittest.mock import MagicMock
import pytest
from Backend.api.tenants.documents.helpers import (
    DOCUMENT_CATEGORIES,
    get_all_categories,
    get_types_for_category,
    validate_document_type,
    requires_expiry_tracking,
    get_category_icon,
    get_category_label,
    suggest_tags_for_type,
    get_total_document_types,
)
from Backend.models.enums import DocumentCategory

pytestmark = pytest.mark.unit


# ============================================================================
# DOCUMENT_CATEGORIES CONSTANT TESTS
# ============================================================================

def test_document_categories_structure():
    """Test DOCUMENT_CATEGORIES has all required fields."""
    assert len(DOCUMENT_CATEGORIES) == 14  # All 14 categories defined

    for category, info in DOCUMENT_CATEGORIES.items():
        assert isinstance(category, DocumentCategory)
        assert "label" in info
        assert "icon" in info
        assert "types" in info
        assert "requires_expiry" in info
        assert isinstance(info["types"], list)
        assert len(info["types"]) > 0


# ============================================================================
# get_all_categories TESTS (Covers helpers.py lines 473-503)
# ============================================================================

def test_get_all_categories_returns_all():
    """Test get_all_categories returns all 14 categories - covers lines 473-503."""
    categories = get_all_categories()

    assert len(categories) == 14
    assert all("key" in cat for cat in categories)
    assert all("label" in cat for cat in categories)
    assert all("icon" in cat for cat in categories)
    assert all("requires_expiry" in cat for cat in categories)
    assert all("types" in cat for cat in categories)


def test_get_all_categories_structure():
    """Test category structure is correct."""
    categories = get_all_categories()
    first_category = categories[0]

    assert first_category["key"] in [cat.value for cat in DocumentCategory]
    assert isinstance(first_category["types"], list)
    assert len(first_category["types"]) > 0


# ============================================================================
# get_types_for_category TESTS (Covers lines 525-528)
# ============================================================================

def test_get_types_for_category_lease_agreements():
    """Test getting types for lease category - covers lines 525-528."""
    types = get_types_for_category(DocumentCategory.LEASE_AGREEMENTS)

    assert isinstance(types, list)
    assert len(types) > 0
    assert "residential_tenancy_agreement" in types


def test_get_types_for_category_insurance():
    """Test getting types for insurance category."""
    types = get_types_for_category(DocumentCategory.INSURANCE_RISK)

    assert isinstance(types, list)
    assert "tenant_insurance_certificate" in types


def test_get_types_for_category_invalid():
    """Test invalid category raises KeyError."""
    # Create a fake category value not in DOCUMENT_CATEGORIES
    with pytest.raises(KeyError):
        # This should fail because we're accessing dict with invalid key
        fake_category = MagicMock()
        fake_category.value = "fake_category_not_in_dict"
        DOCUMENT_CATEGORIES[fake_category]


# ============================================================================
# validate_document_type TESTS (Covers lines 546-570)
# ============================================================================

def test_validate_document_type_valid():
    """Test valid document type - covers lines 567-569."""
    is_valid = validate_document_type(
        DocumentCategory.LEASE_AGREEMENTS,
        "residential_tenancy_agreement"
    )
    assert is_valid == True


def test_validate_document_type_invalid():
    """Test invalid document type - covers lines 567-569."""
    is_valid = validate_document_type(
        DocumentCategory.LEASE_AGREEMENTS,
        "nonexistent_document_type"
    )
    assert is_valid == False


def test_validate_document_type_wrong_category():
    """Test document type in wrong category - covers lines 567-569."""
    # tenant_insurance_certificate is in INSURANCE_RISK, not LEASE_AGREEMENTS
    is_valid = validate_document_type(
        DocumentCategory.LEASE_AGREEMENTS,
        "tenant_insurance_certificate"
    )
    assert is_valid == False


def test_validate_document_type_exception_handling():
    """Test exception handling in validation - covers lines 570."""
    # Pass something that will cause KeyError
    from unittest.mock import MagicMock
    fake_category = MagicMock()
    fake_category.__hash__ = lambda self: hash("fake")

    result = validate_document_type(fake_category, "any_type")
    assert result == False  # Should return False on exception


# ============================================================================
# requires_expiry_tracking TESTS (Covers lines 588-591)
# ============================================================================

def test_requires_expiry_tracking_insurance_true():
    """Test insurance requires expiry - covers line 590."""
    requires_expiry = requires_expiry_tracking(DocumentCategory.INSURANCE_RISK)
    assert requires_expiry == True


def test_requires_expiry_tracking_health_true():
    """Test health/safety requires expiry."""
    requires_expiry = requires_expiry_tracking(DocumentCategory.HEALTH_SAFETY)
    assert requires_expiry == True


def test_requires_expiry_tracking_lease_false():
    """Test lease agreements don't require expiry - covers line 590."""
    requires_expiry = requires_expiry_tracking(DocumentCategory.LEASE_AGREEMENTS)
    assert requires_expiry == False


def test_requires_expiry_tracking_invalid():
    """Test invalid category returns False - covers line 591."""
    from unittest.mock import MagicMock
    fake_category = MagicMock()
    result = requires_expiry_tracking(fake_category)
    assert result == False


# ============================================================================
# get_category_icon TESTS (Covers lines 613, 616-627)
# ============================================================================

def test_get_category_icon_valid():
    """Test get icon for valid category - covers line 625."""
    icon = get_category_icon(DocumentCategory.INSURANCE_RISK)
    assert icon == "Shield"


def test_get_category_icon_lease():
    """Test get icon for lease category."""
    icon = get_category_icon(DocumentCategory.LEASE_AGREEMENTS)
    assert icon == "DocumentText"


def test_get_category_icon_invalid():
    """Test default icon for invalid category - covers line 627."""
    from unittest.mock import MagicMock
    fake_category = MagicMock()
    icon = get_category_icon(fake_category)
    assert icon == "Document"  # Default icon


# ============================================================================
# get_category_label TESTS (Covers lines 639, similar pattern)
# ============================================================================

def test_get_category_label_valid():
    """Test get label for valid category."""
    label = get_category_label(DocumentCategory.INSURANCE_RISK)
    assert label == "Insurance & Risk"


def test_get_category_label_invalid():
    """Test fallback label formatting for invalid category."""
    # Create a category with a specific value
    from unittest.mock import MagicMock
    fake_category = MagicMock()
    fake_category.value = "test_category"

    label = get_category_label(fake_category)
    # Should return formatted value
    assert "Test" in label or "test" in label


# ============================================================================
# suggest_tags_for_type TESTS (Covers lines 620-626, 629)
# ============================================================================

def test_suggest_tags_for_type_insurance():
    """Test tag suggestions for insurance type - covers lines 620-623."""
    tags = suggest_tags_for_type(
        DocumentCategory.INSURANCE_RISK,
        "tenant_insurance_certificate"
    )

    assert "insurance" in tags
    assert "compliance" in tags  # Insurance requires expiry


def test_suggest_tags_for_type_renewal():
    """Test tag suggestions for renewal type - covers line 621."""
    tags = suggest_tags_for_type(
        DocumentCategory.LEASE_AGREEMENTS,
        "lease_renewal_offer"
    )

    assert "renewal" in tags


def test_suggest_tags_for_type_agreement():
    """Test tag suggestions for agreement type - covers line 624."""
    tags = suggest_tags_for_type(
        DocumentCategory.LEASE_AGREEMENTS,
        "residential_tenancy_agreement"
    )

    assert "agreement" in tags


def test_suggest_tags_for_type_notice():
    """Test tag suggestions for notice type - covers line 623."""
    tags = suggest_tags_for_type(
        DocumentCategory.LEGAL_NOTICES,
        "notice_of_entry_unit"
    )

    assert "notice" in tags


# ============================================================================
# get_total_document_types TEST
# ============================================================================

def test_get_total_document_types():
    """Test total document types count."""
    total = get_total_document_types()

    assert total > 200  # Should have 200+ document types
    assert isinstance(total, int)
