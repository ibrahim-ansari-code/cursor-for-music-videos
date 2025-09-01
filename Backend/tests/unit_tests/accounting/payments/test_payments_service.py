"""
Unit tests for the Payments service layer.

These tests focus on business logic, database interactions, and service-level
functionality without involving the HTTP layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4, UUID
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from Backend.api.accounting.payments.service import (
    create_payment,
    get_payments,
    get_payment_by_id,
    update_payment,
    delete_payment,
    get_outstanding_payments_for_month,
    generate_due_payments_for_month,
    parse_payment_receipt,
    run_orphaned_payments_check
)
from Backend.api.accounting.payments.schemas import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaginatedPaymentsResponse,
    PaymentReceiptParseResponse,
    PaymentReceiptParseDetails
)
from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import UserType
from Backend.models.user import User
from Backend.models.property import Property
from Backend.models.tenant import Tenant
from Backend.models.lease import Lease, LeaseStatus

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2025, 1, 1, tzinfo=timezone.utc)
FIXED_CURRENT_DATE = date(2025, 1, 15)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    # Setup common mock behaviors
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalar_one_or_none = AsyncMock()
    return session


@pytest.fixture
def mock_landlord_user():
    """Create a mock landlord user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "landlord@example.com"
    user.user_type = UserType.LANDLORD
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "admin@example.com"
    user.user_type = UserType.ADMIN
    user.is_admin = True
    user.is_active = True
    return user


@pytest.fixture
def mock_tenant_user():
    """Create a mock tenant user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "tenant@example.com"
    user.user_type = UserType.TENANT
    user.is_admin = False
    user.is_active = True
    return user


@pytest.fixture
def mock_payment():
    """Create a mock payment."""
    payment = MagicMock(spec=Payment)
    payment.id = 1
    payment.lease_id = 10
    payment.tenant_id = 100
    payment.amount = Decimal("1200.00")
    payment.payment_date = FIXED_DATETIME
    payment.payment_method = PaymentMethod.BANK_TRANSFER
    payment.status = PaymentStatus.PAID
    payment.transaction_reference = "TXN123"
    payment.description = "Rent payment"
    payment.receipt_url = "http://example.com/receipt.pdf"
    payment.created_at = FIXED_DATETIME
    payment.updated_at = FIXED_DATETIME
    payment.reduction_amount = None
    payment.reduction_reason = None
    return payment


@pytest.fixture
def mock_tenant():
    """Create a mock tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = 100
    tenant.first_name = "John"
    tenant.last_name = "Doe"
    tenant.email = "john.doe@example.com"
    tenant.user_id = uuid4()
    return tenant


@pytest.fixture
def mock_property():
    """Create a mock property."""
    property_obj = MagicMock(spec=Property)
    property_obj.id = 1
    property_obj.name = "Test Property"
    property_obj.user_id = uuid4()
    return property_obj


@pytest.fixture
def mock_lease(mock_tenant, mock_property):
    """Create a mock lease."""
    lease = MagicMock(spec=Lease)
    lease.id = 10
    lease.tenant_id = 100
    lease.property_id = 1
    lease.monthly_rent = Decimal("1200.00")
    lease.status = LeaseStatus.ACTIVE
    lease.start_date = date.today() - timedelta(days=30)
    lease.end_date = date.today() + timedelta(days=330)
    lease.tenant = mock_tenant
    lease.property = mock_property
    return lease


