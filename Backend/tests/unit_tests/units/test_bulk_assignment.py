"""
Unit tests for bulk assignment service layer functionality.

Simplified test structure with 3 logical groupings:
- CSV bulk assignment functionality
- Bulk tenant assignment functionality  
- Validation and edge cases
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError

from Backend.api.units.service import UnitService
from Backend.api.units.schemas import (
    CSVBulkAssignRequest, CSVBulkAssignResponse, CSVAssignmentRow,
    BulkAssignmentRequest, BulkAssignmentResponse, CSVAssignmentError
)
from Backend.api.leases.schemas import LeaseCreate
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.models.lease import Lease

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestFixtures:
    """Test fixtures and setup utilities."""

    @staticmethod
    def create_mock_session():
        """Create a properly configured mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()
        return session

    @staticmethod
    def create_mock_user(is_admin: bool = False):
        """Create a mock user with specified permissions."""
        user = MagicMock()
        user.id = str(uuid4())
        user.email = "test@example.com"
        user.is_admin = is_admin
        return user

    @staticmethod
    def create_mock_property(user_id: Optional[str] = None):
        """Create a mock property."""
        property_obj = MagicMock()
        property_obj.id = 1
        property_obj.name = "Test Property"
        property_obj.user_id = str(user_id) if user_id is not None else str(uuid4())
        return property_obj

    @staticmethod
    def create_mock_units(count: int = 3, available: bool = True):
        """Create mock units."""
        units = []
        for i in range(1, count + 1):
            unit = MagicMock()
            unit.id = i
            unit.unit_number = f"10{i}"
            unit.name = f"Unit {i}"
            unit.tenant_id = None if available else 999
            unit.property_id = 1
            unit.is_rented = not available
            units.append(unit)
        return units

    @staticmethod
    def create_mock_tenants(count: int = 3):
        """Create mock tenants."""
        tenants = []
        for i in range(1, count + 1):
            tenant = MagicMock()
            tenant.id = i
            tenant.email = f"tenant{i}@example.com"
            tenant.first_name = f"Tenant{i}"
            tenant.last_name = "Test"
            tenants.append(tenant)
        return tenants

    @staticmethod
    def create_mock_lease(lease_id: int = 1):
        """Create a mock lease."""
        lease = MagicMock()
        lease.id = lease_id
        return lease

    @staticmethod
    def get_future_date(days: int = 30):
        """Get a future date for testing."""
        return (datetime.now() + timedelta(days=days)).date()

    @staticmethod
    def get_future_date_str(days: int = 30):
        """Get a future date string for testing."""
        return (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

    @staticmethod
    def _create_scalar_result_mock(value):
        """Create a mock result for scalar_one_or_none() pattern."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = value
        return result_mock
    
    @staticmethod
    def _create_list_result_mock(value):
        """Create a mock result for unique().scalars().all() pattern."""
        result_mock = MagicMock()
        unique_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = value if isinstance(value, list) else [value] if value else []
        unique_mock.scalars.return_value = scalars_mock
        result_mock.unique.return_value = unique_mock
        return result_mock
    
    @staticmethod
    def _get_next_return_value(return_values):
        """Safely get the next return value from the list."""
        if not hasattr(return_values, '__iter__') or isinstance(return_values, (str, bytes)):
            return return_values
        
        if not isinstance(return_values, list):
            return_values = list(return_values)
        
        try:
            return return_values.pop(0) if return_values else None
        except (IndexError, AttributeError):
            return None

    @staticmethod
    def setup_session_execute_mock(session, return_values):
        """
        Setup session.execute() mock to properly handle async patterns.

        Supports both patterns:
        1. result.scalar_one_or_none() for single objects
        2. result.unique().scalars().all() for lists
        """
        async def mock_execute(*args, **kwargs):
            value = TestFixtures._get_next_return_value(return_values)
            
            # Create a mock result that supports both patterns
            result_mock = MagicMock()
            result_mock.scalar_one_or_none.return_value = value
            
            # Configure for unique().scalars().all() pattern
            unique_mock = MagicMock()
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = value if isinstance(value, list) else [value] if value else []
            unique_mock.scalars.return_value = scalars_mock
            result_mock.unique.return_value = unique_mock

            return result_mock

        session.execute.side_effect = mock_execute


@pytest.fixture
def fixtures():
    """Provide test fixtures."""
    return TestFixtures


class TestCSVBulkAssignment:
    """Test CSV bulk assignment functionality including business logic, security, and error handling."""

    async def test_csv_success_complete_workflow(self, fixtures):
        """Test successful CSV bulk assignment with complete workflow."""
        # Setup
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        units = fixtures.create_mock_units(2, available=True)
        tenants = fixtures.create_mock_tenants(2)
        future_date = fixtures.get_future_date_str()

        # Setup session execute calls
        fixtures.setup_session_execute_mock(session, [
            property_obj,  # Property lookup
            units[0],      # First unit lookup
            tenants[0],    # First tenant lookup
            units[1],      # Second unit lookup
            tenants[1]     # Second tenant lookup
        ])

        # Mock lease creation
        with patch('Backend.api.units.service.create_lease') as mock_create_lease:
            mock_lease = fixtures.create_mock_lease()
            mock_create_lease.return_value = mock_lease

            # Create test data
            assignments = [
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="tenant1@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1200.00")
                ),
                CSVAssignmentRow(
                    unit_number="102",
                    tenant_email="tenant2@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1300.00"),
                    security_deposit=Decimal("1300.00")
                )
            ]
            request = CSVBulkAssignRequest(assignments=assignments)

            # Execute
            result = await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=user
            )

            # Assertions
            assert isinstance(result, CSVBulkAssignResponse)
            assert result.total_rows == 2
            assert result.successful_assignments == 2
            assert result.failed_assignments == 0
            assert len(result.errors) == 0
            assert len(result.created_leases) == 2
            assert mock_create_lease.call_count == 2

    async def test_csv_unit_not_found(self, fixtures):
        """Test CSV assignment with unit not found error handling."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        future_date = fixtures.get_future_date_str()

        # Setup: property exists, unit doesn't
        fixtures.setup_session_execute_mock(session, [
            property_obj,  # Property lookup
            None,          # Unit not found
        ])

        assignments = [
            CSVAssignmentRow(
                unit_number="999",
                tenant_email="tenant@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        ]
        request = CSVBulkAssignRequest(assignments=assignments)

        # Execute
        result = await UnitService.bulk_assign_from_csv(
            property_id=1,
            csv_data=request,
            session=session,
            current_user=user
        )

        # Assertions
        assert result.total_rows == 1
        assert result.successful_assignments == 0
        assert result.failed_assignments == 1
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "unit_not_found"
        assert "999" in result.errors[0].unit_number

    async def test_csv_tenant_not_found(self, fixtures):
        """Test CSV assignment with tenant not found error handling."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        units = fixtures.create_mock_units(1)
        future_date = fixtures.get_future_date_str()

        # Setup: property and unit exist, tenant doesn't
        fixtures.setup_session_execute_mock(session, [
            property_obj,  # Property lookup
            units[0],      # Unit lookup
            None,          # Tenant not found
        ])

        assignments = [
            CSVAssignmentRow(
                unit_number="101",
                tenant_email="nonexistent@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        ]
        request = CSVBulkAssignRequest(assignments=assignments)

        # Execute
        result = await UnitService.bulk_assign_from_csv(
            property_id=1,
            csv_data=request,
            session=session,
            current_user=user
        )

        # Assertions
        assert result.total_rows == 1
        assert result.successful_assignments == 0
        assert result.failed_assignments == 1
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "tenant_not_found"
        assert "nonexistent@example.com" in result.errors[0].error_message

    async def test_csv_unit_occupied(self, fixtures):
        """Test CSV assignment with occupied unit error handling."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        tenants = fixtures.create_mock_tenants(1)
        future_date = fixtures.get_future_date_str()

        # Create occupied unit
        occupied_unit = fixtures.create_mock_units(1, available=False)[0]

        # Setup mocks
        fixtures.setup_session_execute_mock(session, [
            property_obj,     # Property lookup
            occupied_unit,    # Unit lookup (occupied)
            tenants[0]        # Tenant lookup
        ])

        assignments = [
            CSVAssignmentRow(
                unit_number="101",
                tenant_email="tenant1@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        ]
        request = CSVBulkAssignRequest(assignments=assignments)

        # Execute
        result = await UnitService.bulk_assign_from_csv(
            property_id=1,
            csv_data=request,
            session=session,
            current_user=user
        )

        # Assertions
        assert result.total_rows == 1
        assert result.successful_assignments == 0
        assert result.failed_assignments == 1
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "unit_occupied"

    async def test_csv_lease_creation_failure(self, fixtures):
        """Test CSV assignment with lease creation failure."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        units = fixtures.create_mock_units(1)
        tenants = fixtures.create_mock_tenants(1)
        future_date = fixtures.get_future_date_str()

        # Setup mocks
        fixtures.setup_session_execute_mock(session, [
            property_obj,  # Property lookup
            units[0],      # Unit lookup
            tenants[0]     # Tenant lookup
        ])

        # Mock lease creation to fail
        with patch('Backend.api.units.service.create_lease') as mock_create_lease:
            mock_create_lease.side_effect = HTTPException(
                status_code=400, detail="Invalid property ID"
            )

            assignments = [
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="tenant1@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1200.00")
                )
            ]
            request = CSVBulkAssignRequest(assignments=assignments)

            # Execute
            result = await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=user
            )

            # Assertions
            assert result.total_rows == 1
            assert result.successful_assignments == 0
            assert result.failed_assignments == 1
            assert len(result.errors) == 1
            assert "failed to create lease" in result.errors[0].error_message.lower(
            )

    async def test_csv_mixed_success_failure(self, fixtures):
        """Test CSV assignment with mixed success and failure scenarios."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        units = fixtures.create_mock_units(2)
        tenants = fixtures.create_mock_tenants(2)
        future_date = fixtures.get_future_date_str()

        # Make second unit occupied
        units[1].tenant_id = 999
        units[1].is_rented = True

        # Setup mocks
        fixtures.setup_session_execute_mock(session, [
            property_obj,  # Property lookup
            units[0],      # First unit lookup (available)
            tenants[0],    # First tenant lookup
            units[1],      # Second unit lookup (occupied)
            tenants[1]     # Second tenant lookup
        ])

        # Mock lease creation for first unit only
        with patch('Backend.api.units.service.create_lease') as mock_create_lease:
            mock_lease = fixtures.create_mock_lease()
            mock_create_lease.return_value = mock_lease

            assignments = [
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="tenant1@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1200.00")
                ),
                CSVAssignmentRow(
                    unit_number="102",
                    tenant_email="tenant2@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1300.00"),
                    security_deposit=Decimal("1300.00")
            )
            ]
            request = CSVBulkAssignRequest(assignments=assignments)

            # Execute
            result = await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=user
            )

            # Assertions
            assert result.total_rows == 2
            assert result.successful_assignments == 1
            assert result.failed_assignments == 1
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "unit_occupied"
            assert len(result.created_leases) == 1
            assert mock_create_lease.call_count == 1

    async def test_csv_permission_denied_non_owner(self, fixtures):
        """Test CSV assignment with permission denied for non-owner."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        # Property owned by different user
        property_obj = fixtures.create_mock_property(uuid4())
        future_date = fixtures.get_future_date_str()

        fixtures.setup_session_execute_mock(session, [property_obj])

        assignments = [
            CSVAssignmentRow(
                unit_number="101",
                tenant_email="tenant@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        ]
        request = CSVBulkAssignRequest(assignments=assignments)

        # Execute and assert exception
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=user
            )

        assert exc_info.value.status_code == 403
        assert "permission" in str(exc_info.value.detail).lower()

    async def test_csv_admin_override_permission(self, fixtures):
        """Test CSV assignment with admin user overriding permissions."""
        session = fixtures.create_mock_session()
        admin_user = fixtures.create_mock_user(is_admin=True)
        # Property owned by different user
        property_obj = fixtures.create_mock_property(uuid4())
        units = fixtures.create_mock_units(1)
        tenants = fixtures.create_mock_tenants(1)
        future_date = fixtures.get_future_date_str()

        fixtures.setup_session_execute_mock(session, [
            property_obj,  # Property lookup
            units[0],      # Unit lookup
            tenants[0]     # Tenant lookup
        ])

        # Mock lease creation
        with patch('Backend.api.units.service.create_lease') as mock_create_lease:
            mock_lease = fixtures.create_mock_lease()
            mock_create_lease.return_value = mock_lease

            assignments = [
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="tenant1@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1200.00")
                )
            ]
            request = CSVBulkAssignRequest(assignments=assignments)

            # Execute - should succeed for admin
            result = await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=admin_user
            )

            # Assertions
            assert result.successful_assignments == 1
            assert result.failed_assignments == 0

    async def test_csv_property_not_found(self, fixtures):
        """Test CSV assignment with property not found."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        future_date = fixtures.get_future_date_str()

        fixtures.setup_session_execute_mock(
            session, [None])  # Property not found

        assignments = [
            CSVAssignmentRow(
                unit_number="101",
                tenant_email="tenant@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        ]
        request = CSVBulkAssignRequest(assignments=assignments)

        # Execute and assert exception
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.bulk_assign_from_csv(
                property_id=999,
                csv_data=request,
                session=session,
                current_user=user
            )

        assert exc_info.value.status_code == 404
        assert "Property not found" in str(exc_info.value.detail)

    async def test_csv_large_dataset_workflow(self, fixtures):
        """Test CSV workflow with larger dataset (50 assignments)."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        future_date = fixtures.get_future_date_str()

        # Create larger dataset
        assignments = []
        units = fixtures.create_mock_units(50)
        tenants = fixtures.create_mock_tenants(50)

        # Setup session execute responses
        responses = [property_obj]  # Property lookup
        for i in range(50):
            # Unit and tenant for each assignment
            responses.extend([units[i], tenants[i]])
            assignments.append(
                CSVAssignmentRow(
                    unit_number=f"Unit{i:03d}",
                    tenant_email=f"tenant{i}@example.com",
                    lease_start_date=future_date,
                                    monthly_rent=Decimal(f"{1200 + i * 10}.00"),
                security_deposit=Decimal(f"{1200 + i * 10}.00")
            )
            )

        fixtures.setup_session_execute_mock(session, responses)

        # Mock lease creation
        with patch('Backend.api.units.service.create_lease') as mock_create_lease:
            mock_lease = fixtures.create_mock_lease()
            mock_create_lease.return_value = mock_lease

            request = CSVBulkAssignRequest(assignments=assignments)

            # Execute
            result = await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=user
            )

            # Verify large dataset handling
            assert result.total_rows == 50
            assert result.successful_assignments == 50
            assert result.failed_assignments == 0
            assert len(result.created_leases) == 50
            assert mock_create_lease.call_count == 50

    async def test_csv_partial_failure_recovery(self, fixtures):
        """Test recovery from partial failures in CSV processing."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        property_obj = fixtures.create_mock_property(user.id)
        units = fixtures.create_mock_units(3)
        tenants = fixtures.create_mock_tenants(3)
        future_date = fixtures.get_future_date_str()

        # Setup property and tenant lookups only
        fixtures.setup_session_execute_mock(session, [
            property_obj,  # Property lookup
            tenants[0],    # First tenant lookup (success) 
            tenants[2]     # Third tenant lookup (success)
        ])

        # Mock unit lookups directly using patch
        def mock_find_unit_by_number(session, property_id, unit_number):
            if unit_number == "101":
                return units[0]
            elif unit_number == "999":
                return None  # Unit not found
            elif unit_number == "103": 
                return units[2]
            return None

        # Mock lease creation for successful assignments
        with patch('Backend.api.units.service.UnitService._find_unit_by_number', side_effect=mock_find_unit_by_number), \
             patch('Backend.api.units.service.create_lease') as mock_create_lease:
            mock_lease = fixtures.create_mock_lease()
            mock_create_lease.return_value = mock_lease

            assignments = [
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="tenant1@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1200.00")
                ),
                CSVAssignmentRow(
                    unit_number="999",  # Non-existent unit
                    tenant_email="tenant2@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1300.00"),
                    security_deposit=Decimal("1300.00")
            ),
                CSVAssignmentRow(
                    unit_number="103",
                    tenant_email="tenant3@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1400.00"),
                    security_deposit=Decimal("1400.00")
            )
            ]
            request = CSVBulkAssignRequest(assignments=assignments)

            # Execute
            result = await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=user
            )

            # Verify partial success
            assert result.total_rows == 3
            assert result.successful_assignments == 2
            assert result.failed_assignments == 1
            assert len(result.errors) == 1
            assert result.errors[0].unit_number == "999"
            assert len(result.created_leases) == 2
            assert mock_create_lease.call_count == 2


