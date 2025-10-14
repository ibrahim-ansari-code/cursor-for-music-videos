"""
Unit tests for the Tenants service layer.

These tests focus on business logic, database interactions, and service-level
functionality without involving the HTTP layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4, UUID
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from Backend.api.tenants.service import (
    check_tenant_permission,
    create_and_save_tenant,
    _build_tenant_filters,
    build_filtered_tenants_query,
    build_unassigned_tenants_query,
    enrich_tenants_with_details,
)
from Backend.api.tenants.schemas import (
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    PropertyResponseSimple,
    UnitResponseSimple,
    LeaseResponseSimple,
)
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.enums import TenantType, UserType
from Backend.models.user import User
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.lease import Lease, LeaseStatus

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


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
    return session


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
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
def mock_tenant():
    """Create a mock individual tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.tenant_type = TenantType.INDIVIDUAL
    tenant.first_name = "John"
    tenant.last_name = "Doe"
    tenant.company_name = None
    tenant.contact_person = None
    tenant.email = "john.doe@example.com"
    tenant.phone = "555-1234"
    tenant.status = TenantStatus.ACTIVE
    tenant.landlord_id = uuid4()
    tenant.current_property_id = None
    tenant.created_at = datetime.now(timezone.utc)
    tenant.updated_at = datetime.now(timezone.utc)
    return tenant


@pytest.fixture
def mock_company_tenant():
    """Create a mock company tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = 2
    tenant.tenant_type = TenantType.COMPANY
    tenant.first_name = None
    tenant.last_name = None
    tenant.company_name = "Tech Corp"
    tenant.contact_person = "Jane Smith"
    tenant.email = "contact@techcorp.com"
    tenant.phone = "555-5678"
    tenant.status = TenantStatus.ACTIVE
    tenant.landlord_id = uuid4()
    tenant.current_property_id = None
    tenant.created_at = datetime.now(timezone.utc)
    tenant.updated_at = datetime.now(timezone.utc)
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
def mock_unit():
    """Create a mock unit."""
    unit = MagicMock(spec=PropertyUnit)
    unit.id = 1
    unit.property_id = 1
    unit.name = "Unit A"
    unit.tenant_id = 1
    return unit


@pytest.fixture
def mock_lease():
    """Create a mock lease."""
    lease = MagicMock(spec=Lease)
    lease.id = 1
    lease.tenant_id = 1
    lease.property_id = 1
    lease.unit_id = 1
    lease.status = LeaseStatus.ACTIVE
    lease.start_date = datetime.now(timezone.utc).date()
    lease.end_date = datetime.now(timezone.utc).date()
    return lease


# =============================================================================
# check_tenant_permission Tests
# =============================================================================

@pytest.mark.asyncio
async def test_check_tenant_permission_success(mock_session, mock_user, mock_tenant):
    """Test successful tenant permission check."""
    # Setup mock session
    mock_session.get.return_value = mock_tenant
    mock_tenant.landlord_id = mock_user.id
    
    # Act
    result = await check_tenant_permission(1, mock_session, mock_user)
    
    # Assert
    assert result == mock_tenant
    mock_session.get.assert_called_once_with(Tenant, 1)


@pytest.mark.asyncio
async def test_check_tenant_permission_tenant_not_found(mock_session, mock_user):
    """Test tenant permission check when tenant doesn't exist."""
    # Setup mock session
    mock_session.get.return_value = None
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await check_tenant_permission(999, mock_session, mock_user)
    
    assert exc_info.value.status_code == 404
    assert "Tenant not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_check_tenant_permission_admin_access(mock_session, mock_admin_user, mock_tenant):
    """Test admin can access any tenant."""
    # Setup mock session
    mock_session.get.return_value = mock_tenant
    mock_tenant.landlord_id = uuid4()  # Different owner
    
    # Act
    result = await check_tenant_permission(1, mock_session, mock_admin_user)
    
    # Assert
    assert result == mock_tenant  # Admin can access


@pytest.mark.asyncio
async def test_check_tenant_permission_forbidden(mock_session, mock_user, mock_tenant):
    """Test tenant permission check forbidden for non-owner."""
    # Setup mock session
    mock_session.get.return_value = mock_tenant
    mock_tenant.landlord_id = uuid4()  # Different owner
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await check_tenant_permission(1, mock_session, mock_user)
    
    assert exc_info.value.status_code == 403
    assert "Not authorized to view this tenant" in str(exc_info.value.detail)


