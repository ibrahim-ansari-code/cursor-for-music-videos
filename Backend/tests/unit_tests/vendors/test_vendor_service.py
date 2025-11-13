"""
Unit tests for vendor service layer.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

from Backend.api.vendors.service import VendorService
from Backend.api.vendors.schemas import VendorContactCreate, VendorContactUpdate
from Backend.models.vendor import Vendor, UserVendor
from Backend.models.user import User


# =============================================================================
# _find_or_create_vendor TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_find_or_create_vendor_existing():
    """Test finding an existing vendor by phone."""
    mock_session = AsyncMock()
    mock_vendor = MagicMock()
    mock_vendor.id = 1
    mock_vendor.company_name = "Existing Plumbing Co"
    
    data = VendorContactCreate(
        company_name="New Name",
        contact_person="John",
        trade_category="Plumbing",
        phone="+1234567890",
        email="test@example.com",
        notes="Test notes"
    )
    
    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_vendor
    mock_session.execute.return_value = mock_result
    
    vendor = await VendorService._find_or_create_vendor(data, mock_session)
    
    assert vendor == mock_vendor
    assert vendor.company_name == "Existing Plumbing Co"  # Not overwritten
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_find_or_create_vendor_new():
    """Test creating a new vendor when none exists."""
    mock_session = AsyncMock()
    
    data = VendorContactCreate(
        company_name="New Plumbing",
        contact_person="Jane",
        trade_category="Plumbing",
        phone="+1234567890",
        email="new@example.com",
        notes="Test notes"
    )
    
    # Mock execute result - no existing vendor
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    vendor = await VendorService._find_or_create_vendor(data, mock_session)
    
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()
    added_vendor = mock_session.add.call_args[0][0]
    assert isinstance(added_vendor, Vendor)
    assert added_vendor.company_name == "New Plumbing"
    assert added_vendor.phone == "+1234567890"


# =============================================================================
# create_vendor TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_vendor_success():
    """Test successful vendor creation and association."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    data = VendorContactCreate(
        company_name="Test Vendor",
        contact_person="John Doe",
        trade_category="Electrical",
        phone="+1234567890",
        email="test@example.com",
        notes="Test notes",
        is_active=True
    )
    
    # Mock vendor creation
    mock_vendor = MagicMock()
    mock_vendor.id = 1
    mock_vendor.company_name = "Test Vendor"
    
    # Mock no existing association
    mock_assoc_result = MagicMock()
    mock_assoc_result.scalar_one_or_none.return_value = None
    
    # Setup execute to return vendor first, then no association
    mock_vendor_result = MagicMock()
    mock_vendor_result.scalar_one_or_none.return_value = None  # New vendor
    mock_session.execute.side_effect = [mock_vendor_result, mock_assoc_result]
    
    # Patch _find_or_create_vendor
    with patch.object(VendorService, '_find_or_create_vendor', return_value=mock_vendor):
        vendor, user_vendor = await VendorService.create_vendor(data, mock_user, mock_session)
        
        assert vendor == mock_vendor
        mock_session.add.assert_called()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called()


