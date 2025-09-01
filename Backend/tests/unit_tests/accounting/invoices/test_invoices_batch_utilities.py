"""
Unit tests for invoice batch processing utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.invoices.service_batch import (
    bulk_create_invoices,
    prepare_invoice_batch,
    normalize_payment_status,
    check_duplicate_invoices
)
from Backend.api.accounting.invoices.schemas import CSVInvoiceData
from Backend.models.accounting.common import PaymentStatus

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestBulkCreateInvoices:
    """Test cases for bulk_create_invoices function."""

    @pytest.mark.asyncio
    async def test_bulk_create_invoices_success(self):
        """Test successful bulk creation of invoices."""
        # Arrange
        invoices_data = [
            {
                "invoice_number": "INV-001",
                "amount": 1000.00,
                "description": "Monthly rent",
                "issue_date": FIXED_DATETIME,
                "due_date": FIXED_DATETIME,
                "status": PaymentStatus.PENDING.value,
                "property_id": 1,
                "tenant_id": 1,
                "created_at": FIXED_DATETIME,
                "updated_at": FIXED_DATETIME
            },
            {
                "invoice_number": "INV-002",
                "amount": 500.00,
                "description": "Utilities",
                "issue_date": FIXED_DATETIME,
                "due_date": FIXED_DATETIME,
                "status": PaymentStatus.PAID.value,
                "property_id": 2,
                "tenant_id": 2,
                "created_at": FIXED_DATETIME,
                "updated_at": FIXED_DATETIME
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,), (2,)]
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await bulk_create_invoices(invoices_data, mock_session)
        
        # Assert
        assert result == [1, 2]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_invoices_empty_list(self):
        """Test bulk creation with empty list returns empty result."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Act
        result = await bulk_create_invoices([], mock_session)
        
        # Assert
        assert result == []
        mock_session.execute.assert_not_called()


class TestPrepareInvoiceBatch:
    """Test cases for prepare_invoice_batch function."""

    def test_prepare_invoice_batch_success(self):
        """Test successful preparation of invoice batch."""
        # Arrange
        csv_invoices = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1000.00"),
                description="Monthly rent",
                issue_date="2024-06-01",
                due_date="2024-06-30",
                status="pending",
                property_name="Property A",
                tenant_name="John Doe"
            )
        ]
        
        properties = {
            "property a": MagicMock(id=1, name="Property A")
        }
        
        tenants = {
            "john doe": MagicMock(id=1, full_name="John Doe")
        }
        
        # Act
        valid_invoices, errors = prepare_invoice_batch(
            csv_invoices,
            properties,
            tenants,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_invoices) == 1
        assert len(errors) == 0
        assert valid_invoices[0]["property_id"] == 1
        assert valid_invoices[0]["tenant_id"] == 1
        assert valid_invoices[0]["invoice_number"] == "INV-001"
        assert valid_invoices[0]["amount"] == Decimal("1000.00")

    def test_prepare_invoice_batch_property_not_found(self):
        """Test preparation with property not found."""
        # Arrange
        csv_invoices = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1000.00"),
                description="Monthly rent",
                issue_date="2024-06-01",
                due_date="2024-06-30",
                property_name="Nonexistent Property"
            )
        ]
        
        properties = {}
        tenants = {}
        
        # Act
        valid_invoices, errors = prepare_invoice_batch(
            csv_invoices,
            properties,
            tenants,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_invoices) == 0
        assert len(errors) == 1
        assert errors[0]["row_number"] == 1
        assert "Property 'Nonexistent Property' not found" in errors[0]["error_message"]

    def test_prepare_invoice_batch_tenant_not_found(self):
        """Test preparation with tenant not found."""
        # Arrange
        csv_invoices = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1000.00"),
                description="Monthly rent",
                issue_date="2024-06-01",
                due_date="2024-06-30",
                property_name="Property A",
                tenant_name="Unknown Tenant"
            )
        ]
        
        properties = {
            "property a": MagicMock(id=1, name="Property A")
        }
        tenants = {}
        
        # Act
        valid_invoices, errors = prepare_invoice_batch(
            csv_invoices,
            properties,
            tenants,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_invoices) == 0
        assert len(errors) == 1
        assert "Tenant 'Unknown Tenant' not found" in errors[0]["error_message"]

    def test_prepare_invoice_batch_invalid_date_order(self):
        """Test preparation with due date before issue date."""
        # Arrange
        csv_invoices = [
            CSVInvoiceData(
                invoice_number="INV-001",
                amount=Decimal("1000.00"),
                description="Monthly rent",
                issue_date="2024-06-30",
                due_date="2024-06-01",  # Due date before issue date
                property_name="Property A"
            )
        ]
        
        properties = {
            "property a": MagicMock(id=1, name="Property A")
        }
        
        # Act
        valid_invoices, errors = prepare_invoice_batch(
            csv_invoices,
            properties,
            {},
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_invoices) == 0
        assert len(errors) == 1
        assert "Due date cannot be earlier than issue date" in errors[0]["error_message"]


class TestNormalizePaymentStatus:
    """Test cases for normalize_payment_status function."""

    def test_normalize_pending(self):
        """Test normalizing pending status."""
        assert normalize_payment_status("pending") == PaymentStatus.PENDING
        assert normalize_payment_status("PENDING") == PaymentStatus.PENDING

    def test_normalize_paid(self):
        """Test normalizing paid status."""
        assert normalize_payment_status("paid") == PaymentStatus.PAID
        assert normalize_payment_status("completed") == PaymentStatus.PAID

    def test_normalize_overdue(self):
        """Test normalizing overdue status."""
        assert normalize_payment_status("overdue") == PaymentStatus.OVERDUE

    def test_normalize_partial(self):
        """Test normalizing partial payment status."""
        assert normalize_payment_status("partial") == PaymentStatus.PARTIAL
        assert normalize_payment_status("partially_paid") == PaymentStatus.PARTIAL

    def test_normalize_unknown_status(self):
        """Test unknown status defaults to PENDING."""
        assert normalize_payment_status("unknown") == PaymentStatus.PENDING
        assert normalize_payment_status("") == PaymentStatus.PENDING

    def test_normalize_none_status(self):
        """Test None status defaults to PENDING."""
        assert normalize_payment_status(None) == PaymentStatus.PENDING


class TestCheckDuplicateInvoices:
    """Test cases for check_duplicate_invoices function."""

    @pytest.mark.asyncio
    async def test_check_duplicates_found(self):
        """Test finding duplicate invoices by invoice number."""
        # Arrange
        invoices_data = [
            {
                "invoice_number": "INV-001",
                "amount": 1000.00,
                "property_id": 1
            },
            {
                "invoice_number": "INV-002",
                "amount": 500.00,
                "property_id": 2
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        
        # First invoice is duplicate, second is not
        mock_result1 = MagicMock()
        mock_result1.scalar.return_value = 123  # Existing ID found
        
        mock_result2 = MagicMock()
        mock_result2.scalar.return_value = None  # No duplicate
        
        mock_session.execute.side_effect = [mock_result1, mock_result2]
        
        # Act
        result = await check_duplicate_invoices(invoices_data, mock_session)
        
        # Assert
        assert result == [0]  # First invoice is duplicate
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_check_duplicates_none_found(self):
        """Test when no duplicate invoices are found."""
        # Arrange
        invoices_data = [
            {
                "invoice_number": "INV-NEW-001",
                "amount": 1000.00,
                "property_id": 1
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await check_duplicate_invoices(invoices_data, mock_session)
        
        # Assert
        assert result == []
        mock_session.execute.assert_called_once()