# =============================================================================
# create_payment Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_payment_success(mock_session, mock_landlord_user, mock_lease, mock_tenant, mock_property):
    """Test successful payment creation."""
    # Arrange
    payment_data = PaymentCreate(
        lease_id=10,
        amount=Decimal("1200.00"),
        payment_method=PaymentMethod.BANK_TRANSFER,
        status=PaymentStatus.PAID,
        description="Monthly rent"
    )
    
    # Mock lease with proper relationships
    mock_lease.property.user_id = mock_landlord_user.id
    
    # Mock the helper functions
    with patch('Backend.api.accounting.payments.service.check_lease_ownership', return_value=mock_lease), \
         patch('Backend.api.accounting.payments.service.validate_business_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.get_payment_method_enum', return_value=PaymentMethod.BANK_TRANSFER), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response, \
         patch('Backend.api.accounting.payments.service._ensure_id_is_not_none'), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME):
        
        # Setup mock response
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1200.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PAID,
            description="Monthly rent",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="John Doe",
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Mock refresh side effect to set ID
        def refresh_side_effect(obj, attribute_names=None):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 1
        mock_session.refresh.side_effect = refresh_side_effect
        
        # Act
        result = await create_payment(payment_data, mock_session, mock_landlord_user)
        
        # Assert
        assert result.id == 1
        assert result.amount == Decimal("1200.00")
        assert result.status == PaymentStatus.PAID
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_payment_tenant_forbidden(mock_session, mock_tenant_user):
    """Test that tenants cannot create payments."""
    # Arrange
    payment_data = PaymentCreate(
        lease_id=10,
        amount=Decimal("1200.00")
    )
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_payment(payment_data, mock_session, mock_tenant_user)
    
    assert exc_info.value.status_code == 403
    assert "Tenants cannot directly create payment records" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_payment_database_error(mock_session, mock_landlord_user, mock_lease):
    """Test payment creation handles database errors."""
    # Arrange
    payment_data = PaymentCreate(
        lease_id=10,
        amount=Decimal("1200.00")
    )
    
    # Mock lease ownership check
    with patch('Backend.api.accounting.payments.service.check_lease_ownership', return_value=mock_lease), \
         patch('Backend.api.accounting.payments.service.validate_business_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.get_payment_method_enum', return_value=PaymentMethod.OTHER):
        
        # Setup commit to raise error
        async def commit_side_effect():
            raise Exception("Database error")
        mock_session.commit.side_effect = commit_side_effect
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_payment(payment_data, mock_session, mock_landlord_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to create payment" in str(exc_info.value.detail)
        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_create_payment_no_payment_date_uses_current_time(mock_session, mock_landlord_user, mock_lease):
    """Test payment creation uses current time when no payment_date provided."""
    # Arrange
    payment_data = PaymentCreate(
        lease_id=10,
        amount=Decimal("1200.00")
    )
    payment_data.payment_date = None  # Explicitly set to None
    
    # Mock lease with proper relationships
    mock_lease.property.user_id = mock_landlord_user.id
    
    with patch('Backend.api.accounting.payments.service.check_lease_ownership', return_value=mock_lease), \
         patch('Backend.api.accounting.payments.service.get_payment_method_enum', return_value=PaymentMethod.OTHER), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response, \
         patch('Backend.api.accounting.payments.service._ensure_id_is_not_none'), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME) as mock_utc_now:
        
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1200.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.OTHER,
            status=PaymentStatus.PENDING,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="John Doe",
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Mock refresh side effect
        def refresh_side_effect(obj, attribute_names=None):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 1
        mock_session.refresh.side_effect = refresh_side_effect
        
        # Act
        result = await create_payment(payment_data, mock_session, mock_landlord_user)
        
        # Assert
        assert result.payment_date == FIXED_DATETIME
        mock_utc_now.assert_called()  # Verify current time was used


@pytest.mark.asyncio
async def test_create_payment_data_integrity_error(mock_session, mock_landlord_user, mock_lease):
    """Test payment creation handles data integrity error - covers line 110."""
    # Arrange
    payment_data = PaymentCreate(
        lease_id=10,
        amount=Decimal("1200.00")
    )
    
    # Mock lease with proper relationships
    mock_lease.property.user_id = mock_landlord_user.id
    
    with patch('Backend.api.accounting.payments.service.check_lease_ownership', return_value=mock_lease), \
         patch('Backend.api.accounting.payments.service.validate_business_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.get_payment_method_enum', return_value=PaymentMethod.OTHER), \
         patch('Backend.api.accounting.payments.service._ensure_id_is_not_none'), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME):
        
        # Mock refresh side effect to set ID
        def refresh_side_effect(obj, attribute_names=None):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 1
        mock_session.refresh.side_effect = refresh_side_effect
        
        # Mock build_payment_response_from_orm to return None after everything else succeeds
        with patch('Backend.api.accounting.payments.service.build_payment_response_from_orm', return_value=None):
            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await create_payment(payment_data, mock_session, mock_landlord_user)
            
            assert exc_info.value.status_code == 500
            assert "Payment data integrity error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_payment_by_id_data_integrity_error(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property):
    """Test get_payment_by_id handles data integrity error - covers line 212."""
    # Arrange
    payment_id = 1
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock build_payment_response_from_orm to return None
    with patch('Backend.api.accounting.payments.service.build_payment_response_from_orm', return_value=None):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_payment_by_id(payment_id, mock_session, mock_landlord_user)
        
        assert exc_info.value.status_code == 500
        assert "Payment data integrity error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_payment_refresh_lease_property_tenant(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property, mock_tenant):
    """Test update_payment refreshes lease property and tenant - covers lines 255, 285, 292."""
    # Arrange
    payment_id = 1
    update_data = PaymentUpdate(
        amount=Decimal("1500.00"),
        description="Updated payment"
    )
    
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_lease.tenant = mock_tenant
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.check_payment_ownership', return_value=True), \
         patch('Backend.api.accounting.payments.service.create_audit_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
        
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PAID,
            description="Updated payment",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="John Doe",
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Act
        result = await update_payment(payment_id, update_data, mock_session, mock_landlord_user)
        
        # Assert
        assert result.amount == Decimal("1500.00")
        assert result.description == "Updated payment"
        # Verify refresh was called for lease, property, and tenant
        assert mock_session.refresh.call_count >= 3


