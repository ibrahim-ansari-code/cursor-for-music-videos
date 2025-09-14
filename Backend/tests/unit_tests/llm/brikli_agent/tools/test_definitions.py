"""
Unit tests for tool definitions
"""
import pytest

from Backend.llm.brikli_agent.tools.definitions import get_tool_definitions


class TestToolDefinitions:
    """Test cases for tool definitions"""

    def test_get_tool_definitions_returns_list(self):
        """Test that get_tool_definitions returns a list"""
        # Act
        tools = get_tool_definitions()

        # Assert
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_all_tools_have_required_structure(self):
        """Test that all tools have the required OpenAPI structure"""
        # Act
        tools = get_tool_definitions()

        # Assert
        for tool in tools:
            # Each tool must have type and function
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool

            # Function must have name, description, and parameters
            function = tool["function"]
            assert "name" in function
            assert "description" in function
            assert "parameters" in function

            # Parameters must have type and properties
            parameters = function["parameters"]
            assert "type" in parameters
            assert parameters["type"] == "object"
            assert "properties" in parameters

    def test_search_properties_tool_definition(self):
        """Test search_properties tool definition"""
        # Act
        tools = get_tool_definitions()
        search_properties = next(
            (tool for tool in tools
             if tool["function"]["name"] == "search_properties"), None
        )
        assert search_properties is not None, "search_properties tool not found"

        # Assert
        function = search_properties["function"]
        assert function["name"] == "search_properties"
        assert "Search and filter properties" in function["description"]

        # Check required parameters
        properties = function["parameters"]["properties"]
        expected_properties = ["status", "city", "min_rent", "max_rent", "property_type", "has_vacancies"]
        for prop in expected_properties:
            assert prop in properties

        # Check enum values for status
        assert properties["status"]["enum"] == ["Active", "Inactive", "All"]

    def test_get_tenant_info_tool_definition(self):
        """Test get_tenant_info tool definition"""
        # Act
        tools = get_tool_definitions()
        get_tenant_info = next(
            (tool for tool in tools
             if tool["function"]["name"] == "get_tenant_info"), None
        )
        assert get_tenant_info is not None, "get_tenant_info tool not found"

        # Assert
        function = get_tenant_info["function"]
        assert function["name"] == "get_tenant_info"
        assert "information about tenants" in function["description"]

        # Check parameters
        properties = function["parameters"]["properties"]
        expected_properties = ["tenant_name", "property_id", "unit_id", "status",
                              "include_payment_history", "include_lease_details"]
        for prop in expected_properties:
            assert prop in properties

    def test_search_lease_documents_tool_definition(self):
        """Test search_lease_documents tool definition"""
        # Act
        tools = get_tool_definitions()
        search_docs = next(
            (tool for tool in tools
             if tool["function"]["name"] == "search_lease_documents"), None
        )
        assert search_docs is not None, "search_lease_documents tool not found"

        # Assert
        function = search_docs["function"]
        assert function["name"] == "search_lease_documents"
        assert "semantic search" in function["description"]

        # Check required parameters
        parameters = function["parameters"]
        assert "query" in parameters["required"]

        # Check query parameter
        properties = parameters["properties"]
        assert "query" in properties
        assert properties["query"]["type"] == "string"

    def test_get_financial_summary_tool_definition(self):
        """Test get_financial_summary tool definition"""
        # Act
        tools = get_tool_definitions()
        financial_summary = next(
            (tool for tool in tools
             if tool["function"]["name"] == "get_financial_summary"), None
        )
        assert financial_summary is not None, "get_financial_summary tool not found"

        # Assert
        function = financial_summary["function"]
        assert function["name"] == "get_financial_summary"
        assert "financial summaries" in function["description"]

        # Check required parameters
        parameters = function["parameters"]
        assert "period" in parameters["required"]

        # Check period enum values
        properties = parameters["properties"]
        expected_periods = ["current_month", "last_month", "current_quarter",
                           "last_quarter", "current_year", "last_year", "custom"]
        assert properties["period"]["enum"] == expected_periods

        # Check dependencies for custom period
        assert "dependencies" in parameters
        assert "period" in parameters["dependencies"]

    def test_get_maintenance_requests_tool_definition(self):
        """Test get_maintenance_requests tool definition"""
        # Act
        tools = get_tool_definitions()
        maintenance = next(
            (tool for tool in tools
             if tool["function"]["name"] == "get_maintenance_requests"), None
        )
        assert maintenance is not None, "get_maintenance_requests tool not found"

        # Assert
        function = maintenance["function"]
        assert function["name"] == "get_maintenance_requests"
        assert "maintenance requests" in function["description"]

        # Check status enum
        properties = function["parameters"]["properties"]
        expected_statuses = ["Pending", "In Progress", "Scheduled",
                           "Completed", "Cancelled", "All"]
        assert properties["status"]["enum"] == expected_statuses

    def test_get_lease_expiry_info_tool_definition(self):
        """Test get_lease_expiry_info tool definition"""
        # Act
        tools = get_tool_definitions()
        lease_expiry = next(
            (tool for tool in tools
             if tool["function"]["name"] == "get_lease_expiry_info"), None
        )
        assert lease_expiry is not None, "get_lease_expiry_info tool not found"

        # Assert
        function = lease_expiry["function"]
        assert function["name"] == "get_lease_expiry_info"
        assert "lease expirations" in function["description"]

        # Check days_ahead parameter
        properties = function["parameters"]["properties"]
        days_ahead = properties["days_ahead"]
        assert days_ahead["type"] == "integer"
        assert days_ahead["minimum"] == 1
        assert days_ahead["maximum"] == 365
        assert days_ahead["default"] == 90

    def test_get_payment_status_tool_definition(self):
        """Test get_payment_status tool definition"""
        # Act
        tools = get_tool_definitions()
        payment_status = next(
            (tool for tool in tools
             if tool["function"]["name"] == "get_payment_status"), None
        )
        assert payment_status is not None, "get_payment_status tool not found"

        # Assert
        function = payment_status["function"]
        assert function["name"] == "get_payment_status"
        assert "payment status" in function["description"]

        # Check status enum
        properties = function["parameters"]["properties"]
        expected_statuses = ["overdue", "pending", "paid", "all"]
        assert properties["status"]["enum"] == expected_statuses

    def test_all_expected_tools_present(self):
        """Test that all expected tools are present"""
        # Act
        tools = get_tool_definitions()
        tool_names = [tool["function"]["name"] for tool in tools]

        # Assert
        expected_tools = [
            "search_properties",
            "get_tenant_info",
            "search_lease_documents",
            "get_financial_summary",
            "get_maintenance_requests",
            "get_lease_expiry_info",
            "get_payment_status"
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names

        # Check we have exactly the expected number of tools
        assert len(tool_names) == len(expected_tools)

    def test_tool_descriptions_are_informative(self):
        """Test that tool descriptions provide sufficient information"""
        # Act
        tools = get_tool_definitions()

        # Assert
        for tool in tools:
            description = tool["function"]["description"]

            # Description should be informative (more than just the function name)
            assert len(description) > 20

            # Should not just be the function name reformatted
            function_name = tool["function"]["name"]
            assert description.lower() != function_name.replace("_", " ").lower()

    def test_parameter_types_are_valid(self):
        """Test that all parameter types are valid JSON Schema types"""
        # Act
        tools = get_tool_definitions()
        valid_types = ["string", "number", "integer", "boolean", "array", "object"]

        # Assert
        for tool in tools:
            properties = tool["function"]["parameters"]["properties"]
            for prop_name, prop_def in properties.items():
                assert "type" in prop_def
                assert prop_def["type"] in valid_types

    def test_enum_values_are_consistent(self):
        """Test that enum values follow consistent patterns"""
        # Act
        tools = get_tool_definitions()

        # Assert
        for tool in tools:
            properties = tool["function"]["parameters"]["properties"]
            for prop_name, prop_def in properties.items():
                if "enum" in prop_def:
                    enum_values = prop_def["enum"]

                    # Enums should not be empty
                    assert len(enum_values) > 0

                    # If there's an "All" option, it should typically be last or first
                    if "All" in enum_values:
                        assert enum_values.index("All") in [0, len(enum_values) - 1]

    def test_required_parameters_exist(self):
        """Test that required parameters actually exist in properties"""
        # Act
        tools = get_tool_definitions()

        # Assert
        for tool in tools:
            parameters = tool["function"]["parameters"]
            if "required" in parameters:
                required = parameters["required"]
                properties = parameters["properties"]

                for required_param in required:
                    assert required_param in properties