"""
Unit tests for the expenses parse receipt service functions using hybrid API testing pattern.
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
from Backend.api.accounting.expenses.schemas import ExpenseReceiptParseDetails
from Backend.models.accounting.payment import PaymentMethod

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
def sample_parsed_expense_data():
    """Sample parsed expense data returned by LLM"""
    return {
        "payment_date": "2024-06-01",
        "subtotal_amount": Decimal("85.00"),
        "total_amount": Decimal("95.50"),
        "total_tax_amount": Decimal("10.50"),
        "currency": "USD",
        "payment_method": "Credit Card",
        "description_notes": "Office supplies from Staples",
        "tax_details": [
            {
                "tax_name": "GST",
                "tax_rate": "5.00",
                "tax_amount": "4.25"
            },
            {
                "tax_name": "PST", 
                "tax_rate": "7.00",
                "tax_amount": "5.95"
            }
        ],
        "raw_text_preview": "STAPLES Business Center Receipt Date: 06/01/2024..."
    }


@pytest.fixture
def sample_parse_response_data():
    """Sample successful parse response"""
    return {
        "receipt_url": "https://example.blob.core.windows.net/expenses/receipt_123.pdf",
        "parsed_details": {
            "expense_date": "2024-06-01",
            "payment_date": "2024-06-01",
            "subtotal_amount": "85.00",
            "total_tax_amount": "10.50",
            "total_amount": "95.50",
            "currency": "USD",
            "tax_details": [
                {
                    "tax_name": "GST",
                    "tax_rate": "5.00",
                    "tax_amount": "4.25"
                },
                {
                    "tax_name": "PST",
                    "tax_rate": "7.00", 
                    "tax_amount": "5.95"
                }
            ],
            "payment_method": "Credit Card",
            "description_notes": "Office supplies from Staples",
            "raw_text_preview": "STAPLES Business Center Receipt Date: 06/01/2024..."
        },
        "message": "Receipt parsed successfully"
    }


@pytest.mark.asyncio
async def test_parse_expense_receipt_success(sample_parsed_expense_data, sample_parse_response_data):
    """Test successful expense receipt parsing"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    mock_file = create_mock_upload_file("receipt.pdf", pdf_content)
    
    # Mock the service layer and LLM
    with patch("Backend.api.accounting.expenses.router.service.parse_expense_receipt", 
               new=AsyncMock(return_value=sample_parse_response_data)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/expenses/parse-receipt",
            files={"file": ("receipt.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["receipt_url"] == sample_parse_response_data["receipt_url"]
        assert result["parsed_details"]["total_amount"] == "95.50"
        assert len(result["parsed_details"]["tax_details"]) == 2
        assert result["message"] == "Receipt parsed successfully"


@pytest.mark.asyncio
async def test_parse_expense_receipt_image_success():
    """Test successful expense receipt parsing with image file"""
    # Arrange
    fake_user = create_test_user()
    image_content = b"fake image content"
    
    parse_response = {
        "receipt_url": "https://example.blob.core.windows.net/expenses/receipt_456.jpg",
        "parsed_details": {
            "expense_date": "2024-06-15",
            "payment_date": "2024-06-15",
            "subtotal_amount": "50.00",
            "total_tax_amount": "5.00",
            "total_amount": "55.00",
            "currency": "CAD",
            "tax_details": [
                {
                    "tax_name": "HST",
                    "tax_rate": "10.00",
                    "tax_amount": "5.00"
                }
            ],
            "payment_method": "Cash",
            "description_notes": "Restaurant receipt",
            "raw_text_preview": "Image file processed: receipt.jpg"
        },
        "message": "Receipt parsed successfully"
    }
    
    # Mock the service layer
    with patch("Backend.api.accounting.expenses.router.service.parse_expense_receipt",
               new=AsyncMock(return_value=parse_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/expenses/parse-receipt",
            files={"file": ("receipt.jpg", image_content, "image/jpeg")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["receipt_url"].endswith(".jpg")
        assert result["parsed_details"]["currency"] == "CAD"
        assert result["parsed_details"]["payment_method"] == "Cash"


@pytest.mark.asyncio
async def test_parse_expense_receipt_no_file():
    """Test parse expense receipt without file"""
    # Arrange
    fake_user = create_test_user()
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: None
    
    # Act
    client = TestClientWithHost(app)
    response = client.post("/api/accounting/expenses/parse-receipt")
    
    # Assert
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.asyncio
async def test_parse_expense_receipt_invalid_file_type():
    """Test parse expense receipt with invalid file type"""
    # Arrange
    fake_user = create_test_user()
    text_content = b"invalid file content"
    
    # Mock the service to raise an HTTPException (as the service layer does)
    with patch("Backend.api.accounting.expenses.router.service.parse_expense_receipt",
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
            "/api/accounting/expenses/parse-receipt",
            files={"file": ("document.txt", text_content, "text/plain")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_expense_receipt_llm_failure():
    """Test parse expense receipt when LLM fails"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    
    # Mock the service to raise an HTTPException for internal errors
    with patch("Backend.api.accounting.expenses.router.service.parse_expense_receipt",
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
            "/api/accounting/expenses/parse-receipt",
            files={"file": ("receipt.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 500
        assert "Failed to parse receipt" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_expense_receipt_no_auth():
    """Test parse expense receipt without authentication"""
    # Arrange - Don't override get_current_user
    pdf_content = b"fake pdf content"
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/accounting/expenses/parse-receipt",
        files={"file": ("receipt.pdf", pdf_content, "application/pdf")}
    )
    
    # Assert
    assert response.status_code == 403  # Forbidden (no auth header provided)


@pytest.mark.asyncio
async def test_parse_expense_receipt_invalid_token():
    """Test parse expense receipt with invalid authentication token"""
    # Arrange
    pdf_content = b"fake pdf content"
    
    # Mock get_current_user to raise 401 for invalid token
    async def mock_invalid_auth():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_invalid_auth
    
    # Act
    client = TestClientWithHost(app)
    response = client.post(
        "/api/accounting/expenses/parse-receipt",
        files={"file": ("receipt.pdf", pdf_content, "application/pdf")},
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    # Assert
    assert response.status_code == 401  # Unauthorized (invalid token)


@pytest.mark.asyncio 
async def test_parse_expense_receipt_file_too_large():
    """Test parse expense receipt with file exceeding size limit"""
    # Arrange
    fake_user = create_test_user()
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB file
    
    # Mock the service to raise a file size error as HTTPException
    with patch("Backend.api.accounting.expenses.router.service.parse_expense_receipt",
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
            "/api/accounting/expenses/parse-receipt",
            files={"file": ("large_receipt.pdf", large_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 400
        assert "File size exceeds" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_expense_receipt_empty_parsed_data():
    """Test parse expense receipt when LLM returns empty/minimal data"""
    # Arrange
    fake_user = create_test_user()
    pdf_content = b"fake pdf content"
    
    minimal_response = {
        "receipt_url": "https://example.blob.core.windows.net/expenses/receipt_789.pdf",
        "parsed_details": {
            "expense_date": None,
            "payment_date": None,
            "subtotal_amount": "0.00",
            "total_tax_amount": "0.00", 
            "total_amount": "0.00",
            "currency": "",
            "tax_details": [],
            "payment_method": "",
            "description_notes": "",
            "raw_text_preview": "No text could be extracted"
        },
        "message": "Receipt parsed but no data could be extracted"
    }
    
    # Mock the service layer
    with patch("Backend.api.accounting.expenses.router.service.parse_expense_receipt",
               new=AsyncMock(return_value=minimal_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: None
        
        # Act
        client = TestClientWithHost(app)
        response = client.post(
            "/api/accounting/expenses/parse-receipt",
            files={"file": ("blank_receipt.pdf", pdf_content, "application/pdf")}
        )
        
        # Assert
        assert response.status_code == 200
        result = response.json()
        assert result["parsed_details"]["total_amount"] == "0.00"
        assert len(result["parsed_details"]["tax_details"]) == 0
        assert "no data could be extracted" in result["message"]


def test_payment_method_validator_with_none():
    """Test payment method validator with None value - Line 36."""
    result = ExpenseReceiptParseDetails.validate_payment_method(None)
    assert result is None


def test_payment_method_validator_with_enum():
    """Test payment method validator with PaymentMethod enum - Line 39."""
    result = ExpenseReceiptParseDetails.validate_payment_method(PaymentMethod.CREDIT_CARD)
    assert result == PaymentMethod.CREDIT_CARD


def test_payment_method_validator_case_insensitive_match():
    """Test payment method validator with case insensitive string - Line 51."""
    result = ExpenseReceiptParseDetails.validate_payment_method("credit card")
    assert result == PaymentMethod.CREDIT_CARD


def test_payment_method_validator_fallback_to_other():
    """Test payment method validator fallback to OTHER - Line 56."""
    result = ExpenseReceiptParseDetails.validate_payment_method("invalid_method")
    assert result == PaymentMethod.OTHER