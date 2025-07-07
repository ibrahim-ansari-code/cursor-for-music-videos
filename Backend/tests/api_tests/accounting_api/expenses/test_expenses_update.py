"""
Unit tests for the expenses update service functions using hybrid API testing pattern.
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
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )


@pytest.mark.asyncio
async def test_update_expense_success():
    """Test successful expense update"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 123
    
    update_data = {
        "property_id": 1,
        "category": "Utilities",
        "subtotal_amount": "100.00",
        "description": "Updated expense",
        "receipt_url": "https://new-receipt.com/receipt.jpg",
        "taxes": [],
        "payment_method": PaymentMethod.OTHER
    }
    
    expected_response = ExpenseResponse(
        id=expense_id,
        property_id=1,
        category="Utilities",
        subtotal_amount=Decimal("100.00"),
        expense_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        description="Updated expense",
        receipt_url="https://new-receipt.com/receipt.jpg",
        payment_method=PaymentMethod.OTHER,
        taxes=[],
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("100.00"),
        created_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    blob_to_delete = "https://old-receipt.com/old.jpg"
    
    # Mock the service layer to return tuple (response, blob_to_delete)
    with patch(
        "Backend.api.accounting.expenses.router.service.update_expense",
        new=AsyncMock(return_value=(expected_response, blob_to_delete))
    ):
        # Mock delete_blob_with_error_handling
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                # Act
                response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
                
                # Assert
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["id"] == expense_id
                assert data["category"] == "Utilities"
                assert data["subtotal_amount"] == "100.00"
                assert data["description"] == "Updated expense"
                assert data["receipt_url"] == "https://new-receipt.com/receipt.jpg"
                
                # Verify blob deletion was scheduled (background task)
                # Note: Background tasks are executed synchronously in TestClient
                mock_delete_blob.assert_called_once_with(blob_to_delete)


@pytest.mark.asyncio
async def test_update_expense_tax_and_total_recalculation():
    """Test expense update with tax calculations"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 789
    
    update_data = {
        "property_id": 3,
        "category": "Supplies",
        "subtotal_amount": "200.00",
        "description": "Office supplies",
        "receipt_url": "https://new-receipt.com/supplies.jpg",
        "taxes": [
            {"tax_name": "GST", "tax_rate": "5.00"},
            {"tax_name": "PST", "tax_rate": "7.00"}
        ],
        "payment_method": PaymentMethod.OTHER
    }
    
    expected_response = ExpenseResponse(
        id=expense_id,
        property_id=3,
        category="Supplies",
        subtotal_amount=Decimal("200.00"),
        expense_date=datetime(2024, 6, 2, tzinfo=timezone.utc),
        description="Office supplies",
        receipt_url="https://new-receipt.com/supplies.jpg",
        payment_method=PaymentMethod.OTHER,
        taxes=[
            ExpenseTaxDetailResponse(
                id=1,
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("10.00"),
                expense_id=expense_id
            ),
            ExpenseTaxDetailResponse(
                id=2,
                tax_name="PST",
                tax_rate=Decimal("7.00"),
                tax_amount=Decimal("14.00"),
                expense_id=expense_id
            )
        ],
        total_tax_amount=Decimal("24.00"),
        total_amount=Decimal("224.00"),
        created_at=datetime(2024, 6, 2, tzinfo=timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    with patch(
        "Backend.api.accounting.expenses.router.service.update_expense",
        new=AsyncMock(return_value=(expected_response, None))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
            
            assert response.status_code == status.HTTP_200_OK
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
async def test_update_expense_not_found():
    """Test update of non-existent expense"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 999
    
    update_data = {
        "property_id": 4,
        "category": "Travel",
        "subtotal_amount": "300.00",
        "description": "Business trip",
        "receipt_url": "https://new-receipt.com/travel.jpg",
        "taxes": [],
        "payment_method": PaymentMethod.OTHER
    }
    
    with patch(
        "Backend.api.accounting.expenses.router.service.update_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "Expense not found"


@pytest.mark.asyncio
async def test_update_expense_unauthorized_user():
    """Test update by unauthorized user"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 1001
    
    update_data = {
        "property_id": 5,
        "category": "Insurance",
        "subtotal_amount": "400.00",
        "description": "Annual insurance",
        "receipt_url": "https://new-receipt.com/insurance.jpg",
        "taxes": [],
        "payment_method": PaymentMethod.OTHER
    }
    
    with patch(
        "Backend.api.accounting.expenses.router.service.update_expense",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json()["detail"] == "Not authorized"


@pytest.mark.asyncio
async def test_update_expense_invalid_input():
    """Test update with invalid input data"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 1002
    
    # Invalid data - negative subtotal_amount
    update_data = {
        "property_id": 6,
        "category": "Misc",
        "subtotal_amount": "-50.00",
        "description": "Negative subtotal",
        "receipt_url": "https://new-receipt.com/misc.jpg",
        "taxes": [],
        "payment_method": PaymentMethod.OTHER
    }
    
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any(
            error["loc"][-1] == "subtotal_amount" and "greater than or equal to 0" in error["msg"]
            for error in errors
        )


@pytest.mark.asyncio
async def test_update_expense_receipt_blob_deletion_scheduled():
    """Test that receipt blob deletion is scheduled when receipt URL changes"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 456
    
    update_data = {
        "property_id": 2,
        "category": "Repairs",
        "subtotal_amount": "250.00",
        "description": "Roof repair",
        "receipt_url": "https://new-receipt.com/roof.jpg",
        "taxes": [],
        "payment_method": PaymentMethod.OTHER
    }
    
    expected_response = ExpenseResponse(
        id=expense_id,
        property_id=2,
        category="Repairs",
        subtotal_amount=Decimal("250.00"),
        expense_date=datetime(2024, 6, 3, tzinfo=timezone.utc),
        description="Roof repair",
        receipt_url="https://new-receipt.com/roof.jpg",
        payment_method=PaymentMethod.OTHER,
        taxes=[],
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("250.00"),
        created_at=datetime(2024, 6, 3, tzinfo=timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    blob_to_delete = "https://old-receipt.com/oldroof.jpg"
    
    with patch(
        "Backend.api.accounting.expenses.router.service.update_expense",
        new=AsyncMock(return_value=(expected_response, blob_to_delete))
    ):
        with patch("Backend.api.accounting.expenses.router.delete_blob_with_error_handling") as mock_delete_blob:
            app.dependency_overrides[get_current_user] = lambda: fake_user
            app.dependency_overrides[get_session] = lambda: AsyncMock()
            
            with TestClientWithHost(app) as client:
                response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["receipt_url"] == "https://new-receipt.com/roof.jpg"
                
                # Verify blob deletion was called
                mock_delete_blob.assert_called_once_with(blob_to_delete)


@pytest.mark.asyncio
async def test_update_expense_partial_update():
    """Test partial update of expense (only some fields)"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 333
    
    # Partial update - only category and description
    update_data = {
        "category": "Office Supplies",
        "description": "Updated description only",
        "payment_method": PaymentMethod.OTHER
    }
    
    expected_response = ExpenseResponse(
        id=expense_id,
        property_id=1,  # Unchanged
        category="Office Supplies",  # Updated
        subtotal_amount=Decimal("150.00"),  # Unchanged
        expense_date=datetime(2024, 5, 15, tzinfo=timezone.utc),  # Unchanged
        description="Updated description only",  # Updated
        receipt_url="https://example.com/original-receipt.pdf",  # Unchanged
        payment_method=PaymentMethod.OTHER,
        taxes=[],
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("150.00"),
        created_at=datetime(2024, 5, 15, tzinfo=timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    with patch(
        "Backend.api.accounting.expenses.router.service.update_expense",
        new=AsyncMock(return_value=(expected_response, None))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["category"] == "Office Supplies"
            assert data["description"] == "Updated description only"
            assert data["property_id"] == 1  # Unchanged
            assert data["subtotal_amount"] == "150.00"  # Unchanged


@pytest.mark.asyncio
async def test_update_expense_admin_user():
    """Test that admin users can update any expense"""
    # Arrange
    fake_admin_user = create_test_user(user_type=UserType.ADMIN)
    fake_admin_user.is_admin = True
    expense_id = 555
    
    update_data = {
        "property_id": 999,  # Different property
        "category": "Admin Update",
        "subtotal_amount": "1000.00",
        "description": "Admin updated expense",
        "payment_method": PaymentMethod.OTHER
    }
    
    expected_response = ExpenseResponse(
        id=expense_id,
        property_id=999,
        category="Admin Update",
        subtotal_amount=Decimal("1000.00"),
        expense_date=datetime(2024, 6, 10, tzinfo=timezone.utc),
        description="Admin updated expense",
        receipt_url=None,
        payment_method=PaymentMethod.OTHER,
        taxes=[],
        total_tax_amount=Decimal("0.00"),
        total_amount=Decimal("1000.00"),
        created_at=datetime(2024, 6, 10, tzinfo=timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    with patch(
        "Backend.api.accounting.expenses.router.service.update_expense",
        new=AsyncMock(return_value=(expected_response, None))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            response = client.put(f"/api/accounting/expenses/{expense_id}", json=update_data)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["property_id"] == 999
            assert data["category"] == "Admin Update"