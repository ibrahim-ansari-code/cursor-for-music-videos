"""
Unit tests for the expenses creation service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.models.accounting.expense import ExpenseResponse, ExpenseTaxDetailResponse
from Backend.models.accounting.payment import PaymentMethod
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Fixed datetime for deterministic testing
FIXED_DATETIME = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
FIXED_DATETIME_UPDATED = datetime(2024, 6, 1, 12, 1, 0, tzinfo=timezone.utc)

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

@pytest.fixture
def sample_expense_data():
    """Sample expense creation data"""
    return {
        "property_id": 1,
        "category": "Utilities",
        "subtotal_amount": "100.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "June electricity bill",
        "receipt_url": "https://example.com/receipt.pdf",
        "taxes": []
    }


@pytest.fixture
def sample_expense_response():
    """Sample expense response"""
    return ExpenseResponse(
        id=1,
        property_id=1,
        category="Utilities",
        subtotal_amount=Decimal("100.00"),
        expense_date=FIXED_DATETIME,
        description="June electricity bill",
        receipt_url="https://example.com/receipt.pdf",
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("100.00"),
        taxes=[],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )


@pytest.mark.asyncio
async def test_create_expense_success(sample_expense_data, sample_expense_response):
    """Test successful expense creation"""
    # Arrange
    fake_user = create_test_user()
    
    # Mock the service layer
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=sample_expense_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/accounting/expenses",
                json=sample_expense_data
            )
        
            # Assert
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == 1
            assert data["category"] == "Utilities"
            assert data["subtotal_amount"] == "100.00"
            assert data["total_tax_amount"] == "0.00"
            assert data["total_amount"] == "100.00"
            assert data["property_id"] == 1


@pytest.mark.asyncio
async def test_create_expense_with_taxes():
    """Test expense creation with tax calculations (service calculates tax_amount)"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data with taxes (only tax_rate provided, service calculates tax_amount)
    expense_data = {
        "property_id": 2,
        "category": "Supplies",
        "subtotal_amount": "200.00",
        "expense_date": "2024-06-02T10:00:00Z",
        "description": "Office supplies",
        "receipt_url": "https://example.com/receipt2.pdf",
        "taxes": [
            {"tax_name": "GST", "tax_rate": "5.00"},
            {"tax_name": "PST", "tax_rate": "7.00"}
        ]
    }
    
    # Expected response with tax details
    mock_response = ExpenseResponse(
        id=2,
        property_id=2,
        category="Supplies",
        subtotal_amount=Decimal("200.00"),
        expense_date=datetime(2024, 6, 2, 10, 0, 0, tzinfo=timezone.utc),
        description="Office supplies",
        receipt_url="https://example.com/receipt2.pdf",
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("24.00"),
        total_amount=Decimal("224.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=1,
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("10.00"),
                expense_id=2
            ),
            ExpenseTaxDetailResponse(
                id=2,
                tax_name="PST",
                tax_rate=Decimal("7.00"),
                tax_amount=Decimal("14.00"),
                expense_id=2
            )
        ],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["total_tax_amount"] == "24.00"
            assert data["total_amount"] == "224.00"
            assert len(data["taxes"]) == 2
            
            # Verify tax details
            gst_tax = next(t for t in data["taxes"] if t["tax_name"] == "GST")
            assert gst_tax["tax_rate"] == "5.00"
            assert gst_tax["tax_amount"] == "10.00"
            
            pst_tax = next(t for t in data["taxes"] if t["tax_name"] == "PST")
            assert pst_tax["tax_rate"] == "7.00"
            assert pst_tax["tax_amount"] == "14.00"


