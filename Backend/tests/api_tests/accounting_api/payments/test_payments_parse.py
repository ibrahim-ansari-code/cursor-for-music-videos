"""
Unit tests for the payments parse receipt service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
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
def sample_parsed_payment_data():
    """Sample parsed payment data returned by LLM"""
    return {
        "payment_date": "2024-06-01",
        "subtotal_amount": Decimal("1500.00"),
        "total_amount": Decimal("1500.00"),
        "currency": "USD",
        "payment_method": "Bank Transfer",
        "description_notes": "Rent payment for June 2024 - Unit 101",
        "raw_text_preview": "Payment Receipt - June 2024 Rent..."
    }


@pytest.fixture
def sample_parse_response_data():
    """Sample successful parse response"""
    return {
        "receipt_url": "https://example.blob.core.windows.net/payments/receipt_123.pdf",
        "parsed_details": {
            "payment_date": "2024-06-01",
            "subtotal_amount": "1500.00",
            "total_amount": "1500.00",
            "currency": "USD",
            "payment_method": "Bank Transfer",
            "description_notes": "Rent payment for June 2024 - Unit 101",
            "raw_text_preview": "Payment Receipt - June 2024 Rent..."
        },
        "message": "Receipt parsed successfully"
    }


@pytest.mark.asyncio
async def test_parse_payment_receipt_success(sample_parsed_payment_data, sample_parse_response_data):
    """Test successful payment receipt parsing"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.parse_payment_receipt", 
               new=AsyncMock(return_value=sample_parse_response_data)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/payments/receipts/parse",
            files={"file": ("payment_receipt.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["receipt_url"] == sample_parse_response_data["receipt_url"]
        assert result["parsed_details"]["total_amount"] == "1500.00"
        assert result["parsed_details"]["payment_method"] == "Bank Transfer"
        assert result["message"] == "Receipt parsed successfully"


@pytest.mark.asyncio
async def test_parse_payment_receipt_image_success():
    """Test successful payment receipt parsing with image file"""
    # Arrange
    fake_user = create_test_user()
    image_content = b"fake image content"
    
    parse_response = {
        "receipt_url": "https://example.blob.core.windows.net/payments/receipt_456.jpg",
        "parsed_details": {
            "payment_date": "2024-06-15",
            "subtotal_amount": "850.00",
            "total_amount": "850.00",
            "currency": "CAD",
            "payment_method": "Credit Card",
            "description_notes": "Partial rent payment - Unit 205",
            "raw_text_preview": "Image file processed: payment.jpg"
        },
        "message": "Receipt parsed successfully"
    }
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.parse_payment_receipt",
               new=AsyncMock(return_value=parse_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/payments/receipts/parse",
            files={"file": ("payment.jpg", image_content, "image/jpeg")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["receipt_url"].endswith(".jpg")
        assert result["parsed_details"]["currency"] == "CAD"
        assert result["parsed_details"]["payment_method"] == "Credit Card"


@pytest.mark.asyncio
async def test_parse_payment_receipt_no_file():
    """Test parse payment receipt without file"""
    # Arrange
    fake_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: None
    
    # Act
    client = TestClientWithHost(app)
    response = client.post("/api/accounting/payments/receipts/parse")
    
    # Assert
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_parse_payment_receipt_invalid_file_type():
    """Test parse payment receipt with invalid file type"""
    # Arrange
    fake_user = create_test_user()
    text_content = b"invalid file content"
    
    # Mock the service to raise an HTTPException (as the service layer does)
    with patch("Backend.api.accounting.payments.router.service.parse_payment_receipt",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="File validation failed: Unsupported file type: .txt"
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/payments/receipts/parse",
            files={"file": ("document.txt", text_content, "text/plain")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_payment_receipt_llm_failure():
    """Test parse payment receipt when LLM fails"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    
    # Mock the service to raise an HTTPException for internal errors
    with patch("Backend.api.accounting.payments.router.service.parse_payment_receipt",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                   detail="Failed to parse receipt due to an internal error."
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/payments/receipts/parse",
            files={"file": ("receipt.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 500
        assert "Failed to parse receipt" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_payment_receipt_unauthorized():
    """Test parse payment receipt without authentication"""
    # Arrange - Don't override get_current_user
    pdf_content = b"fake pdf content"
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/accounting/payments/receipts/parse",
        files={"file": ("receipt.pdf", pdf_content, "application/pdf")}
    )
    
    # Assert
    assert response.status_code == 403  # Forbidden (no auth header provided)


@pytest.mark.asyncio 
async def test_parse_payment_receipt_file_too_large():
    """Test parse payment receipt with file exceeding size limit"""
    # Arrange
    fake_user = create_test_user()
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB file
    
    # Mock the service to raise a file size error as HTTPException
    with patch("Backend.api.accounting.payments.router.service.parse_payment_receipt",
               new=AsyncMock(side_effect=HTTPException(
                   status_code=status.HTTP_400_BAD_REQUEST,
                   detail="File validation failed: File size exceeds 10MB limit"
               ))):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/payments/receipts/parse",
            files={"file": ("large_receipt.pdf", large_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "File size exceeds" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_payment_receipt_empty_parsed_data():
    """Test parse payment receipt when LLM returns empty/minimal data"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    
    minimal_response = {
        "receipt_url": "https://example.blob.core.windows.net/payments/receipt_789.pdf",
        "parsed_details": {
            "payment_date": None,
            "subtotal_amount": "0.00",
            "total_amount": "0.00",
            "currency": "",
            "payment_method": "",
            "description_notes": "",
            "raw_text_preview": "No text could be extracted"
        },
        "message": "Receipt parsed but no data could be extracted"
    }
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.parse_payment_receipt",
               new=AsyncMock(return_value=minimal_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/payments/receipts/parse",
            files={"file": ("blank_receipt.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["parsed_details"]["total_amount"] == "0.00"
        assert result["parsed_details"]["payment_method"] == ""
        assert "no data could be extracted" in result["message"]


@pytest.mark.asyncio
async def test_parse_payment_receipt_with_check_payment():
    """Test parse payment receipt with check payment method"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake check receipt"
    
    check_response = {
        "receipt_url": "https://example.blob.core.windows.net/payments/check_123.pdf",
        "parsed_details": {
            "payment_date": "2024-06-20",
            "subtotal_amount": "2000.00",
            "total_amount": "2000.00",
            "currency": "USD",
            "payment_method": "Check",
            "description_notes": "Check #1234 - July rent payment",
            "raw_text_preview": "Check Payment Receipt..."
        },
        "message": "Receipt parsed successfully"
    }
    
    # Mock the service layer
    with patch("Backend.api.accounting.payments.router.service.parse_payment_receipt",
               new=AsyncMock(return_value=check_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/payments/receipts/parse",
            files={"file": ("check_receipt.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["parsed_details"]["payment_method"] == "Check"
        assert "Check #1234" in result["parsed_details"]["description_notes"]