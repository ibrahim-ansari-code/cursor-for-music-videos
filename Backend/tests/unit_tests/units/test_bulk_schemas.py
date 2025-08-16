"""
Unit tests for bulk assignment schema validation.

Tests Pydantic schema validation for bulk assignment requests and responses,
including edge cases and validation rules.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from pydantic import ValidationError

from Backend.api.units.schemas import (
    CSVAssignmentRow, CSVBulkAssignRequest, CSVBulkAssignResponse,
    BulkAssignmentRequest, BulkAssignmentResponse, CSVAssignmentError
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestCSVAssignmentRow:
    """Test CSV assignment row schema validation."""

    def test_valid_csv_row(self):
        """Test creation of valid CSV assignment row."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        data = {
            "unit_number": "101",
            "tenant_email": "tenant@example.com",
            "lease_start_date": future_date,
            "monthly_rent": Decimal("1200.00")
        }

        row = CSVAssignmentRow(**data)

        assert row.unit_number == "101"
        assert row.tenant_email == "tenant@example.com"
        assert row.monthly_rent == Decimal("1200.00")

    def test_csv_row_email_normalization(self):
        """Test that email is normalized to lowercase."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        data = {
            "unit_number": "101",
            "tenant_email": "TENANT@EXAMPLE.COM",
            "lease_start_date": future_date,
            "monthly_rent": Decimal("1200.00")
        }

        row = CSVAssignmentRow(**data)
        assert row.tenant_email == "tenant@example.com"

    def test_csv_row_invalid_email(self):
        """Test validation of invalid email formats."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        invalid_emails = ["notanemail", "test@", "@example.com", "test@.com"]

        for email in invalid_emails:
            data = {
                "unit_number": "101",
                "tenant_email": email,
                "lease_start_date": future_date,
                "monthly_rent": Decimal("1200.00")
            }

            with pytest.raises(ValidationError) as exc_info:
                CSVAssignmentRow(**data)

            errors = exc_info.value.errors()
            assert any("Invalid email format" in str(
                error.get("msg", "")) for error in errors)

    def test_csv_row_invalid_date_format(self):
        """Test validation of invalid date formats."""
        data = {
            "unit_number": "101",
            "tenant_email": "tenant@example.com",
            "lease_start_date": "invalid-date",  # Invalid string for date testing
            "monthly_rent": Decimal("1200.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(**data)

        errors = exc_info.value.errors()
        assert any("lease_start_date" in str(error.get("loc", []))
                   for error in errors)

    def test_csv_row_past_date(self):
        """Test validation rejects past dates."""
        past_date = (datetime.now() - timedelta(days=30)).date()
        data = {
            "unit_number": "101",
            "tenant_email": "tenant@example.com",
            "lease_start_date": past_date,
            "monthly_rent": Decimal("1200.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(**data)

        errors = exc_info.value.errors()
        assert any("Lease start date cannot be in the past" in str(
            error.get("msg", "")) for error in errors)

    def test_csv_row_invalid_rent_amount(self):
        """Test validation of invalid rent amounts."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        data = {
            "unit_number": "101",
            "tenant_email": "tenant@example.com",
            "lease_start_date": future_date,
            "monthly_rent": "invalid"  # Invalid string for rent testing
        }

        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(**data)

        errors = exc_info.value.errors()
        assert any("monthly_rent" in str(error.get("loc", []))
                   for error in errors)

    def test_csv_row_negative_rent(self):
        """Test validation rejects negative rent."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        data = {
            "unit_number": "101",
            "tenant_email": "tenant@example.com",
            "lease_start_date": future_date,
            "monthly_rent": Decimal("-100.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(**data)

        errors = exc_info.value.errors()
        assert any("greater than 0" in str(error.get("msg", ""))
                   for error in errors)

    def test_csv_row_zero_rent(self):
        """Test validation rejects zero rent."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        data = {
            "unit_number": "101",
            "tenant_email": "tenant@example.com",
            "lease_start_date": future_date,
            "monthly_rent": Decimal("0.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(**data)

        errors = exc_info.value.errors()
        assert any("greater than 0" in str(error.get("msg", ""))
                   for error in errors)

    def test_csv_row_missing_required_fields(self):
        """Test validation of missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(**{})

        errors = exc_info.value.errors()
        required_fields = ["unit_number", "tenant_email",
                           "lease_start_date", "monthly_rent"]

        for field in required_fields:
            assert any(field in str(error.get("loc", [])) for error in errors)

    def test_csv_row_empty_unit_number(self):
        """Test validation of empty unit number."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        data = {
            "unit_number": "",
            "tenant_email": "tenant@example.com",
            "lease_start_date": future_date,
            "monthly_rent": Decimal("1200.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentRow(**data)

        errors = exc_info.value.errors()
        assert any("at least 1 character" in str(error.get("msg", ""))
                   for error in errors)


class TestCSVBulkAssignRequest:
    """Test CSV bulk assignment request schema validation."""

    def test_valid_csv_bulk_request(self):
        """Test creation of valid CSV bulk assignment request."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        assignments = [
            CSVAssignmentRow(
                unit_number="101",
                tenant_email="tenant1@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1200.00"),
                security_deposit=None
            ),
            CSVAssignmentRow(
                unit_number="102",
                tenant_email="tenant2@example.com",
                lease_start_date=future_date,
                monthly_rent=Decimal("1300.00"),
                security_deposit=None
            )
        ]
        data = {"assignments": assignments}

        request = CSVBulkAssignRequest(**data)
        assert len(request.assignments) == 2
        assert request.assignments[0].unit_number == "101"
        assert request.assignments[1].unit_number == "102"

    def test_csv_bulk_request_empty_assignments(self):
        """Test validation of empty assignments list."""
        data = {"assignments": []}

        with pytest.raises(ValidationError) as exc_info:
            CSVBulkAssignRequest(**data)

        errors = exc_info.value.errors()
        assert any("at least 1 item" in str(error.get("msg", ""))
                   for error in errors)

    def test_csv_bulk_request_too_many_assignments(self):
        """Test validation of too many assignments (>1000)."""
        future_date = (datetime.now() + timedelta(days=30)).date()
        assignments = []
        for i in range(1001):  # Create 1001 assignments
            assignments.append({
                "unit_number": f"Unit{i}",
                "tenant_email": f"tenant{i}@example.com",
                "lease_start_date": future_date,
                "monthly_rent": "1200.00"
            })

        data = {"assignments": assignments}

        with pytest.raises(ValidationError) as exc_info:
            CSVBulkAssignRequest(**data)

        errors = exc_info.value.errors()
        assert any("at most 1000 items" in str(error.get("msg", ""))
                   for error in errors)

    def test_csv_bulk_request_invalid_assignment(self):
        """Test validation with invalid assignment data in the request."""
        future_date = (datetime.now() + timedelta(days=30)).date()

        # Test validation with invalid assignment data in the request
        with pytest.raises(ValidationError) as exc_info:
            CSVBulkAssignRequest(assignments=[
                CSVAssignmentRow(
                    unit_number="101",
                    tenant_email="invalid-email",  # This will fail email validation
                    lease_start_date=future_date,
                    monthly_rent=Decimal("1200.00"),
                    security_deposit=None
                )
            ])

        errors = exc_info.value.errors()
        assert any("tenant_email" in str(error.get("loc", []))
                   for error in errors)


class TestBulkAssignmentRequest:
    """Test bulk assignment request schema validation."""

    def test_valid_bulk_assignment_request(self):
        """Test creation of valid bulk assignment request."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "monthly_rent": Decimal("1200.00"),
            "security_deposit": Decimal("2400.00"),
            "rent_due_day": 15,
            "late_fee_amount": Decimal("50.00"),
            "late_fee_after_days": 5,
            "special_terms": "Pet allowed"
        }

        request = BulkAssignmentRequest(**data)
        assert request.unit_ids == [1, 2, 3]
        assert request.tenant_id == 1
        assert request.monthly_rent == Decimal("1200.00")
        assert request.security_deposit == Decimal("2400.00")
        assert request.rent_due_day == 15

    def test_bulk_assignment_request_minimal_data(self):
        """Test bulk assignment request with minimal required data."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00")
        }

        request = BulkAssignmentRequest(**data)
        assert request.unit_ids == [1]
        assert request.rent_due_day == 1  # Default value
        assert request.monthly_rent is None  # Optional field

    def test_bulk_assignment_request_empty_unit_ids(self):
        """Test validation of empty unit IDs list."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("at least 1 item" in str(error.get("msg", ""))
                   for error in errors)

    def test_bulk_assignment_request_too_many_units(self):
        """Test validation of too many unit IDs (>1000)."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": list(range(1, 1002)),  # 1001 units
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("at most 1000 items" in str(error.get("msg", ""))
                   for error in errors)

    def test_bulk_assignment_request_invalid_tenant_id(self):
        """Test validation of invalid tenant ID."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 0,  # Invalid (must be > 0)
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("greater than 0" in str(error.get("msg", ""))
                   for error in errors)

    def test_bulk_assignment_request_past_start_date(self):
        """Test validation rejects past start dates."""
        past_date = (datetime.now() - timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 1,
            "lease_start_date": past_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("Lease start date cannot be in the past" in str(
            error.get("msg", "")) for error in errors)

    def test_bulk_assignment_request_end_before_start(self):
        """Test validation rejects end date before start date."""
        start_date = (datetime.now() + timedelta(days=365)).date()
        end_date = (datetime.now() + timedelta(days=30)).date()  # Before start

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00")
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("End date must be after start date" in str(
            error.get("msg", "")) for error in errors)

    def test_bulk_assignment_request_invalid_security_deposit(self):
        """Test validation of invalid security deposit."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("-100.00")  # Negative amount
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("greater than 0" in str(error.get("msg", ""))
                   for error in errors)

    def test_bulk_assignment_request_invalid_rent_due_day(self):
        """Test validation of invalid rent due day."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00"),
            "rent_due_day": 32  # Invalid (must be 1-31)
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("less than or equal to 31" in str(
            error.get("msg", "")) for error in errors)

    def test_bulk_assignment_request_negative_late_fee(self):
        """Test validation of negative late fee."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00"),
            "late_fee_amount": Decimal("-50.00")  # Negative fee
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(
            error.get("msg", "")) for error in errors)

    def test_bulk_assignment_request_long_special_terms(self):
        """Test validation of too long special terms."""
        start_date = (datetime.now() + timedelta(days=30)).date()
        end_date = (datetime.now() + timedelta(days=365)).date()

        data = {
            "unit_ids": [1, 2, 3],
            "tenant_id": 1,
            "lease_start_date": start_date,
            "end_date": end_date,
            "security_deposit": Decimal("1000.00"),
            "special_terms": "x" * 1001  # Too long (max 1000)
        }

        with pytest.raises(ValidationError) as exc_info:
            BulkAssignmentRequest(**data)

        errors = exc_info.value.errors()
        assert any("at most 1000 characters" in str(
            error.get("msg", "")) for error in errors)


