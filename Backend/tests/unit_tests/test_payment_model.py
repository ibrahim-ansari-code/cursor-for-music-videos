"""Unit tests for the Payment model."""
import pytest
from decimal import Decimal
from datetime import datetime
from pydantic import ValidationError

from Backend.models.accounting.payment import Payment, PaymentMethod
from Backend.models.accounting.common import PaymentStatus
from Backend.utils.datetime_utils import utc_now


class TestPaymentModel:
    """Tests for the Payment model."""
    
    def test_create_payment_valid(self):
        """Test creating a valid payment."""
        payment = Payment(
            amount=Decimal("1000.00"),
            payment_date=utc_now(),
            status=PaymentStatus.PAID,
            payment_method=PaymentMethod.BANK_TRANSFER,
            description="Rent payment",
            lease_id=1,
            tenant_id=1
        )
        
        assert payment.amount == Decimal("1000.00")
        assert payment.status == PaymentStatus.PAID
        assert payment.payment_method == PaymentMethod.BANK_TRANSFER
    
    def test_create_payment_with_valid_reduction(self):
        """Test creating a payment with valid reduction amount."""
        payment = Payment(
            amount=Decimal("1000.00"),
            reduction_amount=Decimal("100.00"),  # Valid: reduction < amount
            reduction_reason="First-time tenant discount",
            payment_date=utc_now(),
            status=PaymentStatus.PAID,
            payment_method=PaymentMethod.CREDIT_CARD,
            lease_id=1,
            tenant_id=1
        )
        
        assert payment.amount == Decimal("1000.00")
        assert payment.reduction_amount == Decimal("100.00")
        assert payment.reduction_reason == "First-time tenant discount"
    
    def test_create_payment_reduction_equals_amount(self):
        """Test creating a payment where reduction equals amount (100% discount)."""
        payment = Payment(
            amount=Decimal("500.00"),
            reduction_amount=Decimal("500.00"),  # Valid: reduction = amount
            reduction_reason="Full waiver due to maintenance issues",
            payment_date=utc_now(),
            status=PaymentStatus.PAID,
            payment_method=PaymentMethod.OTHER,
            lease_id=1,
            tenant_id=1
        )
        
        assert payment.amount == Decimal("500.00")
        assert payment.reduction_amount == Decimal("500.00")
    
    def test_create_payment_reduction_exceeds_amount(self):
        """Test that reduction_amount cannot exceed payment amount."""
        with pytest.raises(ValidationError) as excinfo:
            # First, create the model instance
            payment_data = {
                "amount": Decimal("1000.00"),
                "reduction_amount": Decimal("1200.00"),
                "reduction_reason": "Invalid reduction",
                "payment_date": utc_now(),
                "status": PaymentStatus.PAID,
                "payment_method": PaymentMethod.CASH,
                "lease_id": 1,
                "tenant_id": 1
            }
            # Then, explicitly validate it
            Payment.model_validate(payment_data)
        
        assert "Reduction amount cannot exceed the payment amount" in str(excinfo.value)
    
    def test_create_payment_zero_reduction(self):
        """Test creating a payment with zero reduction amount."""
        payment = Payment(
            amount=Decimal("1500.00"),
            reduction_amount=Decimal("0.00"),
            payment_date=utc_now(),
            status=PaymentStatus.PAID,
            payment_method=PaymentMethod.CHECK,
            lease_id=1,
            tenant_id=1
        )
        
        assert payment.amount == Decimal("1500.00")
        assert payment.reduction_amount == Decimal("0.00")
    
    def test_create_payment_no_reduction(self):
        """Test creating a payment without reduction fields."""
        payment = Payment(
            amount=Decimal("2000.00"),
            payment_date=utc_now(),
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.BANK_TRANSFER,
            lease_id=1,
            tenant_id=1
        )
        
        assert payment.amount == Decimal("2000.00")
        assert payment.reduction_amount is None
        assert payment.reduction_reason is None
    
    def test_payment_with_new_payment_methods(self):
        """Test creating payments with newly added payment methods."""
        new_methods = [
            PaymentMethod.DEBIT_CARD,
            PaymentMethod.WIRE_TRANSFER,
            PaymentMethod.DIRECT_DEPOSIT,
            PaymentMethod.INTERAC_E_TRANSFER,
            PaymentMethod.BANK_DRAFT,
            PaymentMethod.PAYPAL,
            PaymentMethod.INTERNAL_TRANSFER
        ]
        
        for method in new_methods:
            payment = Payment(
                amount=Decimal("1000.00"),
                payment_date=utc_now(),
                status=PaymentStatus.PAID,
                payment_method=method,
                lease_id=1,
                tenant_id=1
            )
            assert payment.payment_method == method
    
    def test_payment_with_transaction_reference(self):
        """Test creating a payment with transaction reference."""
        payment = Payment(
            amount=Decimal("1000.00"),
            payment_date=utc_now(),
            status=PaymentStatus.PAID,
            payment_method=PaymentMethod.WIRE_TRANSFER,
            transaction_reference="WIRE-2024-001",
            lease_id=1,
            tenant_id=1
        )
        
        assert payment.transaction_reference == "WIRE-2024-001"
    
    def test_payment_with_receipt_url(self):
        """Test creating payment with receipt URL."""
        payment = Payment(
            amount=Decimal("1200.00"),
            payment_date=utc_now(),
            status=PaymentStatus.PAID,
            payment_method=PaymentMethod.CREDIT_CARD,
            receipt_url="https://example.com/receipt.pdf",
            lease_id=1,
            tenant_id=1
        )
        
        assert payment.receipt_url == "https://example.com/receipt.pdf"
        assert payment.amount == Decimal("1200.00")
    
    def test_create_payment_reduction_requires_reason(self):
        """Test that reduction_reason is required when reduction_amount is provided."""
        with pytest.raises(ValidationError) as excinfo:
            # First, create the payment data without reduction reason
            payment_data = {
                "amount": Decimal("1000.00"),
                "reduction_amount": Decimal("100.00"),
                # Missing reduction_reason
                "payment_date": utc_now(),
                "status": PaymentStatus.PAID,
                "payment_method": PaymentMethod.CASH,
                "lease_id": 1,
                "tenant_id": 1
            }
            # Then, explicitly validate it
            Payment.model_validate(payment_data)
        
        assert "Reduction reason is required when reduction amount is provided" in str(excinfo.value) 