# =============================================================================
# get_payments Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_payments_landlord_filters_and_pagination(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_tenant, mock_property):
    """Test that get_payments correctly applies landlord-specific filters and pagination."""
    # Arrange
    mock_payment.lease = mock_lease
    mock_lease.tenant = mock_tenant
    mock_lease.property = mock_property
    mock_property.user_id = mock_landlord_user.id
    
    # Mock the query builder
    with patch('Backend.api.accounting.payments.service.build_payments_query') as mock_build_query:
        # Create a mock query object
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_build_query.return_value = mock_query
        
        # Mock execute result
        mock_execute_result = MagicMock()
        mock_execute_result.unique.return_value = mock_execute_result
        mock_execute_result.scalars.return_value = mock_execute_result
        mock_execute_result.all.return_value = [mock_payment, mock_payment]  # Return 2 payments to test pagination
        mock_session.execute.return_value = mock_execute_result
        
        # Mock build_payment_response_from_orm
        with patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
            mock_response = PaymentResponse(
                id=1,
                lease_id=10,
                tenant_id=100,
                amount=Decimal("1200.00"),
                payment_date=FIXED_DATETIME,
                payment_method=PaymentMethod.BANK_TRANSFER,
                status=PaymentStatus.PAID,
                created_at=FIXED_DATETIME,
                updated_at=FIXED_DATETIME,
                tenant_name="John Doe",
                property_name="Test Property"
            )
            mock_build_response.return_value = mock_response
            
            # Act
            result = await get_payments(
                session=mock_session,
                current_user=mock_landlord_user,
                property_id=1,
                payment_status=PaymentStatus.PAID,
                start_date=date.today() - timedelta(days=10),
                end_date=date.today(),
                limit=1,
                offset=0
            )
            
            # Assert
            assert isinstance(result, PaginatedPaymentsResponse)
            assert len(result.items) == 1  # Limited to 1 item
            assert result.has_more is True  # Should be True since we returned 2 items but limit is 1
            assert result.items[0].property_name == "Test Property"
            mock_build_query.assert_called_once()


@pytest.mark.asyncio
async def test_get_payments_no_matching_filters(mock_session, mock_landlord_user):
    """Test get_payments returns empty response when no payments match filters."""
    # Mock the query builder
    with patch('Backend.api.accounting.payments.service.build_payments_query') as mock_build_query:
        mock_query = MagicMock()
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_build_query.return_value = mock_query
        
        # Mock execute result to return empty
        mock_execute_result = MagicMock()
        mock_execute_result.unique.return_value = mock_execute_result
        mock_execute_result.scalars.return_value = mock_execute_result
        mock_execute_result.all.return_value = []  # No payments found
        mock_session.execute.return_value = mock_execute_result
        
        # Act
        result = await get_payments(
            session=mock_session,
            current_user=mock_landlord_user,
            lease_id=9999,  # Non-existent lease_id
            limit=10,
            offset=0
        )
        
        # Assert
        assert isinstance(result, PaginatedPaymentsResponse)
        assert result.items == []
        assert result.has_more is False


@pytest.mark.asyncio
async def test_get_payments_database_error(mock_session, mock_landlord_user):
    """Test get_payments handles database errors."""
    # Mock the query builder to raise an exception
    with patch('Backend.api.accounting.payments.service.build_payments_query') as mock_build_query:
        mock_build_query.side_effect = Exception("Database connection error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_payments(
                session=mock_session,
                current_user=mock_landlord_user
            )
        
        assert exc_info.value.status_code == 500
        assert "Failed to fetch payments" in str(exc_info.value.detail)


# =============================================================================
# get_payment_by_id Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_payment_by_id_success(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property):
    """Test successful payment retrieval by ID."""
    # Arrange
    payment_id = 1
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock build_payment_response_from_orm
    with patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1200.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PAID,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="John Doe",
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Act
        result = await get_payment_by_id(payment_id, mock_session, mock_landlord_user)
        
        # Assert
        assert result.id == 1
        assert result.property_name == "Test Property"


@pytest.mark.asyncio
async def test_get_payment_by_id_not_found(mock_session, mock_landlord_user):
    """Test payment by ID not found."""
    # Arrange
    payment_id = 999
    
    # Mock execute result to return None
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_execute_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_payment_by_id(payment_id, mock_session, mock_landlord_user)
    
    assert exc_info.value.status_code == 404
    assert f"Payment {payment_id} not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_payment_by_id_tenant_unauthorized(mock_session, mock_tenant_user, mock_payment, mock_tenant):
    """Test tenant unauthorized to access payment not belonging to them."""
    # Arrange
    payment_id = 1
    mock_payment.tenant_id = 999  # Different tenant
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock tenant query to return different tenant
    mock_tenant.id = 100  # Different from payment.tenant_id
    mock_session.scalar.return_value = mock_tenant
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_payment_by_id(payment_id, mock_session, mock_tenant_user)
    
    assert exc_info.value.status_code == 403
    assert "Not authorized" in str(exc_info.value.detail)