class TestBulkTenantAssignment:
    """Test bulk tenant assignment functionality for multi-unit operations."""

    async def test_bulk_assign_success_complete_workflow(self, fixtures):
        """Test successful bulk tenant assignment with complete workflow."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        units = fixtures.create_mock_units(2)
        tenant = fixtures.create_mock_tenants(1)[0]
        future_date = fixtures.get_future_date()

        # Setup mocks for the specific query patterns used in bulk_assign_tenant
        fixtures.setup_session_execute_mock(session, [tenant])  # Tenant lookup

        # Mock UnitService.get_unit_or_404 for each unit
        with patch.object(UnitService, 'get_unit_or_404') as mock_get_unit:
            mock_get_unit.side_effect = units

            # Mock lease creation
            with patch('Backend.api.leases.service.create_lease') as mock_create_lease:
                mock_lease = fixtures.create_mock_lease()
                mock_create_lease.return_value = mock_lease

                # Create test data
                end_date = future_date + timedelta(days=365)
                bulk_data = BulkAssignmentRequest(
                    unit_ids=[1, 2],
                    tenant_id=1,
                    lease_start_date=future_date,
                    end_date=end_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1000.00"),
                    late_fee_amount=Decimal("50.00"),
                    late_fee_after_days=5,
                    special_terms="Standard lease terms"
                )

                # Execute
                result = await UnitService.bulk_assign_tenant(
                    bulk_data=bulk_data,
                    session=session,
                    current_user=user
                )

                # Assertions
                assert isinstance(result, BulkAssignmentResponse)
                assert result.total_units == 2
                assert result.successful_assignments == 2
                assert result.failed_assignments == 0
                assert len(result.errors) == 0
                assert len(result.created_leases) == 2
                assert mock_create_lease.call_count == 2
                assert mock_get_unit.call_count == 2

    async def test_bulk_assign_tenant_not_found(self, fixtures):
        """Test bulk assignment with tenant not found."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        future_date = fixtures.get_future_date()

        # Setup: tenant not found
        fixtures.setup_session_execute_mock(session, [None])

        end_date = future_date + timedelta(days=365)
        bulk_data = BulkAssignmentRequest(
            unit_ids=[1, 2],
            tenant_id=999,
            lease_start_date=future_date,
            end_date=end_date,
            monthly_rent=Decimal("1200.00"),
            security_deposit=Decimal("1000.00"),
            late_fee_amount=Decimal("50.00"),
            late_fee_after_days=5,
            special_terms="Standard lease terms"
        )

        # Execute and assert exception
        with pytest.raises(HTTPException) as exc_info:
            await UnitService.bulk_assign_tenant(
                bulk_data=bulk_data,
                session=session,
                current_user=user
            )

        assert exc_info.value.status_code == 404
        assert "Tenant" in str(exc_info.value.detail)
        assert "999" in str(exc_info.value.detail)

    async def test_bulk_assign_partial_success_with_occupied_units(self, fixtures):
        """Test bulk assignment with mix of available and occupied units."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        tenant = fixtures.create_mock_tenants(1)[0]
        future_date = fixtures.get_future_date()

        # Create mix of available and occupied units
        available_unit = fixtures.create_mock_units(1, available=True)[0]
        occupied_unit = fixtures.create_mock_units(1, available=False)[0]
        occupied_unit.id = 2

        fixtures.setup_session_execute_mock(session, [tenant])  # Tenant lookup

        # Mock UnitService.get_unit_or_404
        with patch.object(UnitService, 'get_unit_or_404') as mock_get_unit:
            mock_get_unit.side_effect = [available_unit, occupied_unit]

            # Mock lease creation
            with patch('Backend.api.leases.service.create_lease') as mock_create_lease:
                mock_lease = fixtures.create_mock_lease()
                mock_create_lease.return_value = mock_lease

                end_date = future_date + timedelta(days=365)
                bulk_data = BulkAssignmentRequest(
                    unit_ids=[1, 2],
                    tenant_id=1,
                    lease_start_date=future_date,
                    end_date=end_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1000.00"),
                    late_fee_amount=Decimal("50.00"),
                    late_fee_after_days=5,
                    special_terms="Standard lease terms"
                )

                # Execute
                result = await UnitService.bulk_assign_tenant(
                    bulk_data=bulk_data,
                    session=session,
                    current_user=user
                )

                # Assertions
                assert result.total_units == 2
                assert result.successful_assignments == 1
                assert result.failed_assignments == 1
                assert len(result.errors) == 1
                assert result.errors[0].error_type == "unit_occupied"
                assert len(result.created_leases) == 1
                assert mock_create_lease.call_count == 1  # Only for available unit


class TestBulkAssignmentValidation:
    """Test validation, edge cases, performance boundaries, and integration scenarios."""

    def test_csv_assignment_row_email_validation_edge_cases(self, fixtures):
        """Test CSV assignment row email validation edge cases."""
        future_date = fixtures.get_future_date_str()

        # Test definitely invalid email formats
        invalid_emails = [
            "notanemail",
            "test@",
            "@example.com",
            "test@.com",
            "test@example",
            "test.example.com",
            "",  # Empty string
            " ",  # Just space
            "test@"  # No domain
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email=email,
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1200.00")
                )
            assert "email" in str(exc_info.value).lower(
            ) or "field required" in str(exc_info.value).lower()

    def test_csv_assignment_row_date_validation_comprehensive(self, fixtures):
        """Test CSV assignment row date validation comprehensively."""
        # Test various invalid date formats
        invalid_dates = [
            "invalid-date",
            "2024-13-01",  # Invalid month
            "2024-01-32",  # Invalid day
            "24-01-01",    # Wrong year format
            "01/01/24",    # Ambiguous format
            "",            # Empty string
            "2024-1-1",    # No zero padding
        ]

        for date_str in invalid_dates:
            with pytest.raises(ValidationError):
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="test@example.com",
                    lease_start_date=date_str,  # type: ignore # Intentionally testing invalid string dates
                    monthly_rent=Decimal("1200.00")
                )

    def test_csv_assignment_row_monetary_validation_edge_cases(self, fixtures):
        """Test CSV assignment row monetary validation edge cases."""
        future_date = fixtures.get_future_date_str()

        # Test invalid monetary values
        invalid_amounts = [
            Decimal("-100.00"),  # Negative
            Decimal("0.00"),     # Zero
            Decimal("-0.01"),    # Negative small
        ]

        for amount in invalid_amounts:
            with pytest.raises(ValidationError) as exc_info:
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="test@example.com",
                    lease_start_date=future_date,
                    monthly_rent=amount,
                    security_deposit=amount
                )
            assert "greater than 0" in str(exc_info.value)

    def test_bulk_assignment_request_boundary_testing(self, fixtures):
        """Test bulk assignment request boundary conditions."""
        future_date = fixtures.get_future_date()
        end_date = future_date + timedelta(days=365)

        # Test minimum valid values
        min_valid_request = BulkAssignmentRequest(
            unit_ids=[1],  # Minimum 1 unit
            tenant_id=1,   # Minimum positive ID
            lease_start_date=future_date,
            end_date=end_date,
            monthly_rent=Decimal("0.01"),  # Minimum positive rent
            security_deposit=Decimal("0.01"),  # Minimum positive deposit
            late_fee_amount=Decimal("0.00"),  # Minimum zero late fee
            late_fee_after_days=0,  # Minimum zero days
            special_terms=""  # Empty string
        )
        assert min_valid_request.unit_ids == [1]

        # Test maximum valid values
        max_unit_ids = list(range(1, 1001))  # Maximum 1000 units
        max_valid_request = BulkAssignmentRequest(
            unit_ids=max_unit_ids,
            tenant_id=999999,  # Large positive ID
            lease_start_date=future_date,
            end_date=end_date,
            monthly_rent=Decimal("99999.99"),  # Large rent
            security_deposit=Decimal("99999.99"),  # Large deposit
            late_fee_amount=Decimal("9999.99"),  # Large late fee
            late_fee_after_days=999,  # Large days
            special_terms="x" * 1000  # Maximum length string
        )
        assert len(max_valid_request.unit_ids) == 1000

    def test_csv_bulk_assign_request_size_limits(self, fixtures):
        """Test CSV bulk assignment request size limits."""
        future_date = fixtures.get_future_date_str()

        # Test maximum valid size (1000 assignments)
        max_assignments = []
        for i in range(1000):
            max_assignments.append(
                CSVAssignmentRow(
                    unit_number=f"Unit{i:04d}",
                    tenant_email=f"tenant{i}@example.com",
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1200.00")
                )
            )

        valid_request = CSVBulkAssignRequest(assignments=max_assignments)
        assert len(valid_request.assignments) == 1000

        # Test over-limit size (1001 assignments)
        over_limit_assignments = max_assignments + [
            CSVAssignmentRow(
                unit_number="ExtraUnit",
                tenant_email="extra@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        ]

        with pytest.raises(ValidationError) as exc_info:
            CSVBulkAssignRequest(assignments=over_limit_assignments)
        assert "at most 1000 items" in str(exc_info.value)

    def test_date_relationship_validation_comprehensive(self, fixtures):
        """Test comprehensive date relationship validation."""
        base_date = fixtures.get_future_date()

        # Test various invalid date relationships
        invalid_combinations = [
            # End date same as start date
            (base_date, base_date),
            # End date before start date
            (base_date, base_date - timedelta(days=1)),
            (base_date, base_date - timedelta(days=365)),
            # Start date in past
            ((datetime.now() - timedelta(days=1)).date(), base_date),
        ]

        for start_date, end_date in invalid_combinations:
            with pytest.raises(ValidationError):
                BulkAssignmentRequest(
                    unit_ids=[1, 2, 3],
                    tenant_id=1,
                    lease_start_date=start_date,
                    end_date=end_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=Decimal("1000.00"),
                    late_fee_amount=Decimal("50.00"),
                    late_fee_after_days=5,
                    special_terms="Standard lease terms"
                )

    def test_field_length_validation_comprehensive(self, fixtures):
        """Test comprehensive field length validation."""
        future_date = fixtures.get_future_date()
        end_date = future_date + timedelta(days=365)

        # Test special_terms length limit
        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(
                unit_ids=[1, 2, 3],
                tenant_id=1,
                lease_start_date=future_date,
                end_date=end_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1000.00"),
                late_fee_amount=Decimal("50.00"),
                late_fee_after_days=5,
                special_terms="x" * 1001  # Over 1000 character limit
            )
        assert "at most 1000 characters" in str(exc_info.value)

        # Test unit_number length in CSV
        future_date_str = fixtures.get_future_date_str()
        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(
                unit_number="",  # Empty unit number
                tenant_email="test@example.com",
                lease_start_date=future_date_str,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        assert "at least 1 character" in str(exc_info.value)

    def test_email_normalization_and_validation(self, fixtures):
        """Test email normalization and comprehensive validation."""
        future_date = fixtures.get_future_date_str()

        # Test email normalization to lowercase
        test_cases = [
            ("TEST@EXAMPLE.COM", "test@example.com"),
            ("Test@Example.Com", "test@example.com"),
            ("tEsT@eXaMpLe.CoM", "test@example.com"),
        ]

        for input_email, expected_email in test_cases:
            row = CSVAssignmentRow(
                unit_number="101",
                tenant_email=input_email,
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
            assert row.tenant_email == expected_email

    def test_decimal_precision_validation(self, fixtures):
        """Test decimal precision handling for monetary values."""
        future_date = fixtures.get_future_date_str()

        # Test various decimal precisions
        valid_amounts = [
            Decimal("1200.00"),
            Decimal("1200.99"),
            Decimal("1200.01"),
            Decimal("0.01"),
            Decimal("99999.99"),
        ]

        for amount in valid_amounts:
            row = CSVAssignmentRow(
                unit_number="101",
                tenant_email="test@example.com",
                lease_start_date=future_date,
                monthly_rent=amount,
                security_deposit=amount
            )
            assert row.monthly_rent == amount

    def test_concurrent_validation_scenarios(self, fixtures):
        """Test scenarios that might occur with concurrent operations."""
        future_date = fixtures.get_future_date()
        end_date = future_date + timedelta(days=365)

        # Test duplicate unit IDs in same request
        bulk_data = BulkAssignmentRequest(
            unit_ids=[1, 2, 2, 3],  # Duplicate unit ID
            tenant_id=1,
            lease_start_date=future_date,
            end_date=end_date,
            monthly_rent=Decimal("1200.00"),
            security_deposit=Decimal("1000.00"),
            late_fee_amount=Decimal("50.00"),
            late_fee_after_days=5,
            special_terms="Standard lease terms"
        )
        # Should be valid - duplicates will be handled by business logic
        assert 2 in bulk_data.unit_ids
        assert bulk_data.unit_ids.count(2) == 2

    async def test_transaction_rollback_behavior(self, fixtures):
        """Test transaction rollback behavior on critical failures."""
        session = fixtures.create_mock_session()
        user = fixtures.create_mock_user()
        future_date = fixtures.get_future_date_str()

        # Simulate database error during property lookup
        session.execute.side_effect = IntegrityError(
            "Database constraint violation", {}, Exception())

        assignments = [
            CSVAssignmentRow(
                unit_number="101",
                tenant_email="tenant@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=Decimal("1200.00")
            )
        ]
        request = CSVBulkAssignRequest(assignments=assignments)

        # Execute and verify exception handling - IntegrityError should bubble up
        # since bulk assignment methods don't have top-level exception handling
        with pytest.raises(IntegrityError) as exc_info:
            await UnitService.bulk_assign_from_csv(
                property_id=1,
                csv_data=request,
                session=session,
                current_user=user
            )

        assert "Database constraint violation" in str(exc_info.value)

    def test_schema_interoperability(self, fixtures):
        """Test interoperability between different schema types."""
        future_date = fixtures.get_future_date()
        future_date_str = fixtures.get_future_date_str()
        end_date = future_date + timedelta(days=365)

        # Test that CSV and bulk request schemas handle similar data consistently
        csv_row = CSVAssignmentRow(
            unit_number="101",
            tenant_email="tenant@example.com",
            lease_start_date=future_date_str,
            monthly_rent=Decimal("1200.00"),
            security_deposit=Decimal("1200.00")
        )

        bulk_request = BulkAssignmentRequest(
            unit_ids=[1, 2, 3],
            tenant_id=1,
            lease_start_date=future_date,
            end_date=end_date,
            monthly_rent=Decimal("1200.00"),
            security_deposit=Decimal("1000.00"),
            late_fee_amount=Decimal("50.00"),
            late_fee_after_days=5,
            special_terms="Standard lease terms"
        )

        # Both should handle the same monetary precision
        assert csv_row.monthly_rent == bulk_request.monthly_rent
        assert isinstance(csv_row.monthly_rent, Decimal)
        assert isinstance(bulk_request.monthly_rent, Decimal)

        # Both should validate email formats consistently
        assert "@" in csv_row.tenant_email
        assert csv_row.tenant_email == csv_row.tenant_email.lower()