class TestCSVAssignmentError:
    """Test CSV assignment error schema validation."""

    def test_valid_csv_assignment_error(self):
        """Test creation of valid CSV assignment error."""
        data = {
            "row_number": 1,
            "unit_number": "101",
            "error_message": "Unit not found",
            "error_type": "unit_not_found"
        }

        error = CSVAssignmentError(**data)
        assert error.row_number == 1
        assert error.unit_number == "101"
        assert error.error_message == "Unit not found"
        assert error.error_type == "unit_not_found"

    def test_csv_assignment_error_missing_fields(self):
        """Test validation of missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            CSVAssignmentError(**{})

        errors = exc_info.value.errors()
        required_fields = ["row_number", "unit_number",
                           "error_message", "error_type"]

        for field in required_fields:
            assert any(field in str(error.get("loc", [])) for error in errors)


class TestResponseSchemas:
    """Test response schema validation."""

    def test_csv_bulk_assign_response(self):
        """Test CSV bulk assignment response schema."""
        data = {
            "total_rows": 5,
            "successful_assignments": 3,
            "failed_assignments": 2,
            "errors": [
                {
                    "row_number": 3,
                    "unit_number": "103",
                    "error_message": "Unit occupied",
                    "error_type": "unit_occupied"
                },
                {
                    "row_number": 6,
                    "unit_number": "106",
                    "error_message": "Tenant not found",
                    "error_type": "tenant_not_found"
                }
            ],
            "created_leases": [1, 2, 3]
        }

        response = CSVBulkAssignResponse(**data)
        assert response.total_rows == 5
        assert response.successful_assignments == 3
        assert response.failed_assignments == 2
        assert len(response.errors) == 2
        assert len(response.created_leases) == 3

    def test_bulk_assignment_response(self):
        """Test bulk assignment response schema."""
        data = {
            "total_units": 3,
            "successful_assignments": 2,
            "failed_assignments": 1,
            "errors": [
                {
                    "row_number": 0,
                    "unit_number": "Unit 3",
                    "error_message": "Unit already assigned",
                    "error_type": "unit_occupied"
                }
            ],
            "created_leases": [1, 2]
        }

        response = BulkAssignmentResponse(**data)
        assert response.total_units == 3
        assert response.successful_assignments == 2
        assert response.failed_assignments == 1
        assert len(response.errors) == 1
        assert len(response.created_leases) == 2

    def test_response_negative_assignments(self):
        """Test validation rejects negative assignment counts."""
        data = {
            "total_rows": 5,
            "successful_assignments": -1,  # Invalid
            "failed_assignments": 2,
            "errors": []
        }

        with pytest.raises(ValidationError) as exc_info:
            CSVBulkAssignResponse(**data)

        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(
            error.get("msg", "")) for error in errors)