# =============================================================================
# update_payment Tests
# =============================================================================

@pytest.mark.asyncio
async def test_update_payment_success(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property):
    """Test successful payment update."""
    # Arrange
    payment_id = 1
    update_data = PaymentUpdate(
        amount=Decimal("1500.00"),
        description="Updated payment"
    )
    
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.check_payment_ownership', return_value=True), \
         patch('Backend.api.accounting.payments.service.create_audit_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
        
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PAID,
            description="Updated payment",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="John Doe",
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Act
        result = await update_payment(payment_id, update_data, mock_session, mock_landlord_user)
        
        # Assert
        assert result.amount == Decimal("1500.00")
        assert result.description == "Updated payment"
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_payment_tenant_forbidden(mock_session, mock_tenant_user):
    """Test that tenants cannot update payments."""
    # Arrange
    payment_id = 1
    update_data = PaymentUpdate(amount=Decimal("1500.00"))
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_payment(payment_id, update_data, mock_session, mock_tenant_user)
    
    assert exc_info.value.status_code == 403
    assert "Tenants cannot update payment records" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_payment_not_found(mock_session, mock_landlord_user):
    """Test update payment not found."""
    # Arrange
    payment_id = 999
    update_data = PaymentUpdate(amount=Decimal("1500.00"))
    
    # Mock execute result to return None
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_execute_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_payment(payment_id, update_data, mock_session, mock_landlord_user)
    
    assert exc_info.value.status_code == 404
    assert f"Payment {payment_id} not found" in str(exc_info.value.detail)


# =============================================================================
# delete_payment Tests
# =============================================================================

@pytest.mark.asyncio
async def test_delete_payment_success(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property):
    """Test successful payment deletion."""
    # Arrange
    payment_id = 1
    mock_payment.receipt_url = "http://example.com/receipt.pdf"
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock check_payment_ownership
    with patch('Backend.api.accounting.payments.service.check_payment_ownership', return_value=True):
        
        # Act
        result = await delete_payment(payment_id, mock_session, mock_landlord_user)
        
        # Assert
        assert result == "http://example.com/receipt.pdf"
        mock_session.delete.assert_called_once_with(mock_payment)
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_payment_not_found(mock_session, mock_landlord_user):
    """Test delete payment not found."""
    # Arrange
    payment_id = 999
    
    # Mock execute result to return None
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_execute_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_payment(payment_id, mock_session, mock_landlord_user)
    
    assert exc_info.value.status_code == 404
    assert f"Payment {payment_id} not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_payment_http_exception_reraise(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property):
    """Test delete payment re-raises HTTPException - covers line 319."""
    # Arrange
    payment_id = 1
    mock_payment.receipt_url = "http://example.com/receipt.pdf"
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock check_payment_ownership and session.delete to raise HTTPException
    with patch('Backend.api.accounting.payments.service.check_payment_ownership', return_value=True):
        mock_session.delete.side_effect = HTTPException(status_code=403, detail="Test HTTP exception")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await delete_payment(payment_id, mock_session, mock_landlord_user)
        
        assert exc_info.value.status_code == 403
        assert "Test HTTP exception" in str(exc_info.value.detail)


# =============================================================================
# get_outstanding_payments_for_month Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_outstanding_payments_for_month_includes_both_statuses(mock_session, mock_landlord_user):
    """Test get_outstanding_payments_for_month returns both Pending and Overdue payments."""
    # Arrange
    pending_payment = MagicMock(spec=Payment)
    pending_payment.id = 1
    pending_payment.status = PaymentStatus.PENDING
    
    overdue_payment = MagicMock(spec=Payment)
    overdue_payment.id = 2
    overdue_payment.status = PaymentStatus.OVERDUE
    
    # Mock the query builder
    with patch('Backend.api.accounting.payments.service.build_payments_query') as mock_build_query, \
         patch('Backend.api.accounting.payments.service.utc_now') as mock_utc_now:
        
        mock_utc_now.return_value = datetime(2025, 1, 15, tzinfo=timezone.utc)
        
        # Create a mock query object
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_build_query.return_value = mock_query
        
        # Mock execute result
        mock_execute_result = MagicMock()
        mock_execute_result.unique.return_value = mock_execute_result
        mock_execute_result.scalars.return_value = mock_execute_result
        mock_execute_result.all.return_value = [pending_payment, overdue_payment]
        mock_session.execute.return_value = mock_execute_result
        
        # Mock build_payment_response_from_orm
        with patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
            def build_response_side_effect(payment):
                return PaymentResponse(
                    id=payment.id,
                    lease_id=10,
                    tenant_id=100,
                    amount=Decimal("1200.00"),
                    payment_date=FIXED_DATETIME,
                    payment_method=PaymentMethod.BANK_TRANSFER,
                    status=payment.status,
                    created_at=FIXED_DATETIME,
                    updated_at=FIXED_DATETIME,
                    tenant_name="John Doe",
                    property_name="Test Property"
                )
            mock_build_response.side_effect = build_response_side_effect
            
            # Act
            result = await get_outstanding_payments_for_month(
                session=mock_session,
                current_user=mock_landlord_user,
                limit=10
            )
            
            # Assert
            assert isinstance(result, list)
            assert len(result) == 2
            payment_statuses = [payment.status for payment in result]
            assert PaymentStatus.PENDING in payment_statuses
            assert PaymentStatus.OVERDUE in payment_statuses


