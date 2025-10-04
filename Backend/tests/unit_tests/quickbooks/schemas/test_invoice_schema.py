"""
Unit tests for QuickBooks InvoiceSchema class.

Tests data transformation between Brikli Invoice and QuickBooks Invoice formats.
"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC, date
from decimal import Decimal

from Backend.api.quickbooks.schemas.invoice import InvoiceSchema
from Backend.models.accounting.invoice import Invoice
from Backend.models.accounting.common import PaymentStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.tenant import Tenant

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
FIXED_DATE = date(2024, 6, 1)


def create_test_invoice(**kwargs):
    """Helper function to create a test invoice."""
    defaults = {
        "invoice_number": "INV-001",
        "amount": Decimal("1200.00"),  # Correct field name
        "description": "Monthly Rent",
        "issue_date": FIXED_DATETIME,  # Correct field name
        "due_date": datetime(2024, 7, 1, 12, 0, 0, tzinfo=UTC),  # Must be datetime
        "status": PaymentStatus.PENDING,  # Correct field name
        "property_id": 1,
        "tenant_id": uuid4(),
        "created_at": FIXED_DATETIME,
        "updated_at": FIXED_DATETIME
    }
    defaults.update(kwargs)
    return Invoice(**defaults)


def create_test_tenant(**kwargs):
    """Helper function to create a test tenant."""
    defaults = {
        "id": uuid4(),
        "user_id": uuid4(),
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "quickbooks_customer_id": "qb_customer_123",
        "created_at": FIXED_DATETIME,
        "updated_at": FIXED_DATETIME
    }
    defaults.update(kwargs)
    return Tenant(**defaults)


class TestInvoiceValidation:
    """Test invoice validation for QuickBooks sync."""

    def test_validate_invoice_valid(self):
        """Test validation of valid invoice."""
        invoice = create_test_invoice()
        tenant = create_test_tenant()

        errors = InvoiceSchema.validate_for_quickbooks(invoice, tenant)
        # Validation returns Dict[str, str], empty dict means valid
        assert errors == {}

    def test_validate_invoice_missing_customer_id(self):
        """Test validation with tenant missing QuickBooks ID."""
        invoice = create_test_invoice()
        tenant = create_test_tenant(quickbooks_customer_id=None)

        errors = InvoiceSchema.validate_for_quickbooks(invoice, tenant)
        # Should have tenant error
        assert "tenant" in errors

    def test_validate_invoice_zero_amount(self):
        """Test validation with zero amount."""
        invoice = create_test_invoice(amount=Decimal("0.00"))  # Use 'amount' not 'total_amount'
        tenant = create_test_tenant()

        errors = InvoiceSchema.validate_for_quickbooks(invoice, tenant)
        assert "amount" in errors


class TestToQuickBooks:
    """Test conversion from Invoice to QuickBooks format."""

    def test_to_quickbooks_basic(self):
        """Test basic invoice to QuickBooks conversion."""
        invoice = create_test_invoice()
        tenant = create_test_tenant()

        # Actual signature requires service_item_id
        result = InvoiceSchema.to_quickbooks(invoice, tenant, service_item_id="1")

        assert "Invoice" in result
        qb_invoice = result["Invoice"]

        assert qb_invoice["DocNumber"] == "INV-001"
        assert qb_invoice["TxnDate"] == "2024-06-01"
        assert qb_invoice["DueDate"] == "2024-07-01"
        # TotalAmt is not set explicitly - QuickBooks calculates it from Line items

        assert "CustomerRef" in qb_invoice
        assert qb_invoice["CustomerRef"]["value"] == "qb_customer_123"

    def test_to_quickbooks_with_line_items(self):
        """Test conversion with line items."""
        invoice = create_test_invoice()
        tenant = create_test_tenant()

        # Actual signature requires service_item_id
        result = InvoiceSchema.to_quickbooks(invoice, tenant, service_item_id="1")
        qb_invoice = result["Invoice"]

        assert "Line" in qb_invoice
        assert len(qb_invoice["Line"]) >= 1

        line = qb_invoice["Line"][0]
        assert line["Amount"] == 1200.00
        assert "SalesItemLineDetail" in line


class TestFromQuickBooks:
    """Test conversion from QuickBooks Invoice to Brikli format."""

    def test_from_quickbooks_basic(self):
        """Test basic QuickBooks to invoice conversion."""
        qb_invoice = {
            "Id": "123",
            "DocNumber": "QB-001",
            "TxnDate": "2024-06-01",
            "DueDate": "2024-07-01",
            "TotalAmt": 1200.00,
            "CustomerRef": {"value": "cust_123", "name": "John Doe"},
            "Line": [{
                "DetailType": "SalesItemLineDetail",
                "Description": "Monthly Rent",
                "Amount": 1200.00
            }]
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
        tenant = create_test_tenant(quickbooks_customer_id="cust_123")

        # Actual signature: from_quickbooks(qb_invoice, lease, tenant, tax_code_mapping)
        invoice, tax_details = InvoiceSchema.from_quickbooks(qb_invoice, lease, tenant)

        assert invoice.quickbooks_id == "123"
        assert invoice.invoice_number == "QB-001"
        assert "Monthly Rent" in invoice.description
        assert isinstance(tax_details, list)