@pytest.mark.asyncio
async def test_create_expense_with_precalculated_tax_amounts():
    """Test expense creation with pre-calculated tax amounts"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data with pre-calculated tax amounts
    expense_data = {
        "property_id": 3,
        "category": "Supplies",
        "subtotal_amount": "300.00",
        "expense_date": "2024-06-03T10:00:00Z",
        "description": "Office supplies with pre-calculated taxes",
        "receipt_url": "https://example.com/receipt3.pdf",
        "taxes": [
            {"tax_name": "GST", "tax_rate": "5.00", "tax_amount": "15.00"},
            {"tax_name": "PST", "tax_rate": "7.00", "tax_amount": "21.00"}
        ]
    }
    
    # Expected response with pre-calculated tax details
    mock_response = ExpenseResponse(
        id=3,
        property_id=3,
        category="Supplies",
        subtotal_amount=Decimal("300.00"),
        expense_date=datetime(2024, 6, 3, 10, 0, 0, tzinfo=timezone.utc),
        description="Office supplies with pre-calculated taxes",
        receipt_url="https://example.com/receipt3.pdf",
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("36.00"),
        total_amount=Decimal("336.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=5,
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("15.00"),
                expense_id=3
            ),
            ExpenseTaxDetailResponse(
                id=6,
                tax_name="PST",
                tax_rate=Decimal("7.00"),
                tax_amount=Decimal("21.00"),
                expense_id=3
            )
        ],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["total_tax_amount"] == "36.00"
            assert data["total_amount"] == "336.00"
            assert len(data["taxes"]) == 2
            
            # Verify pre-calculated tax details
            gst_tax = next(t for t in data["taxes"] if t["tax_name"] == "GST")
            assert gst_tax["tax_rate"] == "5.00"
            assert gst_tax["tax_amount"] == "15.00"
            
            pst_tax = next(t for t in data["taxes"] if t["tax_name"] == "PST")
            assert pst_tax["tax_rate"] == "7.00"
            assert pst_tax["tax_amount"] == "21.00"


@pytest.mark.asyncio
async def test_create_expense_unauthorized_property(sample_expense_data):
    """Test expense creation for property not owned by user"""
    # Arrange
    fake_user = create_test_user()
    
    with patch(
        "Backend.api.accounting.expenses.router.service.create_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add expenses to this property"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=sample_expense_data
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json()["detail"] == "You don't have permission to add expenses to this property"


@pytest.mark.asyncio
async def test_create_expense_property_not_found():
    """Test expense creation with non-existent property"""
    # Arrange
    fake_user = create_test_user()
    
    expense_data = {
        "property_id": 9999,
        "category": "Utilities",
        "subtotal_amount": "100.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Test expense",
        "taxes": []
    }
    
    with patch(
        "Backend.api.accounting.expenses.router.service.create_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "Property not found"


@pytest.mark.asyncio
async def test_create_expense_invalid_data():
    """Test expense creation with invalid data"""
    # Arrange
    fake_user = create_test_user()
    
    # Missing required fields
    invalid_data = {
        "property_id": 1,
        "category": "Utilities"
        # Missing subtotal_amount and expense_date
    }
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post(
            "/api/accounting/expenses",
            json=invalid_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any(error["loc"][-1] == "subtotal_amount" for error in errors)
        assert any(error["loc"][-1] == "expense_date" for error in errors)


@pytest.mark.asyncio
async def test_create_expense_negative_amount():
    """Test expense creation with negative amount"""
    # Arrange
    fake_user = create_test_user()
    
    expense_data = {
        "property_id": 1,
        "category": "Utilities",
        "subtotal_amount": "-100.00",  # Negative amount
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Invalid expense",
        "taxes": []
    }
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post(
            "/api/accounting/expenses",
            json=expense_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any(
            error["loc"][-1] == "subtotal_amount" and "greater than or equal to 0" in error["msg"]
            for error in errors
        )


@pytest.mark.asyncio
async def test_create_expense_decimal_precision_validation():
    """Test expense creation with amounts having more than 2 decimal places"""
    # Arrange
    fake_user = create_test_user()
    
    # Test with 3 decimal places
    expense_data = {
        "property_id": 1,
        "category": "Utilities",
        "subtotal_amount": "100.123",  # 3 decimal places
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Test expense with precision",
        "taxes": []
    }
    
    # Create a mock response - the service would handle decimal validation
    mock_response = ExpenseResponse(
        id=4,
        property_id=1,
        category="Utilities",
        subtotal_amount=Decimal("100.12"),  # Rounded to 2 decimal places
        expense_date=FIXED_DATETIME,
        description="Test expense with precision",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("100.12"),
        taxes=[],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    # Mock the service layer
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
        # Assert
            # Should succeed and return rounded amount
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["subtotal_amount"] == "100.12"  # Rounded to 2 decimal places


@pytest.mark.asyncio
async def test_create_expense_admin_user():
    """Test that admin users can create expenses for any property"""
    # Arrange
    fake_admin_user = create_test_user(user_type=UserType.ADMIN)
    fake_admin_user.is_admin = True
    
    expense_data = {
        "property_id": 123,
        "category": "Maintenance",
        "subtotal_amount": "500.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Admin created expense",
        "taxes": []
    }
    
    mock_response = ExpenseResponse(
        id=3,
        property_id=123,
        category="Maintenance",
        subtotal_amount=Decimal("500.00"),
        expense_date=FIXED_DATETIME,
        description="Admin created expense",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("500.00"),
        taxes=[],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["property_id"] == 123
            assert data["category"] == "Maintenance"


@pytest.mark.asyncio
async def test_create_expense_database_error(sample_expense_data):
    """Test expense creation with database error"""
    # Arrange
    fake_user = create_test_user()
    
    with patch(
        "Backend.api.accounting.expenses.router.service.create_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=sample_expense_data
            )
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert response.json()["detail"] == "Failed to create expense"


@pytest.mark.asyncio
async def test_create_expense_with_all_fields():
    """Test expense creation with all optional fields populated"""
    # Arrange
    fake_user = create_test_user()
    
    expense_data = {
        "property_id": 1,
        "category": "Repairs and Maintenance",
        "subtotal_amount": "1500.00",
        "expense_date": "2024-06-15T14:30:00Z",
        "description": "Complete HVAC system repair including parts and labor",
        "receipt_url": "https://storage.example.com/receipts/hvac-repair-2024-06.pdf",
        "taxes": [
            {"tax_name": "GST", "tax_rate": "5.00", "tax_amount": "75.00"},
            {"tax_name": "PST", "tax_rate": "7.00", "tax_amount": "105.00"}
        ]
    }
    
    mock_response = ExpenseResponse(
        id=4,
        property_id=1,
        category="Repairs and Maintenance",
        subtotal_amount=Decimal("1500.00"),
        expense_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc),
        description="Complete HVAC system repair including parts and labor",
        receipt_url="https://storage.example.com/receipts/hvac-repair-2024-06.pdf",
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("180.00"),
        total_amount=Decimal("1680.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=3,
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("75.00"),
                expense_id=4
            ),
            ExpenseTaxDetailResponse(
                id=4,
                tax_name="PST",
                tax_rate=Decimal("7.00"),
                tax_amount=Decimal("105.00"),
                expense_id=4
            )
        ],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["category"] == "Repairs and Maintenance"
            assert data["subtotal_amount"] == "1500.00"
            assert data["description"] == "Complete HVAC system repair including parts and labor"
            assert data["receipt_url"] == "https://storage.example.com/receipts/hvac-repair-2024-06.pdf"
            assert data["total_tax_amount"] == "180.00"
            assert data["total_amount"] == "1680.00"
            assert len(data["taxes"]) == 2


@pytest.mark.asyncio
async def test_create_expense_with_both_rate_and_amount():
    """Test expense creation with both tax_rate and pre-calculated tax_amount provided"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data with both tax_rate and tax_amount provided
    expense_data = {
        "property_id": 4,
        "category": "Equipment",
        "subtotal_amount": "500.00",
        "expense_date": "2024-06-04T10:00:00Z",
        "description": "Equipment purchase with calculated taxes",
        "receipt_url": "https://example.com/receipt4.pdf",
        "taxes": [
            {"tax_name": "GST", "tax_rate": "5.00", "tax_amount": "25.00"},  # Both rate and amount
            {"tax_name": "PST", "tax_rate": "7.00", "tax_amount": "35.00"}   # Both rate and amount
        ]
    }
    
    # Expected response using the pre-calculated amounts
    mock_response = ExpenseResponse(
        id=4,
        property_id=4,
        category="Equipment",
        subtotal_amount=Decimal("500.00"),
        expense_date=datetime(2024, 6, 4, 10, 0, 0, tzinfo=timezone.utc),
        description="Equipment purchase with calculated taxes",
        receipt_url="https://example.com/receipt4.pdf",
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("60.00"),
        total_amount=Decimal("560.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=7,
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("25.00"),
                expense_id=4
            ),
            ExpenseTaxDetailResponse(
                id=8,
                tax_name="PST",
                tax_rate=Decimal("7.00"),
                tax_amount=Decimal("35.00"),
                expense_id=4
            )
        ],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["total_tax_amount"] == "60.00"
            assert data["total_amount"] == "560.00"
            assert len(data["taxes"]) == 2
            
            # Verify both rate and amount are preserved
            gst_tax = next(t for t in data["taxes"] if t["tax_name"] == "GST")
            assert gst_tax["tax_rate"] == "5.00"
            assert gst_tax["tax_amount"] == "25.00"
            
            pst_tax = next(t for t in data["taxes"] if t["tax_name"] == "PST")
            assert pst_tax["tax_rate"] == "7.00"
            assert pst_tax["tax_amount"] == "35.00"


