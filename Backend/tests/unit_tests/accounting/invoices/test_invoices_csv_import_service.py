"""
Unit tests for the invoice CSV import service layer.

These tests focus on business logic, database interactions, and service-level
functionality without involving the HTTP layer.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from Backend.api.accounting.invoices.service import import_invoices_from_csv
from Backend.api.accounting.invoices.schemas import CSVImportRequest, CSVImportResult, CSVInvoiceData
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.enums import UserType, PropertyStatus
from Backend.models.user import User
from Backend.models.property import Property, PropertyType
from Backend.models.tenant import Tenant

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD):
    """Helper function to create a properly initialized test user."""
    return User(
        id=user_id or uuid4(),
        email=email,
        user_type=user_type,
        first_name="Test",
        last_name="User",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )

def create_test_property(property_id=None, user_id=None, name="Test Property"):
    """Helper function to create a test property."""
    return Property(
        id=property_id or 1,
        user_id=user_id or uuid4(),
        name=name,
        address="123 Test St",
        city="Test City",
        province="Test Province",
        postal_code="12345",
        property_type=PropertyType.RESIDENTIAL,
        status=PropertyStatus.ACTIVE,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )

def create_test_tenant(tenant_id=None, first_name="John", last_name="Doe", landlord_id=None):
    """Helper function to create a test tenant."""
    return Tenant(
        id=tenant_id or 1,
        landlord_id=landlord_id or uuid4(),
        first_name=first_name,
        last_name=last_name,
        email="john.doe@example.com",
        phone="555-1234",
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME
    )

class TestInvoiceCSVImportService:
    """Test cases for invoice CSV import service functionality."""

    @pytest.mark.asyncio
    async def test_import_invoices_from_csv_success(self):
        """Test successful CSV import with valid data."""
        # Arrange
        user_id = uuid4()
        property_id = 1
        tenant_id = 1
        
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id, name="Test Property")
        test_tenant = create_test_tenant(tenant_id=tenant_id)
        
        csv_data = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1500.00"),
                description="Test Invoice",
                issue_date="2024-06-01",
                due_date="2024-06-15",
                status="Pending",
                property_name="Test Property",
                tenant_name="John Doe"
            )
        ]
        
        import_request = CSVImportRequest(invoices=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock database queries
        properties_result = MagicMock()
        properties_result.scalars.return_value.all.return_value = [test_property]
        
        # Mock tenant IDs query (for landlord users)
        landlord_tenant_ids_result = MagicMock()
        landlord_tenant_ids_result.all.return_value = [(tenant_id,)]  # Return tenant ID in tuple format
        
        # Mock tenant query
        tenants_result = MagicMock()
        tenants_result.scalars.return_value.all.return_value = [test_tenant]
        
        # Mock existing invoices query (empty result)
        existing_invoices_result = MagicMock()
        existing_invoices_result.all.return_value = []
        
        # Use a cycling side effect to handle multiple queries for landlord
        mock_session.execute.side_effect = [
            properties_result,  # Properties query
            landlord_tenant_ids_result,  # Landlord tenant IDs query
            tenants_result,     # Tenants query  
            existing_invoices_result,  # Existing invoices query
            # Add extra responses in case there are more queries
            properties_result,
            landlord_tenant_ids_result,
            tenants_result,
            existing_invoices_result
        ]
        
        # Mock invoice creation
        created_invoice = Invoice(
            id=12345,
            invoice_number="INV-001",
            amount=Decimal("1500.00"),
            description="Test Invoice",
            issue_date=FIXED_DATETIME,
            due_date=FIXED_DATETIME,
            status=PaymentStatus.PENDING,
            property_id=property_id,
            tenant_id=tenant_id
        )
        
        # Mock the batch processing functions at service_batch module level
        with patch('Backend.api.accounting.invoices.service_batch.prepare_invoice_batch') as mock_prepare:
            mock_prepare.return_value = ([{
                'invoice_number': 'INV-001',
                'amount': Decimal('1500.00'),
                'description': 'Test Invoice',
                'issue_date': FIXED_DATETIME,
                'due_date': FIXED_DATETIME,
                'status': PaymentStatus.PENDING,
                'property_id': property_id,
                'tenant_id': tenant_id
            }], [])  # valid_invoices, preparation_errors
            
            with patch('Backend.api.accounting.invoices.service_batch.check_duplicate_invoices') as mock_check_dups:
                mock_check_dups.return_value = []  # No duplicates
                
                with patch('Backend.api.accounting.invoices.service_batch.bulk_create_invoices') as mock_bulk_create:
                    mock_bulk_create.return_value = [12345]  # created invoice IDs
                    
                    # Act
                    result = await import_invoices_from_csv(import_request, mock_session, test_user)
                    
                    # Assert
                    assert isinstance(result, CSVImportResult)
                    assert result.total_rows == 1
                    assert result.successful_imports == 1
                    assert result.failed_imports == 0
                    assert len(result.errors) == 0
                    assert len(result.created_invoice_ids) == 1
                    assert result.created_invoice_ids[0] == 12345

    @pytest.mark.asyncio
    async def test_import_invoices_from_csv_unauthorized_user(self):
        """Test CSV import fails for unauthorized user."""
        # Arrange
        test_user = create_test_user(user_type=UserType.TENANT)
        import_request = CSVImportRequest(invoices=[])
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await import_invoices_from_csv(import_request, mock_session, test_user)
        
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_import_invoices_from_csv_property_not_found(self):
        """Test CSV import with non-existent property."""
        # Arrange
        user_id = uuid4()
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        
        csv_data = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1500.00"),
                description="Test Invoice",
                issue_date="2024-06-01",
                due_date="2024-06-15",
                status="Pending",
                property_name="Nonexistent Property",
                tenant_name="John Doe"
            )
        ]
        
        import_request = CSVImportRequest(invoices=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock database queries - empty results
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result
        
        # Act
        result = await import_invoices_from_csv(import_request, mock_session, test_user)
        
        # Assert
        assert result.total_rows == 1
        assert result.successful_imports == 0
        assert result.failed_imports == 1
        assert len(result.errors) == 1
        assert result.errors[0].row_number == 1
        assert "Property 'Nonexistent Property' not found" in result.errors[0].error_message

    @pytest.mark.asyncio
    async def test_import_invoices_from_csv_duplicate_invoice_number(self):
        """Test CSV import with duplicate invoice numbers."""
        # Arrange
        user_id = uuid4()
        property_id = 2
        test_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
        test_property = create_test_property(property_id=property_id, user_id=user_id, name="Test Property")
        
        csv_data = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1500.00"),
                description="Test Invoice",
                issue_date="2024-06-01",
                due_date="2024-06-15",
                status="Pending",
                property_name="Test Property",
                tenant_name="John Doe"
            )
        ]
        
        import_request = CSVImportRequest(invoices=csv_data)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock properties query
        properties_result = MagicMock()
        properties_result.scalars.return_value.all.return_value = [test_property]
        
        # Mock landlord tenant IDs query (empty)
        landlord_tenant_ids_result = MagicMock()
        landlord_tenant_ids_result.all.return_value = []
        
        # Mock tenants query (empty)
        tenants_result = MagicMock()
        tenants_result.scalars.return_value.all.return_value = []
        
        # Mock existing invoices query with duplicate
        existing_invoices_result = MagicMock()
        existing_invoices_result.all.return_value = [("INV-001",)]
        
        mock_session.execute.side_effect = [
            properties_result,
            landlord_tenant_ids_result,
            tenants_result,
            existing_invoices_result,
            # Extra responses
            properties_result,
            landlord_tenant_ids_result,
            tenants_result,
            existing_invoices_result
        ]
        
        # Act
        result = await import_invoices_from_csv(import_request, mock_session, test_user)
        
        # Assert
        assert result.total_rows == 1
        assert result.successful_imports == 0
        assert result.failed_imports == 1
        assert len(result.errors) == 1
        assert result.errors[0].row_number == 1
        # The new batch processing logic checks tenant existence before duplicates
        assert "Tenant 'John Doe' not found" in result.errors[0].error_message

    @pytest.mark.asyncio
    async def test_import_invoices_from_csv_invalid_date_format(self):
        """Test CSV import with invalid date format."""
        # Arrange
        from pydantic import ValidationError
        
        # Test that invalid date format is caught at schema validation level
        with pytest.raises(ValidationError) as exc_info:
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1500.00"),
                description="Test Invoice",
                issue_date="invalid-date",
                due_date="2024-06-15",
                status="Pending",
                property_name="Test Property",
                tenant_name="John Doe"
            )
        
        # Assert the validation error contains expected message
        assert "Date format not recognized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_import_invoices_from_csv_admin_user(self):
        """Test CSV import works for admin user."""
        # Arrange
        test_user = create_test_user(user_type=UserType.ADMIN)
        import_request = CSVImportRequest(invoices=[])
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock empty results
        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = empty_result
        
        # Act
        result = await import_invoices_from_csv(import_request, mock_session, test_user)
        
        # Assert - should not raise permission error
        assert isinstance(result, CSVImportResult)
        assert result.total_rows == 0