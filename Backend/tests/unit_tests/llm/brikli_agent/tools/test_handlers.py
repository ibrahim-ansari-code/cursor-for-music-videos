"""
Unit tests for ToolHandlers class
"""
import json
import pytest
from datetime import date, datetime, UTC
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from Backend.llm.brikli_agent.tools.handlers import ToolHandlers


@pytest.fixture
def mock_session():
    """Create mock database session"""
    return AsyncMock()


@pytest.fixture
def sample_user_id():
    """Create sample user ID"""
    return uuid4()


class TestToolHandlers:
    """Test cases for ToolHandlers class"""

    async def test_handle_tool_call_success(self, mock_session, sample_user_id):
        """Test successful tool call routing"""
        # Arrange
        tool_name = "search_properties"
        arguments = '{"status": "Active"}'

        with patch.object(ToolHandlers, 'search_properties', return_value={"properties": []}):
            # Act
            result = await ToolHandlers.handle_tool_call(tool_name, arguments, sample_user_id, mock_session)

            # Assert
            assert "properties" in result
            ToolHandlers.search_properties.assert_called_once_with({"status": "Active"}, sample_user_id, mock_session)

    async def test_handle_tool_call_invalid_json(self, mock_session, sample_user_id):
        """Test tool call with invalid JSON arguments"""
        # Arrange
        tool_name = "search_properties"
        arguments = '{"status": "Active"'  # Invalid JSON

        # Act
        result = await ToolHandlers.handle_tool_call(tool_name, arguments, sample_user_id, mock_session)

        # Assert
        assert "error" in result
        assert "Invalid arguments format" in result["error"]

    async def test_handle_tool_call_unknown_tool(self, mock_session, sample_user_id):
        """Test tool call with unknown tool name"""
        # Arrange
        tool_name = "unknown_tool"
        arguments = "{}"

        # Act
        result = await ToolHandlers.handle_tool_call(tool_name, arguments, sample_user_id, mock_session)

        # Assert
        assert "error" in result
        assert "Unknown tool: unknown_tool" in result["error"]

    async def test_handle_tool_call_execution_error(self, mock_session, sample_user_id):
        """Test tool call with execution error"""
        # Arrange
        tool_name = "search_properties"
        arguments = "{}"

        with patch.object(ToolHandlers, 'search_properties', side_effect=Exception("Database error")):
            # Act
            result = await ToolHandlers.handle_tool_call(tool_name, arguments, sample_user_id, mock_session)

            # Assert
            assert "error" in result
            assert "Tool execution failed" in result["error"]

    async def test_search_properties_basic(self, mock_session, sample_user_id):
        """Test basic property search"""
        # Arrange
        args = {"status": "Active"}

        # Mock property with units
        mock_property = Mock()
        mock_property.id = 1
        mock_property.name = "Test Property"
        mock_property.address = "123 Main St"
        mock_property.city = "Test City"
        mock_property.province = "Test Province"
        mock_property.postal_code = "12345"
        mock_property.status.value = "ACTIVE"
        mock_property.property_type = "Residential"
        mock_property.created_at = datetime.now(UTC)

        # Mock units
        mock_unit = Mock()
        mock_unit.monthly_rent = 1000
        mock_unit.is_rented = True
        mock_property.units = [mock_unit]

        # Mock database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_property]
        mock_session.execute.return_value = mock_result

        # Act
        result = await ToolHandlers.search_properties(args, sample_user_id, mock_session)

        # Assert
        assert "properties" in result
        assert "summary" in result
        assert len(result["properties"]) == 1
        assert result["properties"][0]["name"] == "Test Property"
        assert result["summary"]["total_properties"] == 1

    async def test_search_properties_with_filters(self, mock_session, sample_user_id):
        """Test property search with multiple filters"""
        # Arrange
        args = {
            "status": "Active",
            "city": "Toronto",
            "property_type": "Residential",
            "min_rent": 800,
            "max_rent": 1200,
            "has_vacancies": True
        }

        # Mock property with vacant unit
        mock_property = Mock()
        mock_property.id = 1
        mock_property.name = "Toronto Property"
        mock_property.address = "456 Queen St"
        mock_property.city = "Toronto"
        mock_property.province = "ON"
        mock_property.postal_code = "M5V 1A1"
        mock_property.status.value = "ACTIVE"
        mock_property.property_type = "Residential"
        mock_property.created_at = datetime.now(UTC)

        mock_unit = Mock()
        mock_unit.monthly_rent = 1000
        mock_unit.is_rented = False  # Vacant
        mock_property.units = [mock_unit]

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_property]
        mock_session.execute.return_value = mock_result

        # Act
        result = await ToolHandlers.search_properties(args, sample_user_id, mock_session)

        # Assert
        assert len(result["properties"]) == 1
        assert result["properties"][0]["vacant_units"] == 1
        assert result["properties"][0]["occupancy_rate"] == 0.0

    async def test_get_tenant_info_basic(self, mock_session, sample_user_id):
        """Test basic tenant information retrieval"""
        # Arrange
        args = {"tenant_name": "John Doe", "include_lease_details": False}

        # Mock tenant without lease
        mock_tenant = Mock()
        mock_tenant.id = 1
        mock_tenant.first_name = "John"
        mock_tenant.last_name = "Doe"
        mock_tenant.email = "john.doe@example.com"
        mock_tenant.phone = "555-0123"
        mock_tenant.status.value = "ACTIVE"
        mock_tenant.assigned_units = []
        mock_tenant.current_property = None

        # Mock the session to return tenant for first query, empty for lease queries
        tenant_result = Mock()
        tenant_result.scalars.return_value.all.return_value = [mock_tenant]

        lease_result = Mock()
        lease_result.scalars.return_value.first.return_value = None

        # Set up mock session to return different results for different queries
        mock_session.execute.side_effect = [tenant_result, lease_result]

        # Act
        result = await ToolHandlers.get_tenant_info(args, sample_user_id, mock_session)

        # Assert
        assert "tenants" in result
        assert len(result["tenants"]) == 1
        assert result["tenants"][0]["name"] == "John Doe"
        assert result["tenants"][0]["email"] == "john.doe@example.com"

    async def test_get_tenant_info_with_lease_details(self, mock_session, sample_user_id):
        """Test tenant info with lease details"""
        # Arrange
        args = {"tenant_name": "John Doe", "include_lease_details": True}

        # Mock tenant
        mock_tenant = Mock()
        mock_tenant.id = 1
        mock_tenant.first_name = "John"
        mock_tenant.last_name = "Doe"
        mock_tenant.email = "john.doe@example.com"
        mock_tenant.phone = "555-0123"
        mock_tenant.status.value = "ACTIVE"
        mock_tenant.assigned_units = []
        mock_tenant.current_property = None

        # Mock lease
        # Use fixed dates for consistent testing
        fixed_start_date = date(2024, 1, 1)
        fixed_end_date = date(2024, 12, 31)
        
        mock_lease = Mock()
        mock_lease.id = 1
        mock_lease.start_date = fixed_start_date
        mock_lease.end_date = fixed_end_date
        mock_lease.monthly_rent = 1200
        mock_lease.status.value = "Active"

        # Setup session execution results
        mock_tenant_result = Mock()
        mock_tenant_result.scalars.return_value.all.return_value = [mock_tenant]

        mock_lease_result = Mock()
        mock_lease_result.scalar_one_or_none.return_value = mock_lease

        mock_session.execute.side_effect = [mock_tenant_result, mock_lease_result]

        # Act
        result = await ToolHandlers.get_tenant_info(args, sample_user_id, mock_session)

        # Assert
        assert result["tenants"][0]["lease"]["monthly_rent"] == 1200
        assert result["tenants"][0]["lease"]["status"] == "Active"

    async def test_search_lease_documents_placeholder_mode(self, mock_session, sample_user_id):
        """Test search_lease_documents with placeholder EmbeddingService"""
        # Arrange
        args = {"query": "pet policy", "limit": 5}

        # Act
        result = await ToolHandlers.search_lease_documents(args, sample_user_id, mock_session)

        # Assert - Should return some form of result (either found documents or placeholder response)
        assert isinstance(result, dict)
        # The result structure will depend on what the placeholder service returns

    async def test_get_financial_summary_current_month(self, mock_session, sample_user_id):
        """Test financial summary for current month"""
        # Arrange
        args = {"period": "current_month"}

        # Mock payments
        mock_payment = Mock()
        mock_payment.amount = 1200

        # Mock expenses
        mock_expense = Mock()
        mock_expense.total_amount = 300

        # Setup session execution results
        mock_payment_result = Mock()
        mock_payment_result.scalars.return_value.all.return_value = [mock_payment]

        mock_expense_result = Mock()
        mock_expense_result.scalars.return_value.all.return_value = [mock_expense]

        mock_session.execute.side_effect = [mock_payment_result, mock_expense_result]

        # Act
        result = await ToolHandlers.get_financial_summary(args, sample_user_id, mock_session)

        # Assert
        assert result["income"]["total"] == 1200
        assert result["expenses"]["total"] == 300
        assert result["net_income"] == 900
        assert result["profit_margin"] == 75.0

    async def test_get_financial_summary_custom_period(self, mock_session, sample_user_id):
        """Test financial summary for custom period"""
        # Arrange
        args = {
            "period": "custom",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        }

        # Mock empty results
        mock_empty_result = Mock()
        mock_empty_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_empty_result

        # Act
        result = await ToolHandlers.get_financial_summary(args, sample_user_id, mock_session)

        # Assert
        assert result["period"]["type"] == "custom"
        assert result["period"]["start_date"] == "2024-01-01"
        assert result["period"]["end_date"] == "2024-01-31"
        assert result["income"]["total"] == 0
        assert result["expenses"]["total"] == 0

    async def test_get_financial_summary_missing_dates(self, mock_session, sample_user_id):
        """Test financial summary with missing custom dates"""
        # Arrange
        args = {"period": "custom"}

        # Act
        result = await ToolHandlers.get_financial_summary(args, sample_user_id, mock_session)

        # Assert
        assert "error" in result
        assert "start_date and end_date are required" in result["error"]

    async def test_get_maintenance_requests_all(self, mock_session, sample_user_id):
        """Test getting all maintenance requests"""
        # Arrange
        args = {"status": "All"}

        # Mock maintenance request
        mock_request = Mock()
        mock_request.id = 1
        mock_request.issue_title = "Leaky faucet"
        mock_request.description = "Kitchen faucet is dripping"
        mock_request.status.value = "Pending"
        mock_request.priority.value = "Medium"
        mock_request.created_at = datetime.now(UTC)
        mock_request.scheduled_date = None
        mock_request.completed_date = None
        mock_request.estimated_cost = 150
        mock_request.actual_cost = None

        # Mock related objects
        mock_request.property = Mock()
        mock_request.property.name = "Test Property"
        mock_request.unit = Mock()
        mock_request.unit.name = "Unit 1A"
        mock_request.tenant = Mock()
        mock_request.tenant.first_name = "John"
        mock_request.tenant.last_name = "Doe"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_request]
        mock_session.execute.return_value = mock_result

        # Act
        result = await ToolHandlers.get_maintenance_requests(args, sample_user_id, mock_session)

        # Assert
        assert len(result["requests"]) == 1
        assert result["requests"][0]["title"] == "Leaky faucet"
        assert result["requests"][0]["status"] == "Pending"
        assert result["summary"]["total_requests"] == 1

    async def test_get_lease_expiry_info_upcoming(self, mock_session, sample_user_id):
        """Test getting upcoming lease expirations"""
        # Arrange
        args = {"days_ahead": 90}

        # Mock lease expiring soon
        mock_lease = Mock()
        mock_lease.id = 1
        mock_lease.start_date = date(2024, 1, 1)
        mock_lease.end_date = date(2024, 12, 31)
        mock_lease.monthly_rent = 1500

        # Mock related objects
        mock_lease.tenant = Mock()
        mock_lease.tenant.first_name = "Jane"
        mock_lease.tenant.last_name = "Smith"

        mock_lease.unit = Mock()
        mock_lease.unit.name = "Unit 2B"
        mock_lease.unit.property = Mock()
        mock_lease.unit.property.name = "Downtown Apartments"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_lease]
        mock_session.execute.return_value = mock_result

        # Act
        result = await ToolHandlers.get_lease_expiry_info(args, sample_user_id, mock_session)

        # Assert
        assert len(result["leases"]) == 1
        assert result["leases"][0]["tenant"] == "Jane Smith"
        assert result["leases"][0]["monthly_rent"] == 1500
        assert result["summary"]["total_monthly_rent_at_risk"] == 1500

    async def test_get_payment_status_overdue(self, mock_session, sample_user_id):
        """Test getting overdue payment status"""
        # Arrange
        args = {"status": "overdue"}

        # Mock overdue invoice
        mock_invoice = Mock()
        mock_invoice.id = 1
        mock_invoice.due_date = datetime(2024, 1, 1)  # Past due
        mock_invoice.amount = 1200
        mock_invoice.status.value = "Pending"

        mock_invoice.tenant = Mock()
        mock_invoice.tenant.first_name = "Bob"
        mock_invoice.tenant.last_name = "Wilson"

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_invoice]
        mock_session.execute.return_value = mock_result

        # Act
        result = await ToolHandlers.get_payment_status(args, sample_user_id, mock_session)

        # Assert
        assert len(result["payments"]) == 1
        assert result["payments"][0]["is_overdue"] is True
        assert result["payments"][0]["balance"] == 1200
        assert result["summary"]["total_overdue"] == 1200