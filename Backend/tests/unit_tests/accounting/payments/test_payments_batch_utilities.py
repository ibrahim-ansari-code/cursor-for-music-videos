"""
Unit tests for payment batch processing utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.accounting.payments.service_batch import (
    bulk_create_payments,
    prepare_payment_batch,
    normalize_payment_method,
    normalize_payment_status,
    check_duplicate_payments
)
from Backend.api.accounting.payments.schemas import CSVPaymentData
from Backend.models.accounting.payment import PaymentMethod
from Backend.models.accounting.common import PaymentStatus

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


class TestBulkCreatePayments:
    """Test cases for bulk_create_payments function."""

    @pytest.mark.asyncio
    async def test_bulk_create_payments_success(self):
        """Test successful bulk creation of payments."""
        # Arrange
        payments_data = [
            {
                "lease_id": 1,
                "tenant_id": 1,
                "amount": 1000.00,
                "payment_date": FIXED_DATETIME,
                "payment_method": PaymentMethod.BANK_TRANSFER.value,
                "status": PaymentStatus.PAID.value,
                "transaction_reference": "REF001",
                "description": "Monthly rent",
                "created_at": FIXED_DATETIME,
                "updated_at": FIXED_DATETIME
            },
            {
                "lease_id": 2,
                "tenant_id": 2,
                "amount": 500.00,
                "payment_date": FIXED_DATETIME,
                "payment_method": PaymentMethod.CREDIT_CARD.value,
                "status": PaymentStatus.PENDING.value,
                "transaction_reference": "REF002",
                "description": "Utilities",
                "created_at": FIXED_DATETIME,
                "updated_at": FIXED_DATETIME
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(1,), (2,)]
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await bulk_create_payments(payments_data, mock_session)
        
        # Assert
        assert result == [1, 2]
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_payments_empty_list(self):
        """Test bulk creation with empty list returns empty result."""
        # Arrange
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Act
        result = await bulk_create_payments([], mock_session)
        
        # Assert
        assert result == []
        mock_session.execute.assert_not_called()


class TestPreparePaymentBatch:
    """Test cases for prepare_payment_batch function."""

    def test_prepare_payment_batch_success_with_tenant(self):
        """Test successful preparation of payment batch with tenant name."""
        # Arrange
        csv_payments = [
            CSVPaymentData(
                amount=Decimal("1000.00"),
                payment_date="2024-06-01",
                payment_method="Bank Transfer",
                status="paid",
                transaction_reference="REF001",
                description="Monthly rent",
                tenant_name="John Doe"
            )
        ]
        
        properties = {}
        tenants = {
            "john doe": MagicMock(id=1, full_name="John Doe")
        }
        active_leases = {
            1: 10  # tenant_id 1 -> lease_id 10
        }
        
        # Act
        valid_payments, errors = prepare_payment_batch(
            csv_payments,
            properties,
            tenants,
            active_leases,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_payments) == 1
        assert len(errors) == 0
        assert valid_payments[0]["lease_id"] == 10
        assert valid_payments[0]["tenant_id"] == 1
        assert valid_payments[0]["amount"] == 1000.00

    def test_prepare_payment_batch_tenant_not_found(self):
        """Test preparation with tenant not found."""
        # Arrange
        csv_payments = [
            CSVPaymentData(
                amount=Decimal("1000.00"),
                payment_date="2024-06-01",
                tenant_name="Unknown Tenant"
            )
        ]
        
        properties = {}
        tenants = {}
        active_leases = {}
        
        # Act
        valid_payments, errors = prepare_payment_batch(
            csv_payments,
            properties,
            tenants,
            active_leases,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_payments) == 0
        assert len(errors) == 1
        assert "Tenant 'Unknown Tenant' not found" in errors[0]["error_message"]

    def test_prepare_payment_batch_tenant_no_active_lease(self):
        """Test preparation with tenant having no active lease."""
        # Arrange
        csv_payments = [
            CSVPaymentData(
                amount=Decimal("1000.00"),
                payment_date="2024-06-01",
                tenant_name="John Doe"
            )
        ]
        
        tenants = {
            "john doe": MagicMock(id=1, full_name="John Doe")
        }
        active_leases = {}  # No active lease for tenant_id 1
        
        # Act
        valid_payments, errors = prepare_payment_batch(
            csv_payments,
            {},
            tenants,
            active_leases,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_payments) == 0
        assert len(errors) == 1
        assert "Tenant 'John Doe' has no active lease" in errors[0]["error_message"]

    def test_prepare_payment_batch_reduction_validation(self):
        """Test validation of reduction amount."""
        # Arrange
        csv_payments = [
            CSVPaymentData(
                amount=Decimal("1000.00"),
                payment_date="2024-06-01",
                tenant_name="John Doe",
                reduction_amount=Decimal("1500.00"),  # Greater than amount
                reduction_reason="Discount"
            )
        ]
        
        tenants = {
            "john doe": MagicMock(id=1)
        }
        active_leases = {1: 10}
        
        # Act
        valid_payments, errors = prepare_payment_batch(
            csv_payments,
            {},
            tenants,
            active_leases,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_payments) == 0
        assert len(errors) == 1
        assert "Reduction amount cannot be greater than payment amount" in errors[0]["error_message"]

    def test_prepare_payment_batch_reduction_requires_reason(self):
        """Test that reduction amount requires a reason."""
        # Arrange
        csv_payments = [
            CSVPaymentData(
                amount=Decimal("1000.00"),
                payment_date="2024-06-01",
                tenant_name="John Doe",
                reduction_amount=Decimal("100.00"),
                # No reduction_reason provided
            )
        ]
        
        tenants = {
            "john doe": MagicMock(id=1)
        }
        active_leases = {1: 10}
        
        # Act
        valid_payments, errors = prepare_payment_batch(
            csv_payments,
            {},
            tenants,
            active_leases,
            "user123",
            "LANDLORD"
        )
        
        # Assert
        assert len(valid_payments) == 0
        assert len(errors) == 1
        assert "Reduction reason is required when reduction amount is provided" in errors[0]["error_message"]


class TestNormalizePaymentMethod:
    """Test cases for normalize_payment_method function."""

    def test_normalize_credit_card(self):
        """Test normalizing credit card payment method."""
        assert normalize_payment_method("credit card") == PaymentMethod.CREDIT_CARD
        assert normalize_payment_method("Credit Card") == PaymentMethod.CREDIT_CARD

    def test_normalize_bank_methods(self):
        """Test normalizing bank-related payment methods."""
        assert normalize_payment_method("bank transfer") == PaymentMethod.BANK_TRANSFER
        assert normalize_payment_method("wire transfer") == PaymentMethod.WIRE_TRANSFER
        assert normalize_payment_method("direct deposit") == PaymentMethod.DIRECT_DEPOSIT

    def test_normalize_check_variants(self):
        """Test normalizing check/cheque variants."""
        assert normalize_payment_method("check") == PaymentMethod.CHECK
        assert normalize_payment_method("cheque") == PaymentMethod.CHECK

    def test_normalize_interac(self):
        """Test normalizing Interac e-Transfer."""
        assert normalize_payment_method("interac e-transfer") == PaymentMethod.INTERAC_E_TRANSFER

    def test_normalize_unknown_method(self):
        """Test unknown payment method defaults to OTHER."""
        assert normalize_payment_method("bitcoin") == PaymentMethod.OTHER
        assert normalize_payment_method("unknown") == PaymentMethod.OTHER

    def test_normalize_none_method(self):
        """Test None payment method defaults to OTHER."""
        assert normalize_payment_method(None) == PaymentMethod.OTHER
        assert normalize_payment_method("") == PaymentMethod.OTHER


class TestNormalizePaymentStatus:
    """Test cases for normalize_payment_status function."""

    def test_normalize_pending(self):
        """Test normalizing pending status."""
        assert normalize_payment_status("pending") == PaymentStatus.PENDING
        assert normalize_payment_status("processing") == PaymentStatus.PENDING

    def test_normalize_paid(self):
        """Test normalizing paid status."""
        assert normalize_payment_status("paid") == PaymentStatus.PAID
        assert normalize_payment_status("completed") == PaymentStatus.PAID

    def test_normalize_partial(self):
        """Test normalizing partial payment status."""
        assert normalize_payment_status("partial") == PaymentStatus.PARTIAL
        assert normalize_payment_status("partially_paid") == PaymentStatus.PARTIAL

    def test_normalize_cancelled(self):
        """Test normalizing cancelled status."""
        assert normalize_payment_status("cancelled") == PaymentStatus.CANCELLED

    def test_normalize_void(self):
        """Test normalizing void/failed status."""
        assert normalize_payment_status("void") == PaymentStatus.VOID
        assert normalize_payment_status("failed") == PaymentStatus.VOID

    def test_normalize_unknown_status(self):
        """Test unknown status defaults to PENDING."""
        assert normalize_payment_status("unknown") == PaymentStatus.PENDING

    def test_normalize_none_status(self):
        """Test None status defaults to PENDING."""
        assert normalize_payment_status(None) == PaymentStatus.PENDING


class TestCheckDuplicatePayments:
    """Test cases for check_duplicate_payments function."""

    @pytest.mark.asyncio
    async def test_check_duplicates_with_transaction_ref(self):
        """Test finding duplicate payments with transaction reference."""
        # Arrange
        payments_data = [
            {
                "lease_id": 1,
                "amount": 1000.00,
                "payment_date": FIXED_DATETIME,
                "transaction_reference": "REF001"
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = 123  # Existing payment found
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await check_duplicate_payments(payments_data, mock_session)
        
        # Assert
        assert result == [0]  # Payment is duplicate
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_duplicates_without_transaction_ref(self):
        """Test finding duplicate payments without transaction reference."""
        # Arrange
        payments_data = [
            {
                "lease_id": 1,
                "amount": 1000.00,
                "payment_date": FIXED_DATETIME,
                "transaction_reference": None
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None  # No duplicate
        mock_session.execute.return_value = mock_result
        
        # Act
        result = await check_duplicate_payments(payments_data, mock_session)
        
        # Assert
        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_duplicates_none_found(self):
        """Test when no duplicate payments are found."""
        # Arrange
        payments_data = [
            {
                "lease_id": 1,
                "amount": 1000.00,
                "payment_date": FIXED_DATETIME,
                "transaction_reference": "NEW-REF"
            },
            {
                "lease_id": 2,
                "amount": 500.00,
                "payment_date": FIXED_DATETIME,
                "transaction_reference": "NEW-REF-2"
            }
        ]
        
        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_session.execute.side_effect = [mock_result, mock_result]
        
        # Act
        result = await check_duplicate_payments(payments_data, mock_session)
        
        # Assert
        assert result == []
        assert mock_session.execute.call_count == 2