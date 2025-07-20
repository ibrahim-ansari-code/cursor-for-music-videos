"""
Unit tests for LLM tool handlers.
"""
import pytest
from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import json
from decimal import Decimal

from Backend.llm.tool_handlers import ToolHandlers
from Backend.models.property import Property, PropertyUnit, PropertyType, PropertyStatus
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.maintenance import MaintenanceRequest, MaintenanceStatus, MaintenancePriority


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def user_id():
    """Create a test user ID."""
    return uuid4()


@pytest.fixture
def mock_properties(user_id):
    """Create mock properties."""
    return [
        Property(
            id=1,
            name="Sunset Apartments",
            property_type=PropertyType.APARTMENT_COMPLEX.value,
            address="123 Main St",
            city="San Francisco",
            province="CA",
            postal_code="94105",
            user_id=user_id,
            status=PropertyStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            units=[]
        ),
        Property(
            id=2,
            name="Downtown Condos",
            property_type=PropertyType.COMMERCIAL.value,
            address="456 Market St",
            city="San Francisco",
            province="CA",
            postal_code="94103",
            user_id=user_id,
            status=PropertyStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            units=[]
        )
    ]


@pytest.fixture
def mock_units():
    """Create mock units."""
    property_id = 1
    return [
        PropertyUnit(
            id=1,
            property_id=property_id,
            name="Unit 101",
            bedrooms=2,
            bathrooms=1.5,
            monthly_rent=Decimal("2500"),
            is_rented=False,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        ),
        PropertyUnit(
            id=2,
            property_id=property_id,
            name="Unit 102",
            bedrooms=1,
            bathrooms=1,
            monthly_rent=Decimal("2000"),
            is_rented=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
    ]


@pytest.fixture
def mock_tenants(user_id):
    """Create mock tenants."""
    return [
        Tenant(
            id=1,
            landlord_id=user_id,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="555-1234",
            status=TenantStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        ),
        Tenant(
            id=2,
            landlord_id=user_id,
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            phone="555-5678",
            status=TenantStatus.ACTIVE,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC)
        )
    ]


