"""
Unit tests for the expenses retrieval service functions using hybrid API testing pattern.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone
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
    # Store any mocks that might be created during the test
    mocks_to_reset = []
    
    # Store original dependency_overrides to detect new mocks
    original_overrides = dict(app.dependency_overrides)
    
    yield
    
    # Clear all dependency overrides
    app.dependency_overrides.clear()
    
    # Reset any AsyncMock objects that were created
    # This ensures call counts and side effects don't leak between tests
    for override in original_overrides.values():
        if isinstance(override, AsyncMock):
            override.reset_mock()
        else:
            # Check if it's a wrapped function (e.g., from lambda or decorator)
            wrapped = getattr(override, '__wrapped__', None)
            if wrapped and isinstance(wrapped, AsyncMock):
                wrapped.reset_mock()

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


@pytest.fixture
def sample_expenses():
    """Sample list of expense responses"""
    return [
        ExpenseResponse(
            id=1,
            property_id=123,
            category="Utilities",
            subtotal_amount=Decimal("100.00"),
            expense_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            description="Electricity bill",
            receipt_url="https://example.com/receipt1.pdf",
            payment_method=PaymentMethod.OTHER,
            total_tax_amount=Decimal("10.00"),
            total_amount=Decimal("110.00"),
            taxes=[
                ExpenseTaxDetailResponse(
                    id=1,
                    tax_name="GST",
                    tax_rate=Decimal("10.00"),
                    tax_amount=Decimal("10.00"),
                    expense_id=1
                )
            ],
            created_at=datetime(2024, 1, 10, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 10, tzinfo=timezone.utc)
        ),
        ExpenseResponse(
            id=2,
            property_id=123,
            category="Utilities",
            subtotal_amount=Decimal("50.00"),
            expense_date=datetime(2024, 1, 25, tzinfo=timezone.utc),
            description="Water bill",
            receipt_url=None,
            payment_method=PaymentMethod.OTHER,
            total_tax_amount=Decimal("5.00"),
            total_amount=Decimal("55.00"),
            taxes=[
                ExpenseTaxDetailResponse(
                    id=2,
                    tax_name="GST",
                    tax_rate=Decimal("10.00"),
                    tax_amount=Decimal("5.00"),
                    expense_id=2
                )
            ],
            created_at=datetime(2024, 1, 20, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 20, tzinfo=timezone.utc)
        )
    ]


@pytest.mark.asyncio
async def test_get_expenses_success(sample_expenses):
    """Test successful expense retrieval for landlord"""
    # Arrange
    fake_user = create_test_user()

    # Mock the service to return paginated response format
    paginated_response = {
        "items": sample_expenses,
        "has_more": False
    }

    with patch("Backend.api.accounting.expenses.router.service.get_expenses", new=AsyncMock(return_value=paginated_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get("/api/accounting/expenses")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, dict)
            assert "items" in data
            assert "has_more" in data
            assert isinstance(data["items"], list)
            assert len(data["items"]) == 2
            assert data["has_more"] is False

            # Verify first expense
            assert data["items"][0]["id"] == 1
            assert data["items"][0]["category"] == "Utilities"
            assert data["items"][0]["total_amount"] == "110.00"


@pytest.mark.asyncio
async def test_get_expenses_with_filters(sample_expenses):
    """Test expense retrieval with all filters applied"""
    # Arrange
    fake_user = create_test_user()

    # Mock the service to return paginated response format
    paginated_response = {
        "items": sample_expenses,
        "has_more": False
    }

    with patch("Backend.api.accounting.expenses.router.service.get_expenses", new=AsyncMock(return_value=paginated_response)) as mock_get:
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get(
                "/api/accounting/expenses",
                params={
                    "property_id": 123,
                    "category": "Utilities",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 2

            # Verify service was called with correct filters
            mock_get.assert_awaited_once()
            
            # Get the call arguments - await_args returns (args, kwargs) tuple
            if mock_get.await_args:
                call_args = mock_get.await_args[0]  # positional arguments
                
                # The router passes these as positional arguments to the service function
                # service.get_expenses(session, current_user, property_id, category, start_date, end_date, search, limit, offset)
                # Check by matching the signature order
                assert len(call_args) >= 6, "Service should be called with at least 6 positional arguments"
                # args[0] is session, args[1] is current_user
                assert call_args[2] == 123  # property_id
                assert call_args[3] == "Utilities"  # category
                assert call_args[4] == date(2024, 1, 1)  # start_date
                assert call_args[5] == date(2024, 1, 31)  # end_date


@pytest.mark.asyncio
async def test_get_expenses_with_pagination(sample_expenses):
    """Test expense retrieval with pagination parameters"""
    # Arrange
    fake_user = create_test_user()

    # Mock the service to return paginated response format with has_more=True
    paginated_response = {
        "items": [sample_expenses[0]],  # Reuse fixture data instead of duplicating
        "has_more": True
    }

    with patch("Backend.api.accounting.expenses.router.service.get_expenses", new=AsyncMock(return_value=paginated_response)) as mock_get:
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get(
                "/api/accounting/expenses",
                params={
                    "limit": 50,
                    "offset": 100
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "items" in data
            assert "has_more" in data
            assert len(data["items"]) == 1
            assert data["has_more"] is True

            # Verify service was called with correct pagination parameters
            mock_get.assert_awaited_once()
            
            # Get the actual call to inspect arguments
            call = mock_get.await_args_list[0]
            
            # The router should pass these as positional arguments in order:
            # session, current_user, property_id, category, start_date, end_date, search, limit, offset
            args = call[0]
            
            # Instead of checking by position, verify the call included our pagination values
            # This is more maintainable as it doesn't break if argument order changes
            assert any(arg == 50 for arg in args), "limit=50 not found in service call"
            assert any(arg == 100 for arg in args), "offset=100 not found in service call"


@pytest.mark.asyncio
async def test_get_expenses_pagination_limits():
    """Test expense retrieval with pagination limit validation"""
    # Arrange
    fake_user = create_test_user()

    paginated_response = {
        "items": [],
        "has_more": False
    }

    with patch("Backend.api.accounting.expenses.router.service.get_expenses", new=AsyncMock(return_value=paginated_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            # Test limit too high (should be capped at 500)
            response = client.get(
                "/api/accounting/expenses",
                params={"limit": 1000}
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test negative offset
            response = client.get(
                "/api/accounting/expenses",
                params={"offset": -1}
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_get_expenses_admin_access():
    """Test that admin can access all expenses"""
    # Arrange
    fake_admin_user = create_test_user(user_type=UserType.ADMIN)
    fake_admin_user.is_admin = True

    admin_expenses = [
        ExpenseResponse(
            id=10,
            property_id=456,  # Different property
            category="Repairs",
            subtotal_amount=Decimal("150.00"),
            expense_date=datetime(2024, 3, 10, tzinfo=timezone.utc),
            description="Plumbing repair",
            receipt_url=None,
            payment_method=PaymentMethod.OTHER,
            total_tax_amount=Decimal("15.00"),
            total_amount=Decimal("165.00"),
            taxes=[],
            created_at=datetime(2024, 3, 5, tzinfo=timezone.utc),
            updated_at=datetime(2024, 3, 5, tzinfo=timezone.utc)
        )
    ]

    paginated_response = {
        "items": admin_expenses,
        "has_more": False
    }

    with patch("Backend.api.accounting.expenses.router.service.get_expenses", new=AsyncMock(return_value=paginated_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get(
                "/api/accounting/expenses",
                params={"property_id": 456}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["property_id"] == 456


@pytest.mark.asyncio
async def test_get_expenses_unauthorized():
    """Test expense retrieval for unauthorized property access"""
    # Arrange
    fake_user = create_test_user()

    with patch(
        "Backend.api.accounting.expenses.router.service.get_expenses",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view expenses for this property"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get(
                "/api/accounting/expenses",
                params={"property_id": 999}
            )

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json()[
                "detail"] == "Not authorized to view expenses for this property"


@pytest.mark.asyncio
async def test_get_expenses_empty_result():
    """Test expense retrieval with no results"""
    # Arrange
    fake_user = create_test_user()

    paginated_response = {
        "items": [],
        "has_more": False
    }

    with patch("Backend.api.accounting.expenses.router.service.get_expenses", new=AsyncMock(return_value=paginated_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get("/api/accounting/expenses")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, dict)
            assert "items" in data
            assert "has_more" in data
            assert isinstance(data["items"], list)
            assert len(data["items"]) == 0
            assert data["has_more"] is False


@pytest.mark.asyncio
async def test_get_expenses_date_filtering():
    """Test expense retrieval with date range filtering"""
    # Arrange
    fake_user = create_test_user()

    filtered_expenses = [
        ExpenseResponse(
            id=3,
            property_id=123,
            category="Maintenance",
            subtotal_amount=Decimal("300.00"),
            expense_date=datetime(2024, 2, 15, tzinfo=timezone.utc),
            description="HVAC maintenance",
            receipt_url=None,
            payment_method=PaymentMethod.OTHER,
            total_tax_amount=Decimal("30.00"),
            total_amount=Decimal("330.00"),
            taxes=[],
            created_at=datetime(2024, 2, 10, tzinfo=timezone.utc),
            updated_at=datetime(2024, 2, 10, tzinfo=timezone.utc)
        )
    ]

    paginated_response = {
        "items": filtered_expenses,
        "has_more": False
    }

    with patch("Backend.api.accounting.expenses.router.service.get_expenses", new=AsyncMock(return_value=paginated_response)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get(
                "/api/accounting/expenses",
                params={
                    "start_date": "2024-02-01",
                    "end_date": "2024-02-28"
                }
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 1
            assert data["items"][0]["expense_date"].startswith("2024-02-15")


@pytest.mark.asyncio
async def test_get_expense_by_id_success():
    """Test successful retrieval of single expense by ID"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 42

    single_expense = ExpenseResponse(
        id=expense_id,
        property_id=101,
        category="Utilities",
        subtotal_amount=Decimal("100.00"),
        expense_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
        description="Electricity bill",
        receipt_url="https://example.com/receipt.pdf",
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("5.00"),
        total_amount=Decimal("105.00"),
        taxes=[
            ExpenseTaxDetailResponse(
                id=1,
                tax_name="GST",
                tax_rate=Decimal("5.00"),
                tax_amount=Decimal("5.00"),
                expense_id=expense_id
            )
        ],
        created_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    )

    with patch("Backend.api.accounting.expenses.router.service.get_expense_by_id", new=AsyncMock(return_value=single_expense)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get(f"/api/accounting/expenses/{expense_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == expense_id
            assert data["total_tax_amount"] == "5.00"
            assert data["total_amount"] == "105.00"
            assert len(data["taxes"]) == 1
            assert data["taxes"][0]["tax_name"] == "GST"
            assert data["property_id"] == 101
            assert data["category"] == "Utilities"
            assert data["description"] == "Electricity bill"


@pytest.mark.asyncio
async def test_get_expense_by_id_not_found():
    """Test retrieval of non-existent expense"""
    # Arrange
    fake_user = create_test_user()

    with patch(
        "Backend.api.accounting.expenses.router.service.get_expense_by_id",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get("/api/accounting/expenses/9999")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.json()["detail"] == "Expense not found"


@pytest.mark.asyncio
async def test_get_expense_by_id_unauthorized():
    """Test retrieval of expense user doesn't have access to"""
    # Arrange
    fake_user = create_test_user()

    with patch(
        "Backend.api.accounting.expenses.router.service.get_expense_by_id",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this expense"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get("/api/accounting/expenses/123")

            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json()[
                "detail"] == "Not authorized to access this expense"


@pytest.mark.asyncio
async def test_get_expense_by_id_with_multiple_taxes():
    """Test retrieval of expense with multiple tax details"""
    # Arrange
    fake_user = create_test_user()
    expense_id = 100

    expense_with_taxes = ExpenseResponse(
        id=expense_id,
        property_id=201,
        category="Supplies",
        subtotal_amount=Decimal("200.00"),
        expense_date=datetime(2024, 6, 15, tzinfo=timezone.utc),
        description="Office supplies with multiple taxes",
        receipt_url="https://example.com/receipt-multi-tax.pdf",
        payment_method=PaymentMethod.OTHER,
        total_tax_amount=Decimal("26.00"),
        total_amount=Decimal("226.00"),
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
                tax_rate=Decimal("8.00"),
                tax_amount=Decimal("16.00"),
                expense_id=expense_id
            )
        ],
        created_at=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    )

    with patch("Backend.api.accounting.expenses.router.service.get_expense_by_id", new=AsyncMock(return_value=expense_with_taxes)):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get(f"/api/accounting/expenses/{expense_id}")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_tax_amount"] == "26.00"
            assert data["total_amount"] == "226.00"
            assert len(data["taxes"]) == 2

            # Verify GST
            gst_tax = next(t for t in data["taxes"] if t["tax_name"] == "GST")
            assert gst_tax["tax_rate"] == "5.00"
            assert gst_tax["tax_amount"] == "10.00"

            # Verify PST
            pst_tax = next(t for t in data["taxes"] if t["tax_name"] == "PST")
            assert pst_tax["tax_rate"] == "8.00"
            assert pst_tax["tax_amount"] == "16.00"


@pytest.mark.asyncio
async def test_get_expense_by_id_invalid_id():
    """Test retrieval with invalid expense ID format"""
    # Arrange
    fake_user = create_test_user()

    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.get("/api/accounting/expenses/not-a-number")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any(
            error["loc"] == [
                "path", "expense_id"] and error["type"] == "int_parsing"
            for error in errors
        )


@pytest.mark.asyncio
async def test_get_expenses_database_error():
    """Test expense retrieval with database error"""
    # Arrange
    fake_user = create_test_user()

    with patch(
        "Backend.api.accounting.expenses.router.service.get_expenses",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        ))
    ):
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.get("/api/accounting/expenses")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert response.json()["detail"] == "Database connection failed"