# =============================================================================
# generate_due_payments_for_month Tests
# =============================================================================

@pytest.mark.asyncio
async def test_generate_due_payments_for_month_success(mock_session, mock_landlord_user, mock_lease, mock_tenant, mock_property):
    """Test successful generation of due payments for month."""
    # Arrange
    mock_lease.property.user_id = mock_landlord_user.id
    mock_lease.start_date = date.today() - timedelta(days=30)
    mock_lease.end_date = date.today() + timedelta(days=330)
    mock_lease.status = LeaseStatus.ACTIVE
    mock_lease.monthly_rent = Decimal("1200.00")
    
    # Mock active leases query
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.all.return_value = [mock_lease]
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.get_month_payments', return_value=False), \
         patch('Backend.api.accounting.payments.service.get_tenant_display_name', return_value="John Doe"), \
         patch('Backend.api.accounting.payments.service.quantize_2dp', side_effect=lambda x: x), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service._ensure_id_is_not_none'), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
        
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1200.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.OTHER,
            status=PaymentStatus.PENDING,
            description="Monthly rent payment for John Doe",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="John Doe",
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Mock refresh side effect to set ID
        def refresh_side_effect(obj, attribute_names=None):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 1
        mock_session.refresh.side_effect = refresh_side_effect
        
        # Act
        result = await generate_due_payments_for_month(mock_session, mock_landlord_user)
        
        # Assert
        assert len(result) == 1
        assert result[0].amount == Decimal("1200.00")
        assert result[0].status == PaymentStatus.PENDING
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_generate_due_payments_for_month_tenant_forbidden(mock_session, mock_tenant_user):
    """Test that tenants cannot generate payments."""
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await generate_due_payments_for_month(mock_session, mock_tenant_user)
    
    assert exc_info.value.status_code == 403
    assert "Not authorized" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_generate_due_payments_for_month_no_active_leases(mock_session, mock_landlord_user):
    """Test generate payments when no active leases exist."""
    # Mock execute result to return empty
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.all.return_value = []
    mock_session.execute.return_value = mock_execute_result
    
    with patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME):
        # Act
        result = await generate_due_payments_for_month(mock_session, mock_landlord_user)
        
        # Assert
        assert result == []


@pytest.mark.asyncio
async def test_generate_due_payments_for_month_with_no_tenant_id(mock_session, mock_landlord_user, mock_lease, mock_tenant, mock_property):
    """Test generate payments skips lease with no tenant ID - covers line 452."""
    # Arrange
    mock_lease.property.user_id = mock_landlord_user.id
    mock_lease.start_date = date.today() - timedelta(days=30)
    mock_lease.end_date = date.today() + timedelta(days=330)
    mock_lease.status = LeaseStatus.ACTIVE
    mock_lease.monthly_rent = Decimal("1200.00")
    mock_lease.tenant = mock_tenant
    mock_tenant.id = None  # No tenant ID
    
    # Mock active leases query
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.all.return_value = [mock_lease]
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.get_month_payments', return_value=False), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME):
        
        # Act
        result = await generate_due_payments_for_month(mock_session, mock_landlord_user)
        
        # Assert
        assert result == []  # Should skip lease and return empty


@pytest.mark.asyncio
async def test_generate_due_payments_for_month_lease_none_id(mock_session, mock_landlord_user, mock_lease, mock_tenant, mock_property):
    """Test generate payments skips lease with None ID - covers line 335."""
    # Arrange
    mock_lease.id = None  # Lease with None ID
    mock_lease.property.user_id = mock_landlord_user.id
    mock_lease.start_date = date.today() - timedelta(days=30)
    mock_lease.end_date = date.today() + timedelta(days=330)
    mock_lease.status = LeaseStatus.ACTIVE
    mock_lease.monthly_rent = Decimal("1200.00")
    
    # Mock active leases query
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.all.return_value = [mock_lease]
    mock_session.execute.return_value = mock_execute_result
    
    with patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME):
        # Act
        result = await generate_due_payments_for_month(mock_session, mock_landlord_user)
        
        # Assert
        assert result == []  # Should skip lease and return empty