class TestToolHandlers:
    """Test cases for ToolHandlers."""

    async def test_search_properties_all(self, mock_session, user_id, mock_properties, mock_units):
        """Test searching all properties."""
        # Arrange
        mock_properties[0].units = mock_units[:1]
        mock_properties[1].units = mock_units[1:]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_properties
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {}
        
        # Act
        result = await ToolHandlers.search_properties(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "properties" in result
        assert "total" in result
        assert "summary" in result
        assert result["total"] == 2
        assert len(result["properties"]) == 2
        assert result["properties"][0]["name"] == "Sunset Apartments"
        assert result["properties"][1]["name"] == "Downtown Condos"

    async def test_search_properties_vacant(self, mock_session, user_id, mock_properties, mock_units):
        """Test searching vacant properties."""
        # Arrange
        mock_properties[0].units = [u for u in mock_units if not u.is_rented]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_properties[0]]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {"status": "vacant"}
        
        # Act
        result = await ToolHandlers.search_properties(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "properties" in result
        assert result["total"] == 1
        assert result["properties"][0]["name"] == "Sunset Apartments"
        assert result["properties"][0]["vacant_units"] == 1

    async def test_search_properties_by_location(self, mock_session, user_id, mock_properties):
        """Test searching properties by location."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_properties[0]]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {"location": "94105"}
        
        # Act
        result = await ToolHandlers.search_properties(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "properties" in result
        assert result["total"] == 1
        assert result["properties"][0]["name"] == "Sunset Apartments"

    async def test_get_tenant_info_by_name(self, mock_session, user_id, mock_tenants):
        """Test getting tenant info by name."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_tenants[0]]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {"name": "john"}
        
        # Act
        result = await ToolHandlers.get_tenant_info(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "tenants" in result
        assert result["total"] == 1
        assert result["tenants"][0]["name"] == "John Doe"
        assert result["tenants"][0]["email"] == "john@example.com"
        assert result["tenants"][0]["phone"] == "555-1234"

    async def test_get_tenant_info_not_found(self, mock_session, user_id):
        """Test getting tenant info when none found."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {"name": "nonexistent"}
        
        # Act
        result = await ToolHandlers.get_tenant_info(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "tenants" in result
        assert result["total"] == 0
        assert result["tenants"] == []

    async def test_get_financial_summary(self, mock_session, user_id):
        """Test getting financial summary."""
        # Arrange
        current_month = datetime.now(UTC).replace(day=1)
        
        # Mock payments data (the handler queries payments)
        payments_scalars = MagicMock()
        payments_scalars.all.return_value = [
            MagicMock(amount=Decimal("2500.00")),
            MagicMock(amount=Decimal("2500.00"))
        ]
        payments_result = MagicMock()
        payments_result.scalars.return_value = payments_scalars
        
        # Mock expenses data
        expenses_scalars = MagicMock()
        expenses_scalars.all.return_value = [
            MagicMock(total_amount=Decimal("1000.00"))
        ]
        expenses_result = MagicMock()
        expenses_result.scalars.return_value = expenses_scalars
        
        mock_session.execute = AsyncMock(side_effect=[payments_result, expenses_result])
        
        args = {"period": "current_month"}
        
        # Act
        result = await ToolHandlers.get_financial_summary(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "period" in result
        assert "income" in result
        assert "expenses" in result
        assert "net_income" in result
        assert result["income"]["total"] == 5000.0
        assert result["expenses"]["total"] == 1000.0
        assert result["net_income"] == 4000.0

    async def test_get_maintenance_requests_open(self, mock_session, user_id):
        """Test getting open maintenance requests."""
        # Arrange
        requests = [
            MaintenanceRequest(
                id=1,
                property_id=1,
                unit_id=1,
                user_id=user_id,
                issue_title="Leaky faucet",
                description="Kitchen faucet is dripping",
                status=MaintenanceStatus.PENDING,
                priority=MaintenancePriority.MEDIUM,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            MaintenanceRequest(
                id=2,
                property_id=1,
                unit_id=2,
                user_id=user_id,
                issue_title="AC not working",
                description="Air conditioning unit not cooling",
                status=MaintenanceStatus.IN_PROGRESS,
                priority=MaintenancePriority.HIGH,
                created_at=datetime.now(UTC) - timedelta(days=2),
                updated_at=datetime.now(UTC)
            )
        ]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = requests
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {"status": "open"}
        
        # Act
        result = await ToolHandlers.get_maintenance_requests(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "requests" in result
        assert "total" in result
        assert "summary" in result
        assert result["total"] == 2
        assert len(result["requests"]) == 2
        assert result["requests"][0]["title"] == "Leaky faucet"
        assert result["requests"][1]["title"] == "AC not working"
        assert result["requests"][0]["priority"] == MaintenancePriority.MEDIUM.value
        assert result["requests"][1]["priority"] == MaintenancePriority.HIGH.value

    async def test_get_lease_expiry_info(self, mock_session, user_id):
        """Test getting lease expiry information."""
        # Arrange
        leases = [
            Lease(
                id=1,
                property_id=1,
                unit_id=1,
                tenant_id=1,
                start_date=datetime.now(UTC).date() - timedelta(days=300),
                end_date=datetime.now(UTC).date() + timedelta(days=30),
                monthly_rent=Decimal("2500"),
                status=LeaseStatus.ACTIVE,
                security_deposit=Decimal("2500"),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            ),
            Lease(
                id=2,
                property_id=2,
                unit_id=2,
                tenant_id=2,
                start_date=datetime.now(UTC).date() - timedelta(days=200),
                end_date=datetime.now(UTC).date() + timedelta(days=60),
                monthly_rent=Decimal("3000"),
                status=LeaseStatus.ACTIVE,
                security_deposit=Decimal("3000"),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        ]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = leases
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {"days": 90}
        
        # Act
        result = await ToolHandlers.get_lease_expiry_info(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "leases" in result
        assert "total" in result
        assert "summary" in result
        assert result["total"] == 2
        assert len(result["leases"]) == 2
        assert result["leases"][0]["monthly_rent"] == 2500.0
        assert result["leases"][1]["monthly_rent"] == 3000.0
        assert result["leases"][0]["days_until_expiry"] == 30
        assert result["leases"][1]["days_until_expiry"] == 60

    async def test_get_payment_status_overdue(self, mock_session, user_id):
        """Test getting overdue payment status."""
        # Arrange
        overdue_invoices = [
            MagicMock(
                id=1,
                tenant_id=1,
                amount=Decimal("2500"),
                due_date=datetime.now(UTC) - timedelta(days=10),
                status="PENDING",
                tenant=MagicMock(first_name="John", last_name="Doe"),
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
        ]
        
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = overdue_invoices
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        args = {"status": "overdue"}
        
        # Act
        result = await ToolHandlers.get_payment_status(args, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "payments" in result
        assert "total" in result
        assert "summary" in result
        assert result["total"] == 1
        assert result["payments"][0]["balance"] == 2500.0
        assert result["payments"][0]["is_overdue"] is True
        assert result["payments"][0]["days_overdue"] == 10

    async def test_handle_tool_call_success(self, mock_session, user_id):
        """Test handling a tool call successfully."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        tool_name = "search_properties"
        arguments = json.dumps({"status": "vacant"})
        
        # Act
        result = await ToolHandlers.handle_tool_call(tool_name, arguments, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        # The search_properties handler returns a dict with a 'properties' key
        assert "properties" in result

    async def test_handle_tool_call_invalid_tool(self, mock_session, user_id):
        """Test handling an invalid tool call."""
        # Arrange
        tool_name = "invalid_tool"
        arguments = "{}"
        
        # Act
        result = await ToolHandlers.handle_tool_call(tool_name, arguments, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "error" in result
        assert "Unknown tool: invalid_tool" in result["error"]

    async def test_handle_tool_call_invalid_json(self, mock_session, user_id):
        """Test handling a tool call with invalid JSON."""
        # Arrange
        tool_name = "search_properties"
        arguments = "invalid json"
        
        # Act
        result = await ToolHandlers.handle_tool_call(tool_name, arguments, user_id, mock_session)
        
        # Assert
        assert isinstance(result, dict)
        assert "error" in result
        assert "Invalid arguments format" in result["error"]