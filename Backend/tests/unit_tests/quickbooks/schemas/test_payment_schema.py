"""
Unit tests for QuickBooks PaymentSchema class.

Tests data transformation between Brikli Payment and QuickBooks Payment formats.
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC, date
from decimal import Decimal

from Backend.api.quickbooks.schemas.payment import PaymentSchema
from Backend.models.accounting.payment import Payment, PaymentMethod, PaymentStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.tenant import Tenant

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
FIXED_DATE = date(2024, 6, 1)


def create_test_payment(**kwargs):
    """Helper function to create a test payment."""
    defaults = {
        "amount": Decimal("1200.00"),
        "payment_date": FIXED_DATE,
        "payment_method": PaymentMethod.BANK_TRANSFER,  # Enum not string
        "description": "Monthly Rent Payment",
        "status": PaymentStatus.PAID,  # Correct field name
        "lease_id": uuid4(),
        "tenant_id": uuid4(),
        "created_at": FIXED_DATETIME,
        "updated_at": FIXED_DATETIME
    }
    defaults.update(kwargs)
    return Payment(**defaults)


class TestPaymentValidation:
    """Test payment validation for QuickBooks sync."""

    def test_validate_payment_valid(self):
        """Test validation of valid payment."""
        payment = create_test_payment()
        tenant = Tenant(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            quickbooks_id="qb_123",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )

        errors = PaymentSchema.validate_for_quickbooks(payment, tenant)
        # Validation returns Dict[str, str], empty dict means valid
        assert errors == {}

    def test_validate_payment_zero_amount(self):
        """Test validation with zero amount."""
        payment = create_test_payment(amount=Decimal("0.00"))
        tenant = Tenant(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            quickbooks_id="qb_123",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )

        errors = PaymentSchema.validate_for_quickbooks(payment, tenant)
        # Should have amount error
        assert "amount" in errors


class TestToQuickBooks:
    """Test conversion from Payment to QuickBooks format."""

    def test_to_quickbooks_basic(self):
        """Test basic payment to QuickBooks conversion."""
        payment = create_test_payment()
        tenant = Tenant(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            quickbooks_id="qb_customer_123",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )

        result = PaymentSchema.to_quickbooks(payment, tenant)

        assert "Payment" in result
        qb_payment = result["Payment"]

        assert qb_payment["TxnDate"] == "2024-06-01"
        assert qb_payment["TotalAmt"] == 1200.00
        assert qb_payment["CustomerRef"]["value"] == "qb_customer_123"


class TestFromQuickBooks:
    """Test conversion from QuickBooks Payment to Brikli format."""

    def test_from_quickbooks_basic(self):
        """Test basic QuickBooks to payment conversion."""
        qb_payment = {
            "Id": "123",
            "TxnDate": "2024-06-01",
            "TotalAmt": 1200.00,
            "CustomerRef": {"value": "cust_123"},
            "PaymentMethodRef": {"name": "BankTransfer"}
        }
        
        # Create test lease and tenant
        lease = Lease(
            id=uuid4(),
            tenant_id=uuid4(),
            property_id=1,
            status=LeaseStatus.ACTIVE,
            start_date=FIXED_DATE,
            monthly_rent=Decimal("1200.00"),
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )
        tenant = Tenant(
            id=uuid4(),
            user_id=uuid4(),
            email="test@example.com",
            first_name="Test",
            last_name="User",
            quickbooks_id="cust_123",
            created_at=FIXED_DATETIME,
            updated_at=FIXED_DATETIME
        )

        # Actual signature: from_quickbooks(qb_payment, lease, tenant)
        result = PaymentSchema.from_quickbooks(qb_payment, lease, tenant)

        assert result.quickbooks_id == "123"
        assert result.amount == Decimal("1200.00")
        assert result.payment_method == PaymentMethod.BANK_TRANSFER