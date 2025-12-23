"""
Unit tests for rent tracker service layer.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status

from Backend.api.accounting.rent_tracker.service import RentTrackerService
from Backend.api.accounting.rent_tracker.schemas import (
    RentTrackingEntry,
    RentTrackerSummary,
    RentTrackerFilter,
    RentStatus
)
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property


# =============================================================================
# AUTHORIZATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_check_authorization_admin():
    """Test authorization check for admin user."""
    admin_user = MagicMock()
    admin_user.user_type = UserType.ADMIN
    admin_user.is_admin = True
    
    result = RentTrackerService._check_authorization(admin_user)
    
    assert result is True


@pytest.mark.asyncio
async def test_check_authorization_landlord():
    """Test authorization check for landlord user."""
    landlord_user = MagicMock()
    landlord_user.user_type = UserType.LANDLORD
    landlord_user.is_admin = False
    
    result = RentTrackerService._check_authorization(landlord_user)
    
    assert result is True


@pytest.mark.asyncio
async def test_check_authorization_tenant():
    """Test authorization check for tenant user (should fail)."""
    tenant_user = MagicMock()
    tenant_user.user_type = UserType.TENANT
    tenant_user.is_admin = False
    
    result = RentTrackerService._check_authorization(tenant_user)
    
    assert result is False


# =============================================================================
# get_rent_tracker TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_success():
    """Test successful rent tracker retrieval."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    filters = RentTrackerFilter(month=3, year=2024)
    
    # Mock lease data
    mock_lease = MagicMock()
    mock_lease.id = 1
    mock_lease.monthly_rent = Decimal("1500.00")
    mock_lease.tenant_id = 1
    mock_lease.property.name = "Test Property"
    mock_lease.tenant.first_name = "John"
    mock_lease.tenant.last_name = "Doe"
    mock_lease.tenant.email = "john.doe@example.com"
    mock_lease.unit = None
    
    # Mock service methods
    with patch.object(RentTrackerService, '_get_active_leases', new_callable=AsyncMock) as mock_get_leases:
        with patch.object(RentTrackerService, '_create_tracking_entry', new_callable=AsyncMock) as mock_create_entry:
            mock_get_leases.return_value = [mock_lease]
            
            mock_entry = RentTrackingEntry(
                lease_id=1,
                tenant_id=1,
                tenant_name="John Doe",
                property_name="Test Property",
                monthly_rent=Decimal("1500.00"),
                amount_paid=Decimal("1500.00"),
                remaining_due=Decimal("0.00"),
                status=RentStatus.PAID
            )
            mock_create_entry.return_value = mock_entry
            
            # Act
            result = await RentTrackerService.get_rent_tracker(
                session=mock_session,
                current_user=mock_user,
                filters=filters
            )
            
            # Assert
            assert len(result) == 1
            assert result[0].tenant_name == "John Doe"
            assert result[0].status == RentStatus.PAID
            mock_get_leases.assert_called_once()
            mock_create_entry.assert_called_once()


@pytest.mark.asyncio
async def test_get_rent_tracker_unauthorized():
    """Test rent tracker retrieval with unauthorized user."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.TENANT  # Not authorized
    mock_user.is_admin = False  # Explicitly set to False
    
    filters = RentTrackerFilter()
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await RentTrackerService.get_rent_tracker(
            session=mock_session,
            current_user=mock_user,
            filters=filters
        )
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Not authorized to view rent tracker" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_rent_tracker_with_status_filter():
    """Test rent tracker retrieval with status filter."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    filters = RentTrackerFilter(status=RentStatus.OVERDUE)
    
    # Mock lease data
    mock_lease = MagicMock()
    mock_lease.id = 1
    
    # Mock entry with different status (should be filtered out)
    mock_entry_paid = RentTrackingEntry(
        lease_id=1,
        tenant_name="John Doe",
        property_name="Test Property",
        monthly_rent=Decimal("1500.00"),
        amount_paid=Decimal("1500.00"),
        remaining_due=Decimal("0.00"),
        status=RentStatus.PAID  # Different from filter
    )
    
    # Mock service methods
    with patch.object(RentTrackerService, '_get_active_leases', new_callable=AsyncMock) as mock_get_leases:
        with patch.object(RentTrackerService, '_create_tracking_entry', new_callable=AsyncMock) as mock_create_entry:
            mock_get_leases.return_value = [mock_lease]
            mock_create_entry.return_value = mock_entry_paid
            
            # Act
            result = await RentTrackerService.get_rent_tracker(
                session=mock_session,
                current_user=mock_user,
                filters=filters
            )
            
            # Assert - entry should be filtered out due to status mismatch
            assert len(result) == 0