# =============================================================================
# create_and_save_tenant Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_and_save_tenant_individual_success(mock_session, mock_user):
    """Test successful individual tenant creation."""
    # Setup tenant data
    tenant_data = TenantCreate(
        tenant_type=TenantType.INDIVIDUAL,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-123-4567",
        status=TenantStatus.ACTIVE
    )
    
    # Mock refresh to add required fields
    def refresh_side_effect(obj):
        obj.id = 1
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
    
    mock_session.refresh.side_effect = refresh_side_effect
    
    # Act
    result = await create_and_save_tenant(tenant_data, mock_user.id, mock_session, MagicMock())
    
    # Assert
    assert result.tenant_type == TenantType.INDIVIDUAL
    assert result.first_name == "John"
    assert result.last_name == "Doe"
    assert result.email == "john.doe@example.com"
    assert result.landlord_id == mock_user.id
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_create_and_save_tenant_company_success(mock_session, mock_user):
    """Test successful company tenant creation."""
    # Setup tenant data
    tenant_data = TenantCreate(
        tenant_type=TenantType.COMPANY,
        company_name="Tech Corp",
        contact_person="Jane Smith",
        email="contact@techcorp.com",
        phone="555-567-8901",
        status=TenantStatus.ACTIVE
    )
    
    # Mock refresh to add required fields
    def refresh_side_effect(obj):
        obj.id = 2
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)
    
    mock_session.refresh.side_effect = refresh_side_effect
    
    # Act
    result = await create_and_save_tenant(tenant_data, mock_user.id, mock_session, MagicMock())
    
    # Assert
    assert result.tenant_type == TenantType.COMPANY
    assert result.company_name == "Tech Corp"
    assert result.contact_person == "Jane Smith"
    assert result.email == "contact@techcorp.com"
    assert result.landlord_id == mock_user.id
    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_create_and_save_tenant_database_error(mock_session, mock_user):
    """Test tenant creation handles database errors."""
    # Setup tenant data
    tenant_data = TenantCreate(
        tenant_type=TenantType.INDIVIDUAL,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com"
    )
    
    # Setup flush to raise error
    async def flush_side_effect():
        raise IntegrityError(
            statement="INSERT INTO tenants ...",
            params={},
            orig=Exception("Database constraint violated")
        )
    mock_session.flush.side_effect = flush_side_effect
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_and_save_tenant(tenant_data, mock_user.id, mock_session, MagicMock())
    
    assert exc_info.value.status_code == 400
    mock_session.rollback.assert_called_once()


# =============================================================================
# _build_tenant_filters Tests
# =============================================================================

def test_build_tenant_filters_no_filters():
    """Test building tenant filters with no parameters."""
    filters = _build_tenant_filters(None, None)
    assert len(filters) == 0


def test_build_tenant_filters_with_status():
    """Test building tenant filters with status filter."""
    filters = _build_tenant_filters(TenantStatus.ACTIVE, None)
    assert len(filters) == 1


def test_build_tenant_filters_with_search():
    """Test building tenant filters with search term."""
    filters = _build_tenant_filters(None, "john")
    assert len(filters) == 1


def test_build_tenant_filters_all_parameters():
    """Test building tenant filters with all parameters."""
    filters = _build_tenant_filters(
        TenantStatus.ACTIVE, "john"
    )
    assert len(filters) == 2


# =============================================================================
# build_filtered_tenants_query Tests
# =============================================================================

def test_build_filtered_tenants_query_basic(mock_user):
    """Test building basic tenant query."""
    query = build_filtered_tenants_query(mock_user, None, None, None)
    assert query is not None


def test_build_filtered_tenants_query_with_filters(mock_user):
    """Test building tenant query with filters."""
    query = build_filtered_tenants_query(
        mock_user, TenantStatus.ACTIVE, "john", property_id=1
    )
    assert query is not None


def test_build_filtered_tenants_query_admin_access(mock_admin_user):
    """Test admin can query all tenants."""
    query = build_filtered_tenants_query(mock_admin_user, None, None, None)
    assert query is not None


# =============================================================================
# build_unassigned_tenants_query Tests
# =============================================================================

def test_build_unassigned_tenants_query_no_search(mock_user):
    """Test building unassigned tenants query without search."""
    query = build_unassigned_tenants_query(mock_user, None)
    assert query is not None


