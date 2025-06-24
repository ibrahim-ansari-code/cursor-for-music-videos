"""
Unit tests for the leases parse service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal
from io import BytesIO

from fastapi import HTTPException, status, UploadFile

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        # Always add localhost to headers if not present
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD):
    """Helper function to create a properly initialized test user."""
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=FIXED_DATETIME,
        updated_at=FIXED_DATETIME,
        is_email_verified=True
    )


def create_mock_upload_file(filename: str, content: bytes, content_type: str = "application/pdf"):
    """Helper function to create a mock UploadFile."""
    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.content_type = content_type
    file.file = BytesIO(content)
    file.read = AsyncMock(return_value=content)
    file.close = AsyncMock()
    return file


@pytest.fixture
def sample_parsed_lease_data():
    """Sample parsed lease data returned by LLM"""
    return {
        "core_identifiers": {
            "tenant_name": "John Smith",
            "landlord_name": "ABC Property Management",
            "rental_address": "123 Main St, Toronto, ON",
            "unit_number": "101",
            "mailing_address": "",
            "lease_signed_date": "2024-05-15",
            "jurisdiction": "Ontario"
        },
        "term_details": {
            "lease_start_date": "2024-06-01",
            "lease_end_date": "2025-05-31",
            "lease_type": "Fixed-term",
            "auto_renewal": "No",
            "notice_period": "60 days",
            "vacate_clause": "Tenant must provide 60 days written notice",
            "renewal_terms": "Month-to-month after initial term"
        },
        "rent_payment": {
            "monthly_rent": "1500.00",
            "rent_frequency": "Monthly",
            "due_date": "1st of the month",
            "payment_methods": "Check, Bank Transfer, Online Portal",
            "late_fee": "$50 after 5 days",
            "rent_increase_policy": "Annual increase as per provincial guidelines",
            "deposit_usage_policy": "Cannot be used for last month's rent"
        },
        "deposits": {
            "security_deposit": "1500.00",
            "pet_deposit": "0.0",
            "deposit_due_date": "2024-06-01",
            "interest_on_deposit": "As per provincial regulations",
            "return_terms": "Within 30 days of move-out",
            "trust_account_details": "Held in trust account at TD Bank",
            "additional_deposit": ""
        }
    }


@pytest.fixture
def sample_lease_analysis_response():
    """Sample successful lease analysis response"""
    return {
        "monthly_rent": "1500.00",
        "start_date": "2024-06-01",
        "end_date": "2025-05-31",
        "security_deposit": "1500.00",
        "late_fee_amount": "50.00",
        "tenant_name": "John Smith",
        "unit": "101"
    }


@pytest.mark.asyncio
async def test_parse_lease_success(sample_parsed_lease_data, sample_lease_analysis_response):
    """Test successful lease parsing"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake lease pdf content"
    
    # Mock the service layer
    with patch("Backend.api.leases.router.parse_lease", 
               new=AsyncMock(return_value=sample_lease_analysis_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("lease_agreement.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["monthly_rent"] == "1500.00"
        assert result["tenant_name"] == "John Smith"
        assert result["unit"] == "101"
        assert result["security_deposit"] == "1500.00"


@pytest.mark.asyncio
async def test_parse_lease_complex_document():
    """Test parsing a complex lease document with all fields"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"complex lease pdf"
    
    complex_response = {
        "monthly_rent": "2500.00",
        "start_date": "2024-07-01",
        "end_date": "2026-06-30",
        "security_deposit": "5000.00",
        "late_fee_amount": "100.00",
        "tenant_name": "Jane Doe & John Doe",
        "unit": "PH-2A"
    }
    
    # Mock the service layer
    with patch("Backend.api.leases.router.parse_lease",
               new=AsyncMock(return_value=complex_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("complex_lease.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["monthly_rent"] == "2500.00"
        assert "Jane Doe & John Doe" in result["tenant_name"]
        assert result["unit"] == "PH-2A"


@pytest.mark.asyncio
async def test_parse_lease_no_file():
    """Test parse lease without file"""
    # Arrange
    fake_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: None
    
    # Act
    client = TestClientWithHost(app)
    response = client.post("/api/leases/parse")
    
    # Assert
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_parse_lease_invalid_file_type():
    """Test parse lease with non-PDF file"""
    # Arrange
    fake_user = create_test_user()
    image_content = b"image content"
    
    # Mock the service to raise an HTTPException (as the service layer does)
    with patch("Backend.api.leases.router.parse_lease",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="Only PDF files are supported for lease parsing"
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("lease.jpg", image_content, "image/jpeg")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "Only PDF files are supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_lease_llm_failure():
    """Test parse lease when LLM fails"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    
    # Mock the service to raise an HTTPException for internal errors
    with patch("Backend.api.leases.router.parse_lease",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                   detail="Failed to parse lease document. Please try again."
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("lease.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 500
        assert "Failed to parse lease" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_lease_unauthorized():
    """Test parse lease without authentication"""
    # Arrange - Don't override get_current_user
    pdf_content = b"fake pdf content"
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/leases/parse",
        files={"file": ("lease.pdf", pdf_content, "application/pdf")}
    )
    
    # Assert
    assert response.status_code == 403  # Forbidden (no auth header provided)


@pytest.mark.asyncio 
async def test_parse_lease_file_too_large():
    """Test parse lease with file exceeding size limit"""
    # Arrange
    fake_user = create_test_user()
    large_content = b"x" * (21 * 1024 * 1024)  # 21MB file (lease limit is usually higher)
    
    # Mock the service to raise a file size error as HTTPException
    with patch("Backend.api.leases.router.parse_lease",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="File size exceeds 20MB limit"
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("large_lease.pdf", large_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "File size exceeds" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_lease_missing_required_fields():
    """Test parse lease when LLM cannot extract required fields"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    
    minimal_response = {
        "monthly_rent": "0.00",  # Default when not found
        "start_date": None,
        "end_date": None,
        "security_deposit": "0.00",
        "late_fee_amount": None,
        "tenant_name": "",
        "unit": ""
    }
    
    # Mock the service layer
    with patch("Backend.api.leases.router.parse_lease",
               new=AsyncMock(return_value=minimal_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("unclear_lease.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["monthly_rent"] == "0.00"
        assert result["tenant_name"] == ""
        assert result["start_date"] is None


@pytest.mark.asyncio
async def test_parse_lease_non_english_document():
    """Test parse lease with non-English document"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"contrato de arrendamiento"
    
    # Mock the service to handle non-English content as HTTPException
    with patch("Backend.api.leases.router.parse_lease",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="Unable to parse lease: Document appears to be in a non-supported language"
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("contrato.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "non-supported language" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_lease_corrupted_pdf():
    """Test parse lease with corrupted PDF"""
    # Arrange
    fake_user = create_test_user()
    corrupted_content = b"corrupted pdf data"
    
    # Mock the service to raise PDF processing error as HTTPException
    with patch("Backend.api.leases.router.parse_lease",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="Could not process PDF file: Invalid PDF structure"
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/leases/parse",
            files={"file": ("corrupted.pdf", corrupted_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "Could not process PDF" in response.json()["detail"]