@pytest.mark.asyncio
async def test_parse_payment_receipt_file_validation_error_specific(mock_landlord_user):
    """Test payment receipt parsing with specific file validation error - covers line 559."""
    # Arrange
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "receipt.pdf"
    mock_file.content_type = "application/pdf"
    
    # Mock validate_file_from_upload to raise ValueError with file-related error
    with patch('Backend.api.accounting.payments.service.validate_file_from_upload', side_effect=ValueError("Invalid file format detected")):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await parse_payment_receipt(mock_file, mock_landlord_user)
        
        assert exc_info.value.status_code == 400
        assert "File validation failed: Invalid file format detected" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_parse_payment_receipt_data_parsing_error(mock_landlord_user):
    """Test payment receipt parsing with data parsing error - covers line 561."""
    # Arrange
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "receipt.pdf"
    mock_file.content_type = "application/pdf"
    
    # Mock validate_file_from_upload to raise ValueError with data-related error
    with patch('Backend.api.accounting.payments.service.validate_file_from_upload', side_effect=ValueError("Invalid data format")):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await parse_payment_receipt(mock_file, mock_landlord_user)
        
        assert exc_info.value.status_code == 400
        assert "Invalid receipt data provided" in str(exc_info.value.detail)


# =============================================================================
# parse_payment_receipt Tests
# =============================================================================

@pytest.mark.asyncio
async def test_parse_payment_receipt_success(mock_landlord_user):
    """Test successful payment receipt parsing."""
    # Arrange
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "receipt.pdf"
    mock_file.content_type = "application/pdf"
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.validate_file_from_upload', return_value=(b"file_content", "application/pdf")), \
         patch('Backend.api.accounting.payments.service.upload_payment_receipt_to_blob', return_value="http://example.com/receipt.pdf"), \
         patch('Backend.api.accounting.payments.service.analyze_payment_receipt_content', return_value={
             "amount": "1200.00",
             "payment_date": "2024-06-01",
             "tenant_name": "John Doe",
             "property_name": "Test Property"
         }):
        
        # Act
        result = await parse_payment_receipt(mock_file, mock_landlord_user)
        
        # Assert
        assert isinstance(result, PaymentReceiptParseResponse)
        assert result.receipt_url == "http://example.com/receipt.pdf"
        assert result.message is not None and "Receipt processed" in result.message


@pytest.mark.asyncio
async def test_generate_due_payments_refresh_lease_relationships(mock_session, mock_landlord_user, mock_lease, mock_tenant, mock_property):
    """Test generate payments refreshes lease relationships - covers lines 490, 502, 504."""
    # Arrange
    mock_lease.property.user_id = mock_landlord_user.id
    mock_lease.start_date = date.today() - timedelta(days=30)
    mock_lease.end_date = date.today() + timedelta(days=330)
    mock_lease.status = LeaseStatus.ACTIVE
    mock_lease.monthly_rent = Decimal("1200.00")
    mock_lease.tenant = mock_tenant
    mock_tenant.id = 100
    
    # Mock active leases query
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.all.return_value = [mock_lease]
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.get_month_payments', return_value=False), \
         patch('Backend.api.accounting.payments.service.get_tenant_display_name', return_value="John Doe"), \
         patch('Backend.api.accounting.payments.service.quantize_2dp', side_effect=lambda x: x), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service._ensure_id_is_not_none'), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
        
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1200.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.OTHER,
            status=PaymentStatus.PENDING,
            description="Monthly rent payment for John Doe",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name="John Doe",
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Mock refresh side effect to set ID
        def refresh_side_effect(obj, attribute_names=None):
            if hasattr(obj, 'id') and obj.id is None:
                obj.id = 1
        mock_session.refresh.side_effect = refresh_side_effect
        
        # Act
        result = await generate_due_payments_for_month(mock_session, mock_landlord_user)
        
        # Assert
        assert len(result) == 1
        # Verify refresh was called for payment, lease and its relationships
        assert mock_session.refresh.call_count >= 2


@pytest.mark.asyncio
async def test_parse_payment_receipt_tenant_forbidden(mock_tenant_user):
    """Test that tenants cannot parse payment receipts."""
    # Arrange
    mock_file = MagicMock(spec=UploadFile)
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await parse_payment_receipt(mock_file, mock_tenant_user)
    
    assert exc_info.value.status_code == 403
    assert "Not authorized to parse payment receipts" in str(exc_info.value.detail)





@pytest.mark.asyncio
async def test_parse_payment_receipt_connection_error(mock_landlord_user):
    """Test payment receipt parsing with Azure connection error."""
    # Arrange
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "receipt.pdf"
    mock_file.content_type = "application/pdf"
    
    # Mock functions
    with patch('Backend.api.accounting.payments.service.validate_file_from_upload', return_value=(b"file_content", "application/pdf")), \
         patch('Backend.api.accounting.payments.service.upload_payment_receipt_to_blob', side_effect=ConnectionError("Azure connection failed")):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await parse_payment_receipt(mock_file, mock_landlord_user)
        
        assert exc_info.value.status_code == 503
        assert "External service is unavailable" in str(exc_info.value.detail)


