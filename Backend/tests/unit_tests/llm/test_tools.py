"""
Unit tests for tool definitions.
"""
import pytest
from Backend.llm.tools import get_tool_definitions


class TestTools:
    """Test cases for tool definitions."""

    def test_get_tool_definitions_returns_list(self):
        """Test that get_tool_definitions returns a list."""
        tools = get_tool_definitions()
        assert isinstance(tools, list)

    def test_get_tool_definitions_not_empty(self):
        """Test that get_tool_definitions returns tools."""
        tools = get_tool_definitions()
        assert len(tools) > 0

    def test_tool_definition_structure(self):
        """Test that each tool has the required structure."""
        tools = get_tool_definitions()
        
        for tool in tools:
            # Each tool should have 'type' and 'function'
            assert 'type' in tool
            assert tool['type'] == 'function'
            assert 'function' in tool
            
            # Function should have required fields
            func = tool['function']
            assert 'name' in func
            assert 'description' in func
            assert 'parameters' in func
            
            # Parameters should have required schema fields
            params = func['parameters']
            assert 'type' in params
            assert params['type'] == 'object'
            assert 'properties' in params
            assert 'required' in params

    def test_known_tools_exist(self):
        """Test that expected tools are present."""
        tools = get_tool_definitions()
        tool_names = [tool['function']['name'] for tool in tools]
        
        expected_tools = [
            'search_properties',
            'get_tenant_info',
            'get_financial_summary',
            'get_maintenance_requests',
            'get_lease_expiry_info',
            'get_payment_status',
            'search_lease_documents'
        ]
        
        for expected in expected_tools:
            assert expected in tool_names, f"Tool '{expected}' not found in tool definitions"