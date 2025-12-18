"""
Unit tests for accounting schema model validators.

Tests coverage for ORM-to-schema conversion in Invoice and Payment responses.
"""
import pytest
from unittest.mock import MagicMock
from decimal import Decimal
from datetime import datetime

from Backend.api.accounting.invoices.schemas import InvoiceResponse
from Backend.api.accounting.payments.schemas import PaymentResponse
from Backend.models.accounting.common import PaymentStatus


def test_invoice_response_convert_nested_individual_tenant():
    """Test InvoiceResponse model_validator with Individual tenant ORM object."""
    # Mock tenant type enum
    mock_tenant_type = MagicMock()
    mock_tenant_type.value = 'Individual'
    
    # Mock Individual tenant
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    mock_tenant.first_name = 'John'
    mock_tenant.last_name = 'Doe'
    mock_tenant.company_name = None
    mock_tenant.tenant_type = mock_tenant_type
    
    # Mock property
    mock_property = MagicMock()
    mock_property.id = 1
    mock_property.name = 'Test Property'
    
    # Mock invoice ORM
    mock_invoice = MagicMock()
    mock_invoice.id = 1
    mock_invoice.invoice_number = 'INV-001'
    mock_invoice.amount = Decimal('100.00')
    mock_invoice.description = 'Test'
    mock_invoice.issue_date = datetime(2024, 1, 1)
    mock_invoice.due_date = datetime(2024, 2, 1)
    mock_invoice.status = PaymentStatus.PENDING
    mock_invoice.property_id = 1
    mock_invoice.tenant_id = 1
    mock_invoice.subtotal_amount = None
    mock_invoice.total_tax_amount = None
    mock_invoice.taxes = []
    mock_invoice.quickbooks_id = None
    mock_invoice.last_synced_at = None
    mock_invoice.created_at = datetime(2024, 1, 1)
    mock_invoice.updated_at = datetime(2024, 1, 1)
    mock_invoice.property = mock_property
    mock_invoice.tenant = mock_tenant
    
    result = InvoiceResponse.model_validate(mock_invoice)
    
    assert result.tenant.full_name == 'John Doe'
    assert result.property.name == 'Test Property'


def test_invoice_response_convert_nested_company_tenant():
    """Test InvoiceResponse model_validator with Company tenant ORM object."""
    mock_tenant_type = MagicMock()
    mock_tenant_type.value = 'Company'
    
    mock_tenant = MagicMock()
    mock_tenant.id = 2
    mock_tenant.first_name = None
    mock_tenant.last_name = None
    mock_tenant.company_name = 'Acme Corp'
    mock_tenant.tenant_type = mock_tenant_type
    
    mock_property = MagicMock()
    mock_property.id = 1
    mock_property.name = 'Test Property'
    
    mock_invoice = MagicMock()
    mock_invoice.id = 1
    mock_invoice.invoice_number = 'INV-002'
    mock_invoice.amount = Decimal('200.00')
    mock_invoice.description = 'Test'
    mock_invoice.issue_date = datetime(2024, 1, 1)
    mock_invoice.due_date = datetime(2024, 2, 1)
    mock_invoice.status = PaymentStatus.PENDING
    mock_invoice.property_id = 1
    mock_invoice.tenant_id = 2
    mock_invoice.subtotal_amount = None
    mock_invoice.total_tax_amount = None
    mock_invoice.taxes = []
    mock_invoice.quickbooks_id = None
    mock_invoice.last_synced_at = None
    mock_invoice.created_at = datetime(2024, 1, 1)
    mock_invoice.updated_at = datetime(2024, 1, 1)
    mock_invoice.property = mock_property
    mock_invoice.tenant = mock_tenant
    
    result = InvoiceResponse.model_validate(mock_invoice)
    
    assert result.tenant.full_name == 'Acme Corp'


def test_payment_response_convert_nested_individual_tenant():
    """Test PaymentResponse model_validator with Individual tenant and lease.property."""
    mock_tenant_type = MagicMock()
    mock_tenant_type.value = 'Individual'
    
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    mock_tenant.first_name = 'Alice'
    mock_tenant.last_name = 'Smith'
    mock_tenant.company_name = None
    mock_tenant.tenant_type = mock_tenant_type
    
    mock_property = MagicMock()
    mock_property.id = 1
    mock_property.name = 'Sunset Apartments'
    
    mock_lease = MagicMock()
    mock_lease.id = 1
    mock_lease.property = mock_property
    
    mock_payment = MagicMock()
    mock_payment.id = 1
    mock_payment.lease_id = 1
    mock_payment.tenant_id = 1
    mock_payment.amount = Decimal('1500.00')
    mock_payment.payment_date = datetime(2024, 1, 15)
    mock_payment.payment_method = 'Bank Transfer'
    mock_payment.status = PaymentStatus.PAID
    mock_payment.transaction_reference = None
    mock_payment.description = None
    mock_payment.receipt_url = None
    mock_payment.reduction_amount = None
    mock_payment.reduction_reason = None
    mock_payment.quickbooks_id = None
    mock_payment.stripe_payment_intent_id = None
    mock_payment.created_at = datetime(2024, 1, 15)
    mock_payment.updated_at = datetime(2024, 1, 15)
    mock_payment.tenant = mock_tenant
    mock_payment.lease = mock_lease
    
    result = PaymentResponse.model_validate(mock_payment)
    
    assert result.tenant_name == 'Alice Smith'
    assert result.property_name == 'Sunset Apartments'


def test_payment_response_convert_nested_company_tenant():
    """Test PaymentResponse model_validator with Company tenant."""
    mock_tenant_type = MagicMock()
    mock_tenant_type.value = 'Company'
    
    mock_tenant = MagicMock()
    mock_tenant.id = 2
    mock_tenant.first_name = None
    mock_tenant.last_name = None
    mock_tenant.company_name = 'Tech Innovations LLC'
    mock_tenant.tenant_type = mock_tenant_type
    
    mock_property = MagicMock()
    mock_property.id = 2
    mock_property.name = 'Office Building'
    
    mock_lease = MagicMock()
    mock_lease.id = 2
    mock_lease.property = mock_property
    
    mock_payment = MagicMock()
    mock_payment.id = 2
    mock_payment.lease_id = 2
    mock_payment.tenant_id = 2
    mock_payment.amount = Decimal('5000.00')
    mock_payment.payment_date = datetime(2024, 1, 20)
    mock_payment.payment_method = 'Wire Transfer'
    mock_payment.status = PaymentStatus.PAID
    mock_payment.transaction_reference = None
    mock_payment.description = None
    mock_payment.receipt_url = None
    mock_payment.reduction_amount = None
    mock_payment.reduction_reason = None
    mock_payment.quickbooks_id = None
    mock_payment.stripe_payment_intent_id = None
    mock_payment.created_at = datetime(2024, 1, 20)
    mock_payment.updated_at = datetime(2024, 1, 20)
    mock_payment.tenant = mock_tenant
    mock_payment.lease = mock_lease
    
    result = PaymentResponse.model_validate(mock_payment)
    
    assert result.tenant_name == 'Tech Innovations LLC'
    assert result.property_name == 'Office Building'