def test_build_unassigned_tenants_query_with_search(mock_user):
    """Test building unassigned tenants query with search."""
    query = build_unassigned_tenants_query(mock_user, "john")
    assert query is not None


def test_build_unassigned_tenants_query_admin(mock_admin_user):
    """Test admin can query all unassigned tenants."""
    query = build_unassigned_tenants_query(mock_admin_user, None)
    assert query is not None


# =============================================================================
# enrich_tenants_with_details Tests
# =============================================================================

@pytest.mark.asyncio  
async def test_enrich_tenants_with_details_success(mock_session, mock_tenant, mock_property, mock_unit, mock_lease):
    """Test successful tenant enrichment with details."""
    # Setup tenant with current property assignment
    mock_tenant.current_property_id = 1
    
    # Setup property unit query with real values
    mock_unit.id = 1
    mock_unit.name = "Unit A"
    mock_unit.property = mock_property  # Ensure unit points to the real property mock
    unit_result = MagicMock()
    unit_result.scalar_one_or_none.return_value = mock_unit
    
    # Setup property query with real values
    mock_property.id = 1
    mock_property.name = "Test Property"
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    # Setup lease query
    lease_result = MagicMock()
    lease_result.scalars.return_value.all.return_value = [mock_lease]
    
    # Mock empty results for new queries (maintenance, payments, invoices)
    empty_maintenance = MagicMock()
    empty_maintenance.scalars.return_value.all.return_value = []
    empty_payments = MagicMock()
    empty_payments.scalars.return_value.all.return_value = []
    empty_invoices = MagicMock()
    empty_invoices.scalars.return_value.all.return_value = []
    
    # Configure session execute to return different results for different queries
    # Order: unit_query, lease_query, maintenance_query, payment_query, invoice_query
    mock_session.execute.side_effect = [
        unit_result,          # For unit query
        lease_result,         # For lease query
        empty_maintenance,    # For maintenance query
        empty_payments,       # For payment query
        empty_invoices,       # For invoice query
    ]
    
    # Mock model_dump for tenant
    mock_tenant.model_dump.return_value = {
        'id': 1,
        'tenant_type': TenantType.INDIVIDUAL,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': 1,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
    
    # Mock lease property and unit with real values
    mock_lease.id = 1
    mock_lease.start_date = datetime.now(timezone.utc).date()
    mock_lease.end_date = datetime.now(timezone.utc).date()
    mock_lease.status = "ACTIVE"
    mock_lease.property_id = 1
    mock_lease.unit_id = 1
    mock_lease.property = mock_property
    mock_lease.unit = mock_unit
    
    # Patch the schema validation to avoid MagicMock issues
    with patch('Backend.api.tenants.service.PropertyResponseSimple.model_validate') as mock_prop_validate, \
         patch('Backend.api.tenants.service.UnitResponseSimple.model_validate') as mock_unit_validate, \
         patch('Backend.api.tenants.service.LeaseResponseSimple.model_validate') as mock_lease_validate, \
         patch('Backend.api.tenants.service.MaintenanceRequestResponse.model_validate') as mock_maint_validate, \
         patch('Backend.api.tenants.service.PaymentResponse.model_validate') as mock_pay_validate, \
         patch('Backend.api.tenants.service.InvoiceResponse.model_validate') as mock_inv_validate:
        
        # Mock validation returns
        mock_prop_validate.return_value = MagicMock(id=1, name="Test Property")
        mock_unit_validate.return_value = MagicMock(id=1, name="Unit A", property=MagicMock(id=1, name="Test Property"))
        mock_lease_validate.return_value = MagicMock(id=1, start_date=datetime.now().date(), end_date=datetime.now().date())
        mock_maint_validate.return_value = []  # Return empty lists for new data
        mock_pay_validate.return_value = []
        mock_inv_validate.return_value = []
        
        # Act
        result = await enrich_tenants_with_details([mock_tenant], mock_session)
        
        # Assert
        assert len(result) == 1
        assert result[0].id == 1
        mock_session.execute.assert_called()


@pytest.mark.asyncio
async def test_enrich_tenants_with_details_no_current_property(mock_session, mock_tenant, mock_lease):
    """Test tenant enrichment when no current property assigned."""
    # Setup tenant with no current property
    mock_tenant.current_property_id = None
    
    # Setup lease query
    lease_result = MagicMock()
    lease_result.scalars.return_value.all.return_value = [mock_lease]
    
    # Mock empty results for new queries (maintenance, payments, invoices)
    empty_maintenance = MagicMock()
    empty_maintenance.scalars.return_value.all.return_value = []
    empty_payments = MagicMock()
    empty_payments.scalars.return_value.all.return_value = []
    empty_invoices = MagicMock()
    empty_invoices.scalars.return_value.all.return_value = []
    
    # Order: lease_query, maintenance_query, payment_query, invoice_query
    mock_session.execute.side_effect = [
        lease_result,         # For lease query
        empty_maintenance,    # For maintenance query
        empty_payments,       # For payment query
        empty_invoices,       # For invoice query
    ]
    
    # Mock model_dump for tenant
    mock_tenant.model_dump.return_value = {
        'id': 1,
        'tenant_type': TenantType.INDIVIDUAL,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': None,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
    
    # Mock lease property and unit with real values
    mock_lease.id = 1
    mock_lease.start_date = datetime.now(timezone.utc).date()
    mock_lease.end_date = datetime.now(timezone.utc).date()
    mock_lease.status = "ACTIVE"
    mock_lease.property_id = 1
    mock_lease.unit_id = 1
    mock_lease_property = MagicMock()
    mock_lease_property.id = 1
    mock_lease_property.name = "Test Property"
    mock_lease_unit = MagicMock()
    mock_lease_unit.id = 1
    mock_lease_unit.name = "Unit A"
    mock_lease_unit.property = mock_lease_property
    mock_lease.property = mock_lease_property
    mock_lease.unit = mock_lease_unit
    
    # Patch the schema validation to avoid MagicMock issues
    with patch('Backend.api.tenants.service.LeaseResponseSimple.model_validate') as mock_lease_validate, \
         patch('Backend.api.tenants.service.PropertyResponseSimple.model_validate') as mock_prop_validate, \
         patch('Backend.api.tenants.service.UnitResponseSimple.model_validate') as mock_unit_validate, \
         patch('Backend.api.tenants.service.MaintenanceRequestResponse.model_validate') as mock_maint_validate, \
         patch('Backend.api.tenants.service.PaymentResponse.model_validate') as mock_pay_validate, \
         patch('Backend.api.tenants.service.InvoiceResponse.model_validate') as mock_inv_validate:
        
        # Mock validation returns
        mock_lease_validate.return_value = MagicMock(id=1, start_date=datetime.now().date(), end_date=datetime.now().date(), status="ACTIVE")
        mock_prop_validate.return_value = MagicMock(id=1, name="Test Property")
        mock_unit_validate.return_value = MagicMock(id=1, name="Unit A", property=MagicMock(id=1, name="Test Property"))
        
        # Act
        result = await enrich_tenants_with_details([mock_tenant], mock_session)
        
        # Assert
        assert len(result) == 1
        assert result[0].id == 1


@pytest.mark.asyncio
async def test_enrich_tenants_with_details_company_tenant(mock_session, mock_company_tenant):
    """Test tenant enrichment for company tenant."""
    # Setup company tenant
    mock_company_tenant.current_property_id = None
    
    # Setup lease query to return empty
    lease_result = MagicMock()
    lease_result.scalars.return_value.all.return_value = []
    
    mock_session.execute.return_value = lease_result
    
    # Mock model_dump for company tenant
    mock_company_tenant.model_dump.return_value = {
        'id': 2,
        'tenant_type': TenantType.COMPANY,
        'company_name': 'Tech Corp',
        'contact_person': 'Jane Smith',
        'email': 'contact@techcorp.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': None,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
    
    # Act
    result = await enrich_tenants_with_details([mock_company_tenant], mock_session)
    
    # Assert
    assert len(result) == 1
    assert result[0].id == 2


@pytest.mark.asyncio
async def test_enrich_tenants_with_details_empty_list(mock_session):
    """Test tenant enrichment with empty tenant list."""
    # Act
    result = await enrich_tenants_with_details([], mock_session)
    
    # Assert
    assert len(result) == 0


@pytest.mark.asyncio
async def test_enrich_tenants_with_details_no_active_lease_fallback(mock_session, mock_tenant, mock_lease):
    """Test tenant enrichment uses most recent lease when no active lease."""
    # Setup tenant with no current property
    mock_tenant.current_property_id = None
    
    # Setup lease query with inactive lease
    mock_lease.id = 1
    mock_lease.start_date = datetime.now(timezone.utc).date()
    mock_lease.end_date = datetime.now(timezone.utc).date()
    mock_lease.status = "EXPIRED"
    mock_lease.property_id = 1
    mock_lease.unit_id = 1
    mock_lease_property = MagicMock()
    mock_lease_property.id = 1
    mock_lease_property.name = "Test Property"
    mock_lease_unit = MagicMock()
    mock_lease_unit.id = 1
    mock_lease_unit.name = "Unit A"
    mock_lease_unit.property = mock_lease_property
    mock_lease.property = mock_lease_property
    mock_lease.unit = mock_lease_unit
    lease_result = MagicMock()
    lease_result.scalars.return_value.all.return_value = [mock_lease]
    
    mock_session.execute.return_value = lease_result
    
    # Mock model_dump for tenant
    mock_tenant.model_dump.return_value = {
        'id': 1,
        'tenant_type': TenantType.INDIVIDUAL,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': None,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
    
    # Mock lease property and unit
    mock_lease.property = MagicMock()
    mock_lease.unit = MagicMock()
    
    # Patch the schema validation to avoid MagicMock issues
    with patch('Backend.api.tenants.service.LeaseResponseSimple.model_validate') as mock_lease_validate, \
         patch('Backend.api.tenants.service.PropertyResponseSimple.model_validate') as mock_prop_validate, \
         patch('Backend.api.tenants.service.UnitResponseSimple.model_validate') as mock_unit_validate, \
         patch('Backend.api.tenants.service.MaintenanceRequestResponse.model_validate') as mock_maint_validate, \
         patch('Backend.api.tenants.service.PaymentResponse.model_validate') as mock_pay_validate, \
         patch('Backend.api.tenants.service.InvoiceResponse.model_validate') as mock_inv_validate:
        
        # Mock validation returns
        mock_lease_validate.return_value = MagicMock(id=1, start_date=datetime.now().date(), end_date=datetime.now().date(), status="EXPIRED")
        mock_prop_validate.return_value = MagicMock(id=1, name="Test Property")
        mock_unit_validate.return_value = MagicMock(id=1, name="Unit A", property=MagicMock(id=1, name="Test Property"))
        
        # Act
        result = await enrich_tenants_with_details([mock_tenant], mock_session)
        
        # Assert
        assert len(result) == 1
        assert result[0].id == 1


# =============================================================================
# Additional Coverage Tests for Specific Missing Lines
# =============================================================================

@pytest.mark.asyncio
async def test_enrich_tenants_with_details_logging_warning_for_no_active_lease(mock_session, mock_tenant):
    """Test logging warning when tenant has no active lease - covers service.py lines 460-463."""
    # Setup tenant with no current property but with inactive leases
    mock_tenant.current_property_id = None
    
    # Setup lease query with only inactive lease
    mock_inactive_lease = MagicMock(spec=Lease)
    mock_inactive_lease.id = 1
    mock_inactive_lease.start_date = datetime.now(timezone.utc).date()
    mock_inactive_lease.end_date = datetime.now(timezone.utc).date()
    mock_inactive_lease.status = "EXPIRED"
    mock_inactive_lease.property_id = 1
    mock_inactive_lease.unit_id = 1
    mock_inactive_property = MagicMock()
    mock_inactive_property.id = 1
    mock_inactive_property.name = "Test Property"
    mock_inactive_unit = MagicMock()
    mock_inactive_unit.id = 1
    mock_inactive_unit.name = "Unit A"
    mock_inactive_unit.property = mock_inactive_property
    mock_inactive_lease.property = mock_inactive_property
    mock_inactive_lease.unit = mock_inactive_unit
    
    lease_result = MagicMock()
    lease_result.scalars.return_value.all.return_value = [mock_inactive_lease]
    mock_session.execute.return_value = lease_result
    
    # Mock model_dump for tenant
    mock_tenant.model_dump.return_value = {
        'id': 1,
        'tenant_type': TenantType.INDIVIDUAL,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': None,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
    
    # Mock logger.warning to verify it's called and patch schema validation
    with patch('Backend.api.tenants.service.logger.warning') as mock_logger, \
         patch('Backend.api.tenants.service.LeaseResponseSimple.model_validate') as mock_lease_validate, \
         patch('Backend.api.tenants.service.PropertyResponseSimple.model_validate') as mock_prop_validate, \
         patch('Backend.api.tenants.service.UnitResponseSimple.model_validate') as mock_unit_validate:
        
        # Mock validation returns
        mock_lease_validate.return_value = MagicMock(id=1, start_date=datetime.now().date(), end_date=datetime.now().date(), status="EXPIRED")
        mock_prop_validate.return_value = MagicMock(id=1, name="Test Property")
        mock_unit_validate.return_value = MagicMock(id=1, name="Unit A", property=MagicMock(id=1, name="Test Property"))
        
        # Act
        result = await enrich_tenants_with_details([mock_tenant], mock_session)
        
        # Assert
        assert len(result) == 1
        # Should have logged warning about no active lease (line 460-463)
        mock_logger.assert_called_once()
        args, kwargs = mock_logger.call_args
        assert "no active lease" in args[0]
        assert mock_tenant.id in args


@pytest.mark.asyncio
async def test_enrich_tenants_with_details_active_lease_found_no_warning(mock_session, mock_tenant):
    """Test no warning logged when active lease is found - covers active lease branch."""
    # Setup tenant with no current property but with active lease
    mock_tenant.current_property_id = None
    
    # Setup lease query with active lease
    mock_active_lease = MagicMock(spec=Lease)
    mock_active_lease.id = 1
    mock_active_lease.start_date = datetime.now(timezone.utc).date()
    mock_active_lease.end_date = datetime.now(timezone.utc).date()
    mock_active_lease.status = "ACTIVE"
    mock_active_lease.property_id = 1
    mock_active_lease.unit_id = 1
    mock_active_property = MagicMock()
    mock_active_property.id = 1
    mock_active_property.name = "Test Property"
    mock_active_unit = MagicMock()
    mock_active_unit.id = 1
    mock_active_unit.name = "Unit A"
    mock_active_unit.property = mock_active_property
    mock_active_lease.property = mock_active_property
    mock_active_lease.unit = mock_active_unit
    
    lease_result = MagicMock()
    lease_result.scalars.return_value.all.return_value = [mock_active_lease]
    mock_session.execute.return_value = lease_result
    
    # Mock model_dump for tenant
    mock_tenant.model_dump.return_value = {
        'id': 1,
        'tenant_type': TenantType.INDIVIDUAL,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': None,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
    
    # Mock logger.warning to verify it's NOT called and patch schema validation
    with patch('Backend.api.tenants.service.logger.warning') as mock_logger, \
         patch('Backend.api.tenants.service.LeaseResponseSimple.model_validate') as mock_lease_validate, \
         patch('Backend.api.tenants.service.PropertyResponseSimple.model_validate') as mock_prop_validate, \
         patch('Backend.api.tenants.service.UnitResponseSimple.model_validate') as mock_unit_validate:
        
        # Mock validation returns
        mock_lease_validate.return_value = MagicMock(id=1, start_date=datetime.now().date(), end_date=datetime.now().date(), status="ACTIVE")
        mock_prop_validate.return_value = MagicMock(id=1, name="Test Property")
        mock_unit_validate.return_value = MagicMock(id=1, name="Unit A", property=MagicMock(id=1, name="Test Property"))
        
        # Act
        result = await enrich_tenants_with_details([mock_tenant], mock_session)
        
        # Assert
        assert len(result) == 1
        # Should NOT have logged warning since active lease was found
        mock_logger.assert_not_called()


@pytest.mark.asyncio
async def test_enrich_tenants_with_details_unit_assignment_from_lease(mock_session, mock_tenant):
    """Test unit assignment from lease data - covers specific assignment lines."""
    # Setup tenant with current property and unit assignment
    mock_tenant.current_property_id = 1
    
    # Setup unit query
    mock_unit = MagicMock(spec=PropertyUnit)
    mock_unit.id = 1
    mock_unit.name = "Unit A"
    mock_unit.tenant_id = 1
    
    unit_result = MagicMock()
    unit_result.unique.return_value.scalar_one_or_none.return_value = mock_unit
    
    # Setup property query
    mock_property = MagicMock(spec=Property)
    mock_property.id = 1
    mock_property.name = "Test Property"
    
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    # Setup lease query
    mock_lease = MagicMock(spec=Lease)
    mock_lease.id = 1
    mock_lease.property = mock_property
    mock_lease.unit = mock_unit
    mock_lease.status = "ACTIVE"
    
    lease_result = MagicMock()
    lease_result.scalars.return_value.all.return_value = [mock_lease]
    
    # Mock empty results for new queries (maintenance, payments, invoices)
    empty_maintenance = MagicMock()
    empty_maintenance.scalars.return_value.all.return_value = []
    empty_payments = MagicMock()
    empty_payments.scalars.return_value.all.return_value = []
    empty_invoices = MagicMock()
    empty_invoices.scalars.return_value.all.return_value = []
    
    # Configure execute to return different results for different queries
    # Order: unit_query, lease_query, maintenance_query, payment_query, invoice_query
    mock_session.execute.side_effect = [
        unit_result,          # For unit query
        lease_result,         # For lease query
        empty_maintenance,    # For maintenance query
        empty_payments,       # For payment query
        empty_invoices,       # For invoice query
    ]
    
    # Mock model_dump for tenant
    mock_tenant.model_dump.return_value = {
        'id': 1,
        'tenant_type': TenantType.INDIVIDUAL,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': 1,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }
    
    # Patch the schema validation to avoid MagicMock issues
    with patch('Backend.api.tenants.service.PropertyResponseSimple.model_validate') as mock_prop_validate, \
         patch('Backend.api.tenants.service.UnitResponseSimple.model_validate') as mock_unit_validate, \
         patch('Backend.api.tenants.service.LeaseResponseSimple.model_validate') as mock_lease_validate:
        
        # Mock validation returns
        mock_prop_validate.return_value = MagicMock(id=1, name="Test Property")
        mock_unit_validate.return_value = MagicMock(id=1, name="Unit A", property=MagicMock(id=1, name="Test Property"))
        mock_lease_validate.return_value = MagicMock(id=1, start_date=datetime.now().date(), end_date=datetime.now().date(), status="ACTIVE")
        
        # Act
        result = await enrich_tenants_with_details([mock_tenant], mock_session)

        # Assert
        assert len(result) == 1
        tenant_response = result[0]
        assert tenant_response.id == 1


@pytest.mark.asyncio
async def test_enrich_tenants_with_details_lease_with_unit_processing(mock_session, mock_tenant):
    """Test lease processing when lease has unit - covers unit assignment in lease."""
    # Setup tenant with no current property
    mock_tenant.current_property_id = None

    # Setup lease with unit
    mock_property = MagicMock(spec=Property)
    mock_property.id = 1
    mock_property.name = "Test Property"

    mock_unit = MagicMock(spec=PropertyUnit)
    mock_unit.id = 1
    mock_unit.name = "Unit A"
    mock_unit.property = mock_property

    mock_lease = MagicMock(spec=Lease)
    mock_lease.id = 1
    mock_lease.start_date = datetime.now(timezone.utc).date()
    mock_lease.end_date = datetime.now(timezone.utc).date()
    mock_lease.status = "ACTIVE"
    mock_lease.property_id = 1
    mock_lease.unit_id = 1
    mock_lease.property = mock_property
    mock_lease.unit = mock_unit

    lease_result = MagicMock()
    lease_result.scalars().return_value.all.return_value = [mock_lease]
    mock_session.execute.return_value = lease_result

    # Mock model_dump for tenant
    mock_tenant.model_dump.return_value = {
        'id': 1,
        'tenant_type': TenantType.INDIVIDUAL,
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john.doe@example.com',
        'status': TenantStatus.ACTIVE,
        'landlord_id': uuid4(),
        'current_property_id': None,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
    }

    # Patch the schema validation to avoid MagicMock issues
    with patch('Backend.api.tenants.service.LeaseResponseSimple.model_validate') as mock_lease_validate, \
         patch('Backend.api.tenants.service.PropertyResponseSimple.model_validate') as mock_prop_validate, \
         patch('Backend.api.tenants.service.UnitResponseSimple.model_validate') as mock_unit_validate:

        # Mock validation returns
        mock_lease_validate.return_value = MagicMock(id=1, start_date=datetime.now().date(), end_date=datetime.now().date(), status="ACTIVE")
        mock_prop_validate.return_value = MagicMock(id=1, name="Test Property")
        mock_unit_validate.return_value = MagicMock(id=1, name="Unit A", property=MagicMock(id=1, name="Test Property"))

        # Act
        result = await enrich_tenants_with_details([mock_tenant], mock_session)

        # Assert
        assert len(result) == 1
        tenant_response = result[0]
        assert tenant_response.id == 1