@pytest.mark.asyncio
async def test_get_rent_tracker_service_error():
    """Test rent tracker retrieval when service raises an error."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    filters = RentTrackerFilter()
    
    # Mock service to raise an error
    with patch.object(RentTrackerService, '_get_active_leases', new_callable=AsyncMock) as mock_get_leases:
        mock_get_leases.side_effect = Exception("Database error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await RentTrackerService.get_rent_tracker(
                session=mock_session,
                current_user=mock_user,
                filters=filters
            )
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to get rent tracker" in str(exc_info.value.detail)


# =============================================================================
# get_rent_tracker_summary TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_rent_tracker_summary_success():
    """Test successful rent tracker summary retrieval."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    filters = RentTrackerFilter()
    
    expected_summary = RentTrackerSummary(
        total_units=10,
        total_expected=Decimal("15000.00"),
        total_collected=Decimal("12000.00"),
        total_outstanding=Decimal("3000.00"),
        units_paid=7,
        units_partial=2,
        units_due=1,
        units_overdue=0,
        collection_rate=Decimal("80.00")
    )
    
    # Mock service method
    with patch.object(RentTrackerService, '_get_summary_aggregation', new_callable=AsyncMock) as mock_get_summary:
        mock_get_summary.return_value = expected_summary
        
        # Act
        result = await RentTrackerService.get_rent_tracker_summary(
            session=mock_session,
            current_user=mock_user,
            filters=filters
        )
        
        # Assert
        assert result.total_units == 10
        assert result.collection_rate == Decimal("80.00")
        mock_get_summary.assert_called_once()


@pytest.mark.asyncio
async def test_get_rent_tracker_summary_unauthorized():
    """Test rent tracker summary retrieval with unauthorized user."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.TENANT  # Not authorized
    mock_user.is_admin = False  # Explicitly set to False
    
    filters = RentTrackerFilter()
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await RentTrackerService.get_rent_tracker_summary(
            session=mock_session,
            current_user=mock_user,
            filters=filters
        )
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Not authorized to view rent tracker summary" in str(exc_info.value.detail)


# =============================================================================
# _get_active_leases TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_active_leases_admin():
    """Test getting active leases for admin user."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    mock_user.id = str(uuid4())
    
    property_id = None
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock lease result
    mock_lease = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value = [mock_lease]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await RentTrackerService._get_active_leases(
        session=mock_session,
        current_user=mock_user,
        property_id=property_id,
        month_start=month_start,
        month_end=month_end
    )
    
    # Assert
    assert len(result) == 1
    assert result[0] == mock_lease
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_leases_landlord():
    """Test getting active leases for landlord user (filtered by ownership)."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.LANDLORD
    mock_user.id = str(uuid4())
    
    property_id = None
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock lease result
    mock_lease = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value = [mock_lease]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await RentTrackerService._get_active_leases(
        session=mock_session,
        current_user=mock_user,
        property_id=property_id,
        month_start=month_start,
        month_end=month_end
    )
    
    # Assert
    assert len(result) == 1
    assert result[0] == mock_lease
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_active_leases_with_property_filter():
    """Test getting active leases with property filter."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    property_id = 123  # Specific property filter
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock lease result
    mock_lease = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value = [mock_lease]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await RentTrackerService._get_active_leases(
        session=mock_session,
        current_user=mock_user,
        property_id=property_id,
        month_start=month_start,
        month_end=month_end
    )
    
    # Assert
    assert len(result) == 1
    mock_session.execute.assert_called_once()