# =============================================================================
# Additional Coverage Tests - Missing Lines
# =============================================================================

@pytest.mark.asyncio
async def test_get_payment_by_id_tenant_no_user_tenant(mock_session, mock_tenant_user, mock_payment):
    """Test get_payment_by_id when tenant user has no associated tenant record - covers line 214."""
    # Arrange
    payment_id = 1
    
    # Mock execute result for payment query
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock session.scalar to return None for tenant query (line 214)
    mock_session.scalar.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_payment_by_id(payment_id, mock_session, mock_tenant_user)
    
    assert exc_info.value.status_code == 403
    assert "Not authorized" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_payment_by_id_tenant_wrong_tenant_id(mock_session, mock_tenant_user, mock_payment, mock_tenant):
    """Test get_payment_by_id when tenant payment doesn't belong to user - covers line 217."""
    # Arrange
    payment_id = 1
    mock_payment.tenant_id = 999  # Different tenant ID
    
    # Mock tenant for the user
    mock_tenant.id = 100  # User's tenant ID (different from payment)
    
    # Mock execute result for payment query
    mock_execute_result = MagicMock()
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock session.scalar to return user's tenant
    mock_session.scalar.return_value = mock_tenant
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_payment_by_id(payment_id, mock_session, mock_tenant_user)
    
    assert exc_info.value.status_code == 403
    assert "Not authorized" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_payment_data_integrity_error(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property):
    """Test update_payment handles data integrity error - covers line 257."""
    # Arrange
    payment_id = 1
    update_data = PaymentUpdate(amount=Decimal("1500.00"))
    
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.check_payment_ownership', return_value=True), \
         patch('Backend.api.accounting.payments.service.create_audit_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm', return_value=None):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_payment(payment_id, update_data, mock_session, mock_landlord_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to update payment" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_payment_no_lease_property(mock_session, mock_landlord_user, mock_payment, mock_lease):
    """Test update_payment refresh when lease has no property - covers line 287."""
    # Arrange
    payment_id = 1
    update_data = PaymentUpdate(amount=Decimal("1500.00"))
    
    mock_payment.lease = mock_lease
    mock_lease.property = None  # No property
    mock_lease.tenant = None
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.check_payment_ownership', return_value=True), \
         patch('Backend.api.accounting.payments.service.create_audit_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
        
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PAID,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name=None,
            property_name=None
        )
        mock_build_response.return_value = mock_response
        
        # Act
        result = await update_payment(payment_id, update_data, mock_session, mock_landlord_user)
        
        # Assert
        assert result.amount == Decimal("1500.00")
        # Verify refresh was called for payment and lease but not property/tenant
        mock_session.refresh.assert_called()


@pytest.mark.asyncio
async def test_update_payment_no_lease_tenant(mock_session, mock_landlord_user, mock_payment, mock_lease, mock_property):
    """Test update_payment refresh when lease has no tenant - covers line 294."""
    # Arrange
    payment_id = 1
    update_data = PaymentUpdate(amount=Decimal("1500.00"))
    
    mock_payment.lease = mock_lease
    mock_lease.property = mock_property
    mock_lease.tenant = None  # No tenant
    mock_property.user_id = mock_landlord_user.id
    
    # Mock execute result
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = mock_payment
    mock_session.execute.return_value = mock_execute_result
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.check_payment_ownership', return_value=True), \
         patch('Backend.api.accounting.payments.service.create_audit_datetime', return_value=FIXED_DATETIME), \
         patch('Backend.api.accounting.payments.service.build_payment_response_from_orm') as mock_build_response:
        
        mock_response = PaymentResponse(
            id=1,
            lease_id=10,
            tenant_id=100,
            amount=Decimal("1500.00"),
            payment_date=FIXED_DATETIME,
            payment_method=PaymentMethod.BANK_TRANSFER,
            status=PaymentStatus.PAID,
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME,
            tenant_name=None,
            property_name="Test Property"
        )
        mock_build_response.return_value = mock_response
        
        # Act
        result = await update_payment(payment_id, update_data, mock_session, mock_landlord_user)
        
        # Assert
        assert result.amount == Decimal("1500.00")
        # Verify refresh was called for payment, lease, and property but not tenant
        mock_session.refresh.assert_called()