@pytest.mark.asyncio
async def test_create_vendor_duplicate_association():
    """Test creating vendor when user already has this vendor."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    data = VendorContactCreate(
        company_name="Test Vendor",
        contact_person="John",
        trade_category="Plumbing",
        phone="+1234567890",
        email="test@example.com"
    )
    
    mock_vendor = MagicMock()
    mock_vendor.id = 1
    mock_vendor.company_name = "Test Vendor"
    
    # Mock existing association
    mock_existing_assoc = MagicMock()
    mock_assoc_result = MagicMock()
    mock_assoc_result.scalar_one_or_none.return_value = mock_existing_assoc
    mock_session.execute.return_value = mock_assoc_result
    
    with patch.object(VendorService, '_find_or_create_vendor', return_value=mock_vendor):
        with pytest.raises(HTTPException) as exc_info:
            await VendorService.create_vendor(data, mock_user, mock_session)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already have" in exc_info.value.detail


@pytest.mark.asyncio
async def test_create_vendor_database_error():
    """Test vendor creation handling database errors."""
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("Database error")
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    data = VendorContactCreate(
        company_name="Test",
        contact_person="John",
        trade_category="Plumbing",
        phone="+1234567890",
        email="test@example.com"
    )
    
    mock_vendor = MagicMock()
    mock_vendor.id = 1
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    with patch.object(VendorService, '_find_or_create_vendor', return_value=mock_vendor):
        with pytest.raises(HTTPException) as exc_info:
            await VendorService.create_vendor(data, mock_user, mock_session)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_session.rollback.assert_called_once()


# =============================================================================
# get_vendor TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_vendor_success():
    """Test successful vendor retrieval."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_vendor.id = 1
    
    mock_user_vendor = MagicMock()
    mock_user_vendor.vendor = mock_vendor
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user_vendor
    mock_session.execute.return_value = mock_result
    
    vendor, user_vendor = await VendorService.get_vendor(1, mock_user, mock_session)
    
    assert vendor == mock_vendor
    assert user_vendor == mock_user_vendor


@pytest.mark.asyncio
async def test_get_vendor_not_found():
    """Test getting vendor that doesn't exist or user doesn't have access to."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc_info:
        await VendorService.get_vendor(999, mock_user, mock_session)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_vendor_no_vendor_object():
    """Test getting vendor when UserVendor exists but vendor is None."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_user_vendor = MagicMock()
    mock_user_vendor.vendor = None  # Vendor is None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user_vendor
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc_info:
        await VendorService.get_vendor(1, mock_user, mock_session)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# list_vendors TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_list_vendors_no_filters():
    """Test listing vendors without filters."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    # Mock vendors
    mock_vendor1 = MagicMock()
    mock_vendor1.company_name = "A Company"
    mock_vendor2 = MagicMock()
    mock_vendor2.company_name = "B Company"
    
    mock_uv1 = MagicMock()
    mock_uv1.vendor = mock_vendor1
    mock_uv2 = MagicMock()
    mock_uv2.vendor = mock_vendor2
    
    # Mock execute results
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 2
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_uv1, mock_uv2]
    
    mock_session.execute.side_effect = [mock_count_result, mock_result]
    
    vendors, total = await VendorService.list_vendors(mock_user, mock_session)
    
    assert len(vendors) == 2
    assert total == 2
    assert vendors[0] == (mock_vendor1, mock_uv1)


@pytest.mark.asyncio
async def test_list_vendors_with_filters():
    """Test listing vendors with trade category and active filters."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_uv = MagicMock()
    mock_uv.vendor = mock_vendor
    
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_uv]
    
    mock_session.execute.side_effect = [mock_count_result, mock_result]
    
    vendors, total = await VendorService.list_vendors(
        mock_user,
        mock_session,
        trade_category="Plumbing",
        is_active=True
    )
    
    assert len(vendors) == 1
    assert total == 1


@pytest.mark.asyncio
async def test_list_vendors_with_search():
    """Test listing vendors with search filter."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_vendor.company_name = "Test Plumbing"
    mock_uv = MagicMock()
    mock_uv.vendor = mock_vendor
    
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 1
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_uv]
    
    mock_session.execute.side_effect = [mock_count_result, mock_result]
    
    vendors, total = await VendorService.list_vendors(
        mock_user,
        mock_session,
        search="Plumbing"
    )
    
    assert len(vendors) == 1


@pytest.mark.asyncio
async def test_list_vendors_pagination():
    """Test vendor list pagination."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 100
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    
    mock_session.execute.side_effect = [mock_count_result, mock_result]
    
    vendors, total = await VendorService.list_vendors(
        mock_user,
        mock_session,
        limit=10,
        offset=20
    )
    
    assert total == 100