# =============================================================================
# _create_tracking_entry TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_tracking_entry_success():
    """Test successful creation of tracking entry."""
    # Arrange
    mock_session = AsyncMock()
    
    mock_lease = MagicMock()
    mock_lease.id = 1
    mock_lease.monthly_rent = Decimal("1500.00")
    mock_lease.tenant_id = 1
    mock_lease.property.name = "Test Property"
    mock_lease.tenant.first_name = "John"
    mock_lease.tenant.last_name = "Doe"
    mock_lease.tenant.email = "john.doe@example.com"
    mock_lease.unit = None
    
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    filters = RentTrackerFilter()
    
    # Mock helper functions
    with patch('Backend.api.accounting.rent_tracker.service.calculate_rent_due_date') as mock_due_date:
        with patch('Backend.api.accounting.rent_tracker.service.determine_rent_status') as mock_status:
            with patch.object(RentTrackerService, '_calculate_lease_payments', new_callable=AsyncMock) as mock_calc_payments:
                with patch.object(RentTrackerService, '_get_last_payment_date', new_callable=AsyncMock) as mock_last_payment:
                    
                    mock_calc_payments.return_value = Decimal("1500.00")
                    mock_last_payment.return_value = date(2024, 3, 1)
                    mock_due_date.return_value = date(2024, 3, 1)
                    mock_status.return_value = (RentStatus.PAID, None)
                    
                    # Act
                    result = await RentTrackerService._create_tracking_entry(
                        session=mock_session,
                        lease=mock_lease,
                        month_start=month_start,
                        month_end=month_end,
                        filters=filters
                    )
                    
                    # Assert
                    assert result is not None
                    assert result.lease_id == 1
                    assert result.tenant_name == "John Doe"
                    assert result.status == RentStatus.PAID
                    assert result.monthly_rent == Decimal("1500.00")


@pytest.mark.asyncio
async def test_create_tracking_entry_no_lease_id():
    """Test tracking entry creation with lease having no ID."""
    # Arrange
    mock_session = AsyncMock()
    
    mock_lease = MagicMock()
    mock_lease.id = None  # No ID
    
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    filters = RentTrackerFilter()
    
    # Act
    result = await RentTrackerService._create_tracking_entry(
        session=mock_session,
        lease=mock_lease,
        month_start=month_start,
        month_end=month_end,
        filters=filters
    )
    
    # Assert
    assert result is None


# =============================================================================
# _calculate_lease_payments TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_calculate_lease_payments():
    """Test calculating total payments for a lease."""
    # Arrange
    mock_session = AsyncMock()
    lease_id = 1
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock query result
    mock_result = MagicMock()
    mock_result.scalar.return_value = Decimal("1200.00")
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await RentTrackerService._calculate_lease_payments(
        session=mock_session,
        lease_id=lease_id,
        month_start=month_start,
        month_end=month_end
    )
    
    # Assert
    assert result == Decimal("1200.00")
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_calculate_lease_payments_no_payments():
    """Test calculating payments when no payments exist."""
    # Arrange
    mock_session = AsyncMock()
    lease_id = 1
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock query result - no payments
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await RentTrackerService._calculate_lease_payments(
        session=mock_session,
        lease_id=lease_id,
        month_start=month_start,
        month_end=month_end
    )
    
    # Assert
    assert result == Decimal("0.0")


