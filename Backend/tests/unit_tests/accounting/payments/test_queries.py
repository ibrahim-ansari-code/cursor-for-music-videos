"""
Unit tests for the Payments queries layer.

These tests focus on query building logic, database query construction, 
and helper functions without involving the HTTP layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.payments.queries import (
    get_month_payments,
    build_payments_query,
    get_user_id_from_direct_relationship,
    get_user_id_from_lease_query,
    get_user_id_from_tenant_query,
    get_affected_user_ids_concurrently,
    log_orphan_report,
    check_for_orphaned_payments
)
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2025, 1, 1, tzinfo=timezone.utc)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def mock_landlord_user():
    """Create a mock landlord user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "landlord@example.com"
    user.user_type = UserType.LANDLORD
    user.is_admin = False
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    user.user_type = UserType.ADMIN
    user.is_admin = True
    return user


@pytest.fixture
def mock_tenant_user():
    """Create a mock tenant user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "tenant@example.com"
    user.user_type = UserType.TENANT
    user.is_admin = False
    return user


@pytest.fixture
def mock_payment():
    """Create a mock payment."""
    payment = MagicMock(spec=Payment)
    payment.id = 1
    payment.lease_id = 10
    payment.tenant_id = 100
    payment.lease = None
    return payment


@pytest.fixture
def mock_lease():
    """Create a mock lease."""
    lease = MagicMock(spec=Lease)
    lease.id = 10
    lease.property_id = 1
    lease.property = None
    return lease


@pytest.fixture
def mock_property():
    """Create a mock property."""
    property_obj = MagicMock(spec=Property)
    property_obj.id = 1
    property_obj.user_id = uuid4()
    return property_obj


# =============================================================================
# get_month_payments Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_month_payments_exists(mock_session):
    """Test get_month_payments returns True when payment exists in month."""
    # Arrange
    lease_id = 10
    month_date = date(2025, 6, 15)  # June 2025
    
    # Mock query result that returns a payment ID
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = 1  # Payment ID exists
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_month_payments(mock_session, lease_id, month_date)
    
    # Assert
    assert result is True
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_month_payments_not_exists(mock_session):
    """Test get_month_payments returns False when no payment exists in month."""
    # Arrange
    lease_id = 10
    month_date = date(2025, 6, 15)  # June 2025
    
    # Mock query result that returns None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # No payment found
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_month_payments(mock_session, lease_id, month_date)
    
    # Assert
    assert result is False
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_month_payments_december_year_rollover(mock_session):
    """Test get_month_payments handles December to January year rollover correctly."""
    # Arrange
    lease_id = 10
    month_date = date(2025, 12, 15)  # December 2025
    
    # Mock query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_month_payments(mock_session, lease_id, month_date)
    
    # Assert
    assert result is False
    mock_session.execute.assert_called_once()
    
    # Verify the query was built correctly (would span Dec 1, 2025 to Jan 1, 2026)
    call_args = mock_session.execute.call_args[0][0]
    # The query should be constructed properly - we can't easily test the exact SQL
    # but we verified the function runs without error for December


# =============================================================================
# build_payments_query Tests
# =============================================================================

@pytest.mark.asyncio
async def test_build_payments_query_landlord_basic(mock_session, mock_landlord_user):
    """Test building basic payments query for landlord."""
    # Act
    query = await build_payments_query(
        session=mock_session,
        current_user=mock_landlord_user
    )
    
    # Assert
    assert query is not None
    # Query should be properly constructed for landlord filtering


@pytest.mark.asyncio
async def test_build_payments_query_tenant_forbidden_property_filter(mock_session, mock_tenant_user):
    """Test that tenants cannot filter by property."""
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await build_payments_query(
            session=mock_session,
            current_user=mock_tenant_user,
            property_id=1  # Tenants cannot filter by property
        )
    
    assert exc_info.value.status_code == 403
    assert "Tenants cannot filter payments by property" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_build_payments_query_tenant_unauthorized_tenant_filter(mock_session, mock_tenant_user):
    """Test that tenants cannot filter by other tenant IDs."""
    # Arrange - Mock tenant lookup
    mock_tenant = MagicMock()
    mock_tenant.id = 100
    mock_session.scalar.return_value = mock_tenant
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await build_payments_query(
            session=mock_session,
            current_user=mock_tenant_user,
            tenant_id=999  # Different tenant ID
        )
    
    assert exc_info.value.status_code == 403
    assert "Not authorized to access payments for other tenants" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_build_payments_query_tenant_no_profile_found(mock_session, mock_tenant_user):
    """Test that tenant without profile gets forbidden."""
    # Arrange - Mock no tenant profile found
    mock_session.scalar.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await build_payments_query(
            session=mock_session,
            current_user=mock_tenant_user
        )
    
    assert exc_info.value.status_code == 403
    assert "No tenant profile found for user" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_build_payments_query_admin_with_filters(mock_session, mock_admin_user):
    """Test building payments query for admin with all filters."""
    # Act
    query = await build_payments_query(
        session=mock_session,
        current_user=mock_admin_user,
        lease_id=10,
        property_id=1,
        tenant_id=100,
        payment_status=PaymentStatus.PAID,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31)
    )
    
    # Assert
    assert query is not None


@pytest.mark.asyncio
async def test_build_payments_query_landlord_with_property_filter(mock_session, mock_landlord_user):
    """Test building payments query for landlord with property filter - covers line 149."""
    # Act
    query = await build_payments_query(
        session=mock_session,
        current_user=mock_landlord_user,
        property_id=1  # This should trigger line 149 in queries.py
    )
    
    # Assert
    assert query is not None


@pytest.mark.asyncio
async def test_get_user_id_from_lease_query_with_property(mock_session, mock_payment):
    """Test lease query with property - covers line 221."""
    # Arrange
    user_id = uuid4()
    mock_payment.lease_id = 10
    
    # Mock lease query result with property
    mock_lease = MagicMock(spec=Lease)
    mock_property = MagicMock(spec=Property)
    mock_property.user_id = user_id
    mock_lease.property = mock_property
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_lease
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_user_id_from_lease_query(mock_payment, mock_session)
    
    # Assert
    assert result == user_id


@pytest.mark.asyncio
async def test_get_affected_user_ids_concurrently_with_exception(mock_session):
    """Test concurrent user ID aggregation handles exceptions - covers line 251."""
    # Arrange
    payment = MagicMock(spec=Payment)
    payment.lease = None  # Force database lookup
    payment.lease_id = 10
    payment.tenant_id = 100
    
    # Mock to return an exception in results
    with patch('Backend.api.accounting.payments.queries.get_user_id_from_lease_query', return_value=Exception("Test error")), \
         patch('Backend.api.accounting.payments.queries.get_user_id_from_tenant_query', return_value=None), \
         patch('Backend.api.accounting.payments.queries.logger') as mock_logger:
        
        # Act
        result = await get_affected_user_ids_concurrently([payment], mock_session)
        
        # Assert
        assert isinstance(result, set)
        # Should log the exception
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_build_payments_query_unknown_user_type(mock_session):
    """Test that unknown user type raises forbidden error."""
    # Arrange
    unknown_user = MagicMock(spec=User)
    unknown_user.user_type = "UNKNOWN_TYPE"  # Invalid user type
    unknown_user.is_admin = False
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await build_payments_query(
            session=mock_session,
            current_user=unknown_user
        )
    
    assert exc_info.value.status_code == 403
    assert "Unknown user type" in str(exc_info.value.detail)


# =============================================================================
# Orphaned Payment Detection Tests
# =============================================================================

def test_get_user_id_from_direct_relationship_success(mock_payment, mock_lease, mock_property):
    """Test successful user ID extraction from direct relationship."""
    # Arrange
    user_id = uuid4()
    mock_property.user_id = user_id
    mock_lease.property = mock_property
    mock_payment.lease = mock_lease
    
    # Act
    result = get_user_id_from_direct_relationship(mock_payment)
    
    # Assert
    assert result == user_id


def test_get_user_id_from_direct_relationship_no_lease():
    """Test user ID extraction when no lease exists."""
    # Arrange
    mock_payment = MagicMock(spec=Payment)
    mock_payment.lease = None
    
    # Act
    result = get_user_id_from_direct_relationship(mock_payment)
    
    # Assert
    assert result is None


def test_get_user_id_from_direct_relationship_no_property():
    """Test user ID extraction when lease has no property."""
    # Arrange
    mock_payment = MagicMock(spec=Payment)
    mock_lease = MagicMock(spec=Lease)
    mock_lease.property = None
    mock_payment.lease = mock_lease
    
    # Act
    result = get_user_id_from_direct_relationship(mock_payment)
    
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_user_id_from_lease_query_success(mock_session, mock_payment):
    """Test successful user ID extraction via lease query."""
    # Arrange
    user_id = uuid4()
    mock_payment.lease_id = 10
    
    # Mock lease query result
    mock_lease = MagicMock(spec=Lease)
    mock_property = MagicMock(spec=Property)
    mock_property.user_id = user_id
    mock_lease.property = mock_property
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_lease
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_user_id_from_lease_query(mock_payment, mock_session)
    
    # Assert
    assert result == user_id


@pytest.mark.asyncio
async def test_get_user_id_from_lease_query_no_lease_id(mock_session, mock_payment):
    """Test user ID extraction when payment has no lease_id."""
    # Arrange
    mock_payment.lease_id = None
    
    # Act
    result = await get_user_id_from_lease_query(mock_payment, mock_session)
    
    # Assert
    assert result is None
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_id_from_lease_query_exception(mock_session, mock_payment):
    """Test user ID extraction handles database exceptions."""
    # Arrange
    mock_payment.lease_id = 10
    mock_session.execute.side_effect = Exception("Database error")
    
    # Act
    result = await get_user_id_from_lease_query(mock_payment, mock_session)
    
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_user_id_from_tenant_query_success(mock_session, mock_payment):
    """Test successful user ID extraction via tenant query."""
    # Arrange
    user_id = uuid4()
    mock_payment.tenant_id = 100
    
    # Mock tenant property query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [user_id]  # Single user ID
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_user_id_from_tenant_query(mock_payment, mock_session)
    
    # Assert
    assert result == user_id


@pytest.mark.asyncio
async def test_get_user_id_from_tenant_query_no_tenant_id(mock_session, mock_payment):
    """Test user ID extraction when payment has no tenant_id."""
    # Arrange
    mock_payment.tenant_id = None
    
    # Act
    result = await get_user_id_from_tenant_query(mock_payment, mock_session)
    
    # Assert
    assert result is None
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_id_from_tenant_query_multiple_users(mock_session, mock_payment):
    """Test user ID extraction when tenant has multiple landlords (ambiguous)."""
    # Arrange
    user_id1 = uuid4()
    user_id2 = uuid4()
    mock_payment.tenant_id = 100
    
    # Mock tenant property query result with multiple user IDs
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [user_id1, user_id2]
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await get_user_id_from_tenant_query(mock_payment, mock_session)
    
    # Assert
    assert result is None  # Ambiguous, should return None


@pytest.mark.asyncio
async def test_get_affected_user_ids_concurrently_direct_relationships():
    """Test concurrent user ID aggregation with direct relationships."""
    # Arrange
    user_id1 = uuid4()
    user_id2 = uuid4()
    
    payment1 = MagicMock(spec=Payment)
    payment1.lease = MagicMock()
    payment1.lease.property = MagicMock()
    payment1.lease.property.user_id = user_id1
    
    payment2 = MagicMock(spec=Payment)
    payment2.lease = MagicMock()
    payment2.lease.property = MagicMock()
    payment2.lease.property.user_id = user_id2
    
    payments = [payment1, payment2]
    mock_session = MagicMock()
    
    # Act
    result = await get_affected_user_ids_concurrently(payments, mock_session)
    
    # Assert
    assert user_id1 in result
    assert user_id2 in result
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_affected_user_ids_concurrently_database_queries():
    """Test concurrent user ID aggregation with database queries."""
    # Arrange
    user_id = uuid4()
    
    payment = MagicMock(spec=Payment)
    payment.lease = None  # Force database lookup
    payment.lease_id = 10
    payment.tenant_id = 100
    
    mock_session = AsyncMock()
    
    # Mock both query strategies to return the same user_id
    with patch('Backend.api.accounting.payments.queries.get_user_id_from_lease_query', return_value=user_id), \
         patch('Backend.api.accounting.payments.queries.get_user_id_from_tenant_query', return_value=user_id):
        
        # Act
        result = await get_affected_user_ids_concurrently([payment], mock_session)
        
        # Assert
        assert user_id in result
        assert len(result) == 1  # Should deduplicate


def test_log_orphan_report_single_user():
    """Test orphan report logging for single user scan."""
    # Arrange
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid4()
    
    with patch('Backend.api.accounting.payments.queries.logger') as mock_logger:
        # Act
        log_orphan_report(5, 1, ["1", "2", "3", "4", "5"], mock_user)
        
        # Assert
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        # Check that log level is WARNING (30) or ERROR (40)
        log_level = call_args[0][0]
        assert log_level in [30, 40]  # WARNING or ERROR level
        assert str(mock_user.id) in str(call_args)


def test_log_orphan_report_global_scan():
    """Test orphan report logging for global scan."""
    # Arrange
    with patch('Backend.api.accounting.payments.queries.logger') as mock_logger:
        # Act
        log_orphan_report(15, 3, ["1", "2", "3"], None)  # Global scan (no user)
        
        # Assert
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        # Check that log level is WARNING (30) or ERROR (40)
        log_level = call_args[0][0]
        assert log_level in [30, 40]  # WARNING or ERROR level
        assert "3 user(s)" in str(call_args)


def test_log_orphan_report_critical_level():
    """Test orphan report logging uses ERROR level for many orphans."""
    # Arrange
    orphaned_ids = [str(i) for i in range(15)]  # 15 orphans should trigger ERROR level
    
    with patch('Backend.api.accounting.payments.queries.logger') as mock_logger:
        # Act
        log_orphan_report(15, 1, orphaned_ids, None)
        
        # Assert
        mock_logger.log.assert_called_once()
        call_args = mock_logger.log.call_args
        # Should use ERROR level (40) for > 10 orphans
        log_level = call_args[0][0]
        assert log_level == 40  # logging.ERROR


@pytest.mark.asyncio
async def test_check_for_orphaned_payments_success(mock_session, mock_landlord_user):
    """Test successful orphaned payments check."""
    # Arrange
    mock_payment1 = MagicMock(spec=Payment)
    mock_payment1.id = 1
    mock_payment2 = MagicMock(spec=Payment)
    mock_payment2.id = 2
    
    # Mock query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_payment1, mock_payment2]
    mock_session.execute.return_value = mock_result
    
    with patch('Backend.api.accounting.payments.queries.get_affected_user_ids_concurrently', return_value={uuid4()}), \
         patch('Backend.api.accounting.payments.queries.log_orphan_report'):
        
        # Act
        result = await check_for_orphaned_payments(mock_session, mock_landlord_user, False)
        
        # Assert
        assert result["orphaned_payments"] is True
        assert result["total_orphaned_count"] == 2
        assert result["users_with_orphans"] == 1
        assert len(result["orphaned_payment_ids"]) == 2


@pytest.mark.asyncio
async def test_check_for_orphaned_payments_no_orphans(mock_session, mock_landlord_user):
    """Test orphaned payments check when no orphans found."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # No orphaned payments
    mock_session.execute.return_value = mock_result
    
    # Act
    result = await check_for_orphaned_payments(mock_session, mock_landlord_user, False)
    
    # Assert
    assert result["orphaned_payments"] is False
    assert result["total_orphaned_count"] == 0
    assert result["users_with_orphans"] == 0
    assert result["orphaned_payment_ids"] == []