@pytest.mark.asyncio
async def test_get_outstanding_payments_for_month_http_exception_reraise(mock_session, mock_landlord_user):
    """Test get_outstanding_payments_for_month re-raises HTTPException - covers line 337."""
    # Arrange - Mock build_payments_query to raise HTTPException
    with patch('Backend.api.accounting.payments.service.build_payments_query', side_effect=HTTPException(status_code=403, detail="Access denied")), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=datetime(2025, 1, 15, tzinfo=timezone.utc)):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_outstanding_payments_for_month(mock_session, mock_landlord_user)
        
        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_generate_due_payments_for_month_lease_processing_error(mock_session, mock_landlord_user):
    """Test generate_due_payments_for_month handles lease processing exception - covers lines 399,401."""
    # Arrange - Mock execute to raise an exception during lease query
    mock_session.execute.side_effect = Exception("Database error during lease query")
    
    with patch('Backend.api.accounting.payments.service.utc_now', return_value=datetime(2025, 1, 15, tzinfo=timezone.utc)):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_due_payments_for_month(mock_session, mock_landlord_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate due payments" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_generate_due_payments_for_month_commit_exception(mock_session, mock_landlord_user, mock_lease, mock_tenant, mock_property):
    """Test generate_due_payments_for_month handles commit exception - covers lines 492,504,506."""
    # Arrange
    mock_lease.property.user_id = mock_landlord_user.id
    mock_lease.start_date = date.today() - timedelta(days=30)
    mock_lease.end_date = date.today() + timedelta(days=330)
    mock_lease.status = LeaseStatus.ACTIVE
    mock_lease.monthly_rent = Decimal("1200.00")
    mock_lease.tenant = mock_tenant
    mock_tenant.id = 100
    
    # Mock active leases query
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_execute_result
    mock_execute_result.unique.return_value = mock_execute_result
    mock_execute_result.all.return_value = [mock_lease]
    mock_session.execute.return_value = mock_execute_result
    
    # Mock commit to raise exception after payments are added
    mock_session.commit.side_effect = Exception("Database commit failed")
    
    # Mock helper functions
    with patch('Backend.api.accounting.payments.service.get_month_payments', return_value=False), \
         patch('Backend.api.accounting.payments.service.get_tenant_display_name', return_value="John Doe"), \
         patch('Backend.api.accounting.payments.service.quantize_2dp', side_effect=lambda x: x), \
         patch('Backend.api.accounting.payments.service.utc_now', return_value=FIXED_DATETIME):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await generate_due_payments_for_month(mock_session, mock_landlord_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to generate due payments" in str(exc_info.value.detail)
        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_parse_payment_receipt_general_exception(mock_landlord_user):
    """Test parse_payment_receipt handles general exception - covers line 581."""
    # Arrange
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "receipt.pdf"
    mock_file.content_type = "application/pdf"
    
    # Mock validate_file_from_upload to succeed but other function to fail
    with patch('Backend.api.accounting.payments.service.validate_file_from_upload', return_value=(b"file_content", "application/pdf")), \
         patch('Backend.api.accounting.payments.service.upload_payment_receipt_to_blob', return_value="http://example.com/receipt.pdf"), \
         patch('Backend.api.accounting.payments.service.analyze_payment_receipt_content', side_effect=Exception("Unexpected error")):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await parse_payment_receipt(mock_file, mock_landlord_user)
        
        assert exc_info.value.status_code == 500
        assert "Failed to parse payment receipt due to an internal error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_run_orphaned_payments_check_success(mock_session, mock_admin_user):
    """Test successful orphaned payments check."""
    # Arrange
    mock_report = {
        "orphaned_payments": [],
        "total_orphaned_count": 0,
        "users_with_orphans": 0
    }
    
    with patch('Backend.api.accounting.payments.service.check_for_orphaned_payments', return_value=mock_report):
        
        # Act
        result = await run_orphaned_payments_check(mock_session, mock_admin_user)
        
        # Assert
        assert result["status"] == "ok"
        assert "No orphaned payments found" in result["message"]


@pytest.mark.asyncio
async def test_run_orphaned_payments_check_with_orphans(mock_session, mock_admin_user):
    """Test orphaned payments check when orphans are found."""
    # Arrange
    mock_report = {
        "orphaned_payments": [{"id": 1, "lease_id": 999}],
        "total_orphaned_count": 5,
        "users_with_orphans": 2
    }
    
    with patch('Backend.api.accounting.payments.service.check_for_orphaned_payments', return_value=mock_report):
        
        # Act
        result = await run_orphaned_payments_check(mock_session, mock_admin_user)
        
        # Assert
        assert result["status"] == "warning"
        assert "Found 5 orphaned payment(s) across 2 user(s)" in result["message"]
        assert result["details"] == mock_report


@pytest.mark.asyncio
async def test_run_orphaned_payments_check_not_admin(mock_session, mock_landlord_user):
    """Test orphaned payments check when user is not admin."""
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await run_orphaned_payments_check(mock_session, mock_landlord_user)
    
    assert exc_info.value.status_code == 403
    assert "Not authorized for this operation" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_run_orphaned_payments_check_exception(mock_session, mock_admin_user):
    """Test orphaned payments check handles exceptions."""
    # Arrange
    with patch('Backend.api.accounting.payments.service.check_for_orphaned_payments', side_effect=Exception("Check failed")):
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await run_orphaned_payments_check(mock_session, mock_admin_user)
        
        assert exc_info.value.status_code == 500
        assert "Integrity check failed due to internal error" in str(exc_info.value.detail)