# =============================================================================
# _get_last_payment_date TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_last_payment_date():
    """Test getting last payment date for a lease."""
    # Arrange
    mock_session = AsyncMock()
    lease_id = 1
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock query result
    mock_result = MagicMock()
    mock_result.scalar.return_value = date(2024, 3, 15)
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await RentTrackerService._get_last_payment_date(
        session=mock_session,
        lease_id=lease_id,
        month_start=month_start,
        month_end=month_end
    )
    
    # Assert
    assert result == date(2024, 3, 15)
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_last_payment_date_no_payments():
    """Test getting last payment date when no payments exist."""
    # Arrange
    mock_session = AsyncMock()
    lease_id = 1
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock query result - no payments
    mock_result = MagicMock()
    mock_result.scalar.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await RentTrackerService._get_last_payment_date(
        session=mock_session,
        lease_id=lease_id,
        month_start=month_start,
        month_end=month_end
    )
    
    # Assert
    assert result is None


# =============================================================================
# _get_summary_aggregation TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_summary_aggregation_no_leases():
    """Test summary aggregation when no leases exist."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    property_id = None
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock no leases
    with patch.object(RentTrackerService, '_get_active_leases', new_callable=AsyncMock) as mock_get_leases:
        mock_get_leases.return_value = []
        
        # Act
        result = await RentTrackerService._get_summary_aggregation(
            session=mock_session,
            current_user=mock_user,
            property_id=property_id,
            month_start=month_start,
            month_end=month_end
        )
        
        # Assert
        assert result.total_units == 0
        assert result.total_expected == Decimal("0.00")
        assert result.collection_rate == Decimal("0.00")


@pytest.mark.asyncio
async def test_get_summary_aggregation_with_leases():
    """Test summary aggregation with leases."""
    # Arrange
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    property_id = None
    month_start = date(2024, 3, 1)
    month_end = date(2024, 3, 31)
    
    # Mock leases
    mock_lease1 = MagicMock()
    mock_lease1.id = 1
    mock_lease1.monthly_rent = Decimal("1500.00")
    
    mock_lease2 = MagicMock()
    mock_lease2.id = 2
    mock_lease2.monthly_rent = Decimal("1200.00")
    
    # Mock payment query result
    mock_payment_result = MagicMock()
    mock_payment_result.__iter__ = lambda self: iter([
        MagicMock(lease_id=1, total_paid=Decimal("1500.00")),
        MagicMock(lease_id=2, total_paid=Decimal("600.00"))
    ])
    mock_session.execute.return_value = mock_payment_result
    
    # Mock helper functions
    with patch.object(RentTrackerService, '_get_active_leases', new_callable=AsyncMock) as mock_get_leases:
        with patch('Backend.api.accounting.rent_tracker.service.calculate_rent_due_date') as mock_due_date:
            with patch('Backend.api.accounting.rent_tracker.service.determine_rent_status') as mock_status:
                with patch('Backend.api.accounting.rent_tracker.service.calculate_collection_rate') as mock_calc_rate:
                    
                    mock_get_leases.return_value = [mock_lease1, mock_lease2]
                    mock_due_date.return_value = date(2024, 3, 1)
                    
                    # Mock different statuses for the leases
                    mock_status.side_effect = [
                        (RentStatus.PAID, None),      # Lease 1
                        (RentStatus.PARTIAL, None)    # Lease 2
                    ]
                    mock_calc_rate.return_value = Decimal("77.78")
                    
                    # Act
                    result = await RentTrackerService._get_summary_aggregation(
                        session=mock_session,
                        current_user=mock_user,
                        property_id=property_id,
                        month_start=month_start,
                        month_end=month_end
                    )
                    
                    # Assert
                    assert result.total_units == 2
                    assert result.total_expected == Decimal("2700.00")  # 1500 + 1200
                    assert result.total_collected == Decimal("2100.00")  # 1500 + 600
                    assert result.units_paid == 1
                    assert result.units_partial == 1
                    assert result.units_due == 0
                    assert result.units_overdue == 0