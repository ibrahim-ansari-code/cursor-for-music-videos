"""
Unit tests for billing email templates.
"""
import pytest
from datetime import datetime, timezone, timedelta, date

from Backend.api.billing.email_templates import BillingEmailTemplates


pytestmark = pytest.mark.unit


class TestEmailTemplates:
    """Tests for billing email template generation."""
    
    def test_payment_succeeded_email(self):
        """Test payment succeeded email generation."""
        # Arrange
        user_name = "Test User"
        amount = 49.00
        currency = "CAD"
        invoice_id = "inv_123"
        invoice_pdf_url = "https://example.com/invoice.pdf"
        plan_name = "Brikli Premium"
        next_payment_date = date.today() + timedelta(days=30)
        frontend_url = "https://app.brikli.com"
        
        # Act
        subject, html = BillingEmailTemplates.create_payment_succeeded_email(
            user_name, amount, currency, invoice_id, invoice_pdf_url, 
            plan_name, next_payment_date, frontend_url
        )
        
        # Assert
        assert "payment" in subject.lower() or "success" in subject.lower()
        assert user_name in html
        assert plan_name in html
        assert "$49" in html or "49" in html
    
    def test_payment_failed_email(self):
        """Test payment failed email generation."""
        # Arrange
        user_name = "Test User"
        amount = 49.00
        currency = "CAD"
        plan_name = "Brikli Premium"
        attempt_count = 2
        invoice_url = "https://example.com/invoice"
        frontend_url = "https://app.brikli.com"
        
        # Act
        subject, html = BillingEmailTemplates.create_payment_failed_email(
            user_name, amount, currency, plan_name, attempt_count, invoice_url, frontend_url
        )
        
        # Assert
        assert "payment" in subject.lower() or "failed" in subject.lower()
        assert user_name in html
        assert "update" in html.lower() or "payment" in html.lower()
    
    def test_subscription_created_email(self):
        """Test subscription created email generation."""
        # Arrange
        user_name = "Test User"
        plan_name = "Brikli Premium"
        amount = 49.00
        currency = "CAD"
        trial_days = 14
        trial_end_date = date.today() + timedelta(days=trial_days)
        frontend_url = "https://app.brikli.com"
        
        # Act
        subject, html = BillingEmailTemplates.create_subscription_created_email(
            user_name, plan_name, amount, currency, trial_days, trial_end_date, frontend_url
        )
        
        # Assert
        assert "subscription" in subject.lower() or "welcome" in subject.lower()
        assert user_name in html
        assert plan_name in html
    
    def test_trial_ending_email(self):
        """Test trial ending soon email generation."""
        # Arrange
        user_name = "Test User"
        days_remaining = 3
        plan_name = "Brikli Premium"
        amount = 49.00
        currency = "CAD"
        frontend_url = "https://app.brikli.com"
        
        # Act
        subject, html = BillingEmailTemplates.create_trial_ending_email(
            user_name, days_remaining, plan_name, amount, currency, frontend_url
        )
        
        # Assert
        assert "trial" in subject.lower()
        assert user_name in html
        assert str(days_remaining) in html
    
    def test_email_contains_branding(self):
        """Test that emails contain Brikli branding."""
        # Arrange
        user_name = "Test User"
        plan_name = "Brikli Premium"
        amount = 49.00
        currency = "CAD"
        trial_days = 14
        trial_end_date = date.today() + timedelta(days=trial_days)
        frontend_url = "https://app.brikli.com"
        
        # Act
        _, html = BillingEmailTemplates.create_subscription_created_email(
            user_name, plan_name, amount, currency, trial_days, trial_end_date, frontend_url
        )
        
        # Assert
        # Email template system should include Brikli branding
        assert "Brikli" in html or "brikli" in html.lower()
    
    def test_email_has_content(self):
        """Test that generated emails have substantial content."""
        # Arrange
        user_name = "Test User"
        plan_name = "Brikli Premium"
        amount = 49.00
        currency = "CAD"
        trial_days = None
        trial_end_date = None
        frontend_url = "https://app.brikli.com"
        
        # Act
        subject, html = BillingEmailTemplates.create_subscription_created_email(
            user_name, plan_name, amount, currency, trial_days, trial_end_date, frontend_url
        )
        
        # Assert
        assert len(subject) > 5  # Subject should have content
        assert len(html) > 100  # HTML should have substantial content
    
    def test_payment_succeeded_with_no_next_payment_date(self):
        """Test payment succeeded email with no next payment date."""
        # Arrange
        user_name = "Test User"
        amount = 49.00
        currency = "CAD"
        invoice_id = "inv_123"
        invoice_pdf_url = "https://example.com/invoice.pdf"
        plan_name = "Brikli Premium"
        next_payment_date = None  # No next payment (e.g., canceled subscription)
        frontend_url = "https://app.brikli.com"
        
        # Act
        subject, html = BillingEmailTemplates.create_payment_succeeded_email(
            user_name, amount, currency, invoice_id, invoice_pdf_url, 
            plan_name, next_payment_date, frontend_url
        )
        
        # Assert
        assert subject is not None
        assert html is not None
        assert len(html) > 50