# =============================================================================
# update_vendor TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_update_vendor_success():
    """Test successful vendor update."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_vendor.id = 1
    
    mock_user_vendor = MagicMock()
    mock_user_vendor.notes = "Old notes"
    mock_user_vendor.is_active = True
    
    update_data = VendorContactUpdate(
        notes="New notes",
        is_active=False,
        is_favorite=True
    )
    
    with patch.object(VendorService, 'get_vendor', return_value=(mock_vendor, mock_user_vendor)):
        vendor, user_vendor = await VendorService.update_vendor(1, update_data, mock_user, mock_session)
        
        assert user_vendor.notes == "New notes"
        assert user_vendor.is_active == False
        assert user_vendor.is_favorite == True
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_vendor_partial():
    """Test partial vendor update."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_user_vendor = MagicMock()
    mock_user_vendor.notes = "Old notes"
    mock_user_vendor.is_active = True
    
    update_data = VendorContactUpdate(notes="New notes")  # Only update notes
    
    with patch.object(VendorService, 'get_vendor', return_value=(mock_vendor, mock_user_vendor)):
        await VendorService.update_vendor(1, update_data, mock_user, mock_session)
        
        assert mock_user_vendor.notes == "New notes"
        assert mock_user_vendor.is_active == True  # Unchanged


@pytest.mark.asyncio
async def test_update_vendor_database_error():
    """Test vendor update handling database errors."""
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("Database error")
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_user_vendor = MagicMock()
    
    update_data = VendorContactUpdate(notes="New notes")
    
    with patch.object(VendorService, 'get_vendor', return_value=(mock_vendor, mock_user_vendor)):
        with pytest.raises(HTTPException) as exc_info:
            await VendorService.update_vendor(1, update_data, mock_user, mock_session)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_session.rollback.assert_called_once()


# =============================================================================
# delete_vendor TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_delete_vendor_success():
    """Test successful vendor deletion."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_user_vendor = MagicMock()
    
    with patch.object(VendorService, 'get_vendor', return_value=(mock_vendor, mock_user_vendor)):
        await VendorService.delete_vendor(1, mock_user, mock_session)
        
        mock_session.delete.assert_called_once_with(mock_user_vendor)
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_vendor_database_error():
    """Test vendor deletion handling database errors."""
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("Database error")
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_vendor = MagicMock()
    mock_user_vendor = MagicMock()
    
    with patch.object(VendorService, 'get_vendor', return_value=(mock_vendor, mock_user_vendor)):
        with pytest.raises(HTTPException) as exc_info:
            await VendorService.delete_vendor(1, mock_user, mock_session)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_session.rollback.assert_called_once()


# =============================================================================
# bulk_delete_vendors TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_bulk_delete_vendors_success():
    """Test successful bulk vendor deletion."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_result = MagicMock()
    mock_result.rowcount = 3
    mock_session.execute.return_value = mock_result
    
    count = await VendorService.bulk_delete_vendors([1, 2, 3], mock_user, mock_session)
    
    assert count == 3
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_delete_vendors_none_found():
    """Test bulk delete when no vendors found."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc_info:
        await VendorService.bulk_delete_vendors([999], mock_user, mock_session)
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "No vendors found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_bulk_delete_vendors_database_error():
    """Test bulk delete handling database errors."""
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database error")
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    with pytest.raises(HTTPException) as exc_info:
        await VendorService.bulk_delete_vendors([1, 2], mock_user, mock_session)
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    mock_session.rollback.assert_called_once()


# =============================================================================
# get_trade_categories TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_trade_categories_success():
    """Test getting trade categories."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["Plumbing", "Electrical", "HVAC"]
    mock_session.execute.return_value = mock_result
    
    categories = await VendorService.get_trade_categories(mock_user, mock_session)
    
    assert len(categories) == 3
    assert "Plumbing" in categories
    assert "Electrical" in categories


@pytest.mark.asyncio
async def test_get_trade_categories_empty():
    """Test getting trade categories when user has no vendors."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    categories = await VendorService.get_trade_categories(mock_user, mock_session)
    
    assert len(categories) == 0