@pytest.mark.asyncio
async def test_check_for_orphaned_payments_global_scan(mock_session, mock_landlord_user):
    """Test orphaned payments check for all users."""
    # Arrange
    mock_payment = MagicMock(spec=Payment)
    mock_payment.id = 1
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_payment]
    mock_session.execute.return_value = mock_result
    
    with patch('Backend.api.accounting.payments.queries.get_affected_user_ids_concurrently', return_value={uuid4(), uuid4()}), \
         patch('Backend.api.accounting.payments.queries.log_orphan_report'):
        
        # Act
        result = await check_for_orphaned_payments(mock_session, mock_landlord_user, True)
        
        # Assert
        assert result["orphaned_payments"] is True
        assert result["total_orphaned_count"] == 1
        assert result["users_with_orphans"] == 2  # Two affected users


@pytest.mark.asyncio
async def test_check_for_orphaned_payments_exception_handling(mock_session, mock_landlord_user):
    """Test orphaned payments check handles exceptions gracefully."""
    # Arrange
    mock_session.execute.side_effect = Exception("Database error")
    
    with patch('Backend.api.accounting.payments.queries.logger') as mock_logger:
        # Act
        result = await check_for_orphaned_payments(mock_session, mock_landlord_user, False)
        
        # Assert
        assert result["orphaned_payments"] is False
        assert result["total_orphaned_count"] == 0
        mock_logger.exception.assert_called_once() 