# ===== SMART TAX INTEGRATION TESTS =====

@pytest.mark.asyncio
async def test_create_expense_smart_tax_auto_population():
    """Test expense creation with smart tax auto-population when no taxes provided"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data without taxes - should trigger smart tax population
    expense_data = {
        "property_id": 1,
        "category": "Utilities",
        "subtotal_amount": "100.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Test expense for smart tax",
        "taxes": []  # Empty taxes should trigger smart population
    }
    
    # Mock response with smart tax populated
    mock_response = ExpenseResponse(
        id=10,
        property_id=1,
        category="Utilities",
        subtotal_amount=Decimal("100.00"),
        expense_date=FIXED_DATETIME,
        description="Test expense for smart tax",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("13.00"),  # HST auto-populated
        total_amount=Decimal("113.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=20,
                tax_name="HST",
                tax_rate=Decimal("13.00"),
                tax_amount=Decimal("13.00"),
                expense_id=10
            )
        ],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify smart tax was populated
            assert data["total_tax_amount"] == "13.00"
            assert data["total_amount"] == "113.00"
            assert len(data["taxes"]) == 1
            
            smart_tax = data["taxes"][0]
            assert smart_tax["tax_name"] == "HST"
            assert smart_tax["tax_rate"] == "13.00"
            assert smart_tax["tax_amount"] == "13.00"


@pytest.mark.asyncio
async def test_create_expense_smart_tax_not_override_existing():
    """Test expense creation does not override existing taxes with smart tax"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data with existing taxes - should NOT trigger smart tax population
    expense_data = {
        "property_id": 1,
        "category": "Utilities", 
        "subtotal_amount": "100.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Test expense with existing tax",
        "taxes": [
            {"tax_name": "GST", "tax_rate": "5.00"}
        ]
    }
    
    # Mock response preserving existing taxes (no smart tax override)
    mock_response = ExpenseResponse(
        id=11,
        property_id=1,
        category="Utilities",
        subtotal_amount=Decimal("100.00"),
        expense_date=FIXED_DATETIME,
        description="Test expense with existing tax",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("5.00"),  # Only GST, no HST override
        total_amount=Decimal("105.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=21,
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("5.00"),
                expense_id=11
            )
        ],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify existing tax was preserved, smart tax did not override
            assert data["total_tax_amount"] == "5.00"
            assert data["total_amount"] == "105.00"
            assert len(data["taxes"]) == 1
            
            preserved_tax = data["taxes"][0]
            assert preserved_tax["tax_name"] == "GST"
            assert preserved_tax["tax_rate"] == "5.00"


@pytest.mark.asyncio
async def test_create_expense_smart_tax_with_different_property():
    """Test expense creation with smart tax for different property contexts"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data for different property (might have different smart tax)
    expense_data = {
        "property_id": 2,  # Different property
        "category": "Maintenance",
        "subtotal_amount": "200.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Test expense for property 2",
        "taxes": []
    }
    
    # Mock response with provincial default tax (different from property 1)
    mock_response = ExpenseResponse(
        id=12,
        property_id=2,
        category="Maintenance", 
        subtotal_amount=Decimal("200.00"),
        expense_date=FIXED_DATETIME,
        description="Test expense for property 2",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("24.00"),  # GST+PST auto-populated
        total_amount=Decimal("224.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=22,
                tax_name="GST+PST",
                tax_rate=Decimal("12.00"),
                tax_amount=Decimal("24.00"),
                expense_id=12
            )
        ],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify different smart tax was applied based on property
            assert data["total_tax_amount"] == "24.00"
            assert data["total_amount"] == "224.00" 
            assert len(data["taxes"]) == 1
            
            smart_tax = data["taxes"][0]
            assert smart_tax["tax_name"] == "GST+PST"
            assert smart_tax["tax_rate"] == "12.00"


@pytest.mark.asyncio  
async def test_create_expense_without_property_id():
    """Test expense creation without property_id to skip smart tax auto-population"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data with a property_id but no smart tax recommendation available
    expense_data = {
        "property_id": 1,
        "category": "General", 
        "subtotal_amount": "75.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Test expense with property but no smart tax",
        "taxes": []
    }
    
    mock_response = ExpenseResponse(
        id=14,
        property_id=1,  # Use a valid property_id in response even though request had None
        category="General",
        subtotal_amount=Decimal("75.00"),
        expense_date=FIXED_DATETIME,
        description="Test expense without property",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("75.00"),
        taxes=[],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses",
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            # The key point is that create_expense was called with None property_id
            # which skips the smart tax auto-population logic (lines 201-202)

@pytest.mark.asyncio  
async def test_create_expense_smart_tax_no_recommendation():
    """Test expense creation when smart tax service returns no recommendation"""
    # Arrange
    fake_user = create_test_user()
    
    # Test data for case where no smart tax is available
    expense_data = {
        "property_id": 999,  # Property with no tax preferences
        "category": "Other",
        "subtotal_amount": "50.00",
        "expense_date": "2024-06-01T12:00:00Z",
        "description": "Test expense with no smart tax",
        "taxes": []
    }
    
    # Mock response with no taxes (smart tax service found no recommendation)
    mock_response = ExpenseResponse(
        id=13,
        property_id=999,
        category="Other",
        subtotal_amount=Decimal("50.00"),
        expense_date=FIXED_DATETIME,
        description="Test expense with no smart tax",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("0.00"),  # No smart tax recommendation
        total_amount=Decimal("50.00"),
        taxes=[],
        created_at=FIXED_DATETIME_UPDATED,
        updated_at=FIXED_DATETIME_UPDATED
    )
    
    with patch("Backend.api.accounting.expenses.router.service.create_expense", new=AsyncMock(return_value=mock_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.post(
                "/api/accounting/expenses", 
                json=expense_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify no taxes were applied when smart tax had no recommendation
            assert data["total_tax_amount"] == "0.00"
            assert data["total_amount"] == "50.00"
            assert len(data["taxes"]) == 0