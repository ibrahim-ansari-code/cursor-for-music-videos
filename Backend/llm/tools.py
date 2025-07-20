"""
Tool definitions for the Brikli Assistant

This module defines the tools available to the Azure AI Assistant
for querying and analyzing property management data.
"""
from typing import Any


def get_tool_definitions() -> list[dict[str, Any]]:
    """
    Return tool definitions for the Azure AI Assistant
    
    These tools enable the assistant to:
    - Search and filter properties
    - Get tenant information
    - Search through documents using semantic search
    - Provide financial summaries
    - Check maintenance requests
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_properties",
                "description": "Search and filter properties by various criteria such as status, location, rent range, and property type",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["Active", "Inactive", "All"],
                            "description": "Property status filter. Use 'All' to see all properties regardless of status"
                        },
                        "city": {
                            "type": "string",
                            "description": "City to filter by (partial match supported)"
                        },
                        "min_rent": {
                            "type": "number",
                            "description": "Minimum monthly rent amount"
                        },
                        "max_rent": {
                            "type": "number",
                            "description": "Maximum monthly rent amount"
                        },
                        "property_type": {
                            "type": "string",
                            "enum": ["Residential", "Commercial", "Mixed", "All"],
                            "description": "Type of property. Use 'All' to see all property types"
                        },
                        "has_vacancies": {
                            "type": "boolean",
                            "description": "Filter to show only properties with vacant units"
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_tenant_info",
                "description": "Get detailed information about tenants, including their lease details and payment history",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tenant_name": {
                            "type": "string",
                            "description": "Full or partial name of the tenant to search for"
                        },
                        "property_id": {
                            "type": "string",
                            "description": "UUID of the property to filter tenants by"
                        },
                        "unit_id": {
                            "type": "string",
                            "description": "UUID of the unit to filter tenants by"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["Active", "Inactive", "All"],
                            "description": "Tenant status filter"
                        },
                        "include_payment_history": {
                            "type": "boolean",
                            "description": "Whether to include recent payment history (last 6 payments)",
                            "default": False
                        },
                        "include_lease_details": {
                            "type": "boolean",
                            "description": "Whether to include current lease details",
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_lease_documents",
                "description": "Search through lease agreements and other documents using semantic search to find specific information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "What to search for in the documents (e.g., 'pet policy', 'late payment fees', 'maintenance responsibilities')"
                        },
                        "document_type": {
                            "type": "string",
                            "enum": ["lease", "invoice", "expense", "all"],
                            "description": "Type of documents to search through",
                            "default": "all"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of relevant results to return",
                            "minimum": 1,
                            "maximum": 10,
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_summary",
                "description": "Get comprehensive financial summaries including income, expenses, and outstanding payments",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period": {
                            "type": "string",
                            "enum": ["current_month", "last_month", "current_quarter", "last_quarter", "current_year", "last_year", "custom"],
                            "description": "Time period for the financial summary"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date for custom period (YYYY-MM-DD format). Required if period is 'custom'"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for custom period (YYYY-MM-DD format). Required if period is 'custom'"
                        },
                        "property_id": {
                            "type": "string",
                            "description": "UUID of specific property to filter by (optional)"
                        },
                        "include_details": {
                            "type": "boolean",
                            "description": "Whether to include detailed breakdowns by category",
                            "default": False
                        },
                        "group_by": {
                            "type": "string",
                            "enum": ["property", "category", "month", "none"],
                            "description": "How to group the financial data",
                            "default": "none"
                        }
                    },
                    "required": ["period"],
                    "dependencies": {
                        "period": {
                            "properties": {
                                "period": {"enum": ["custom"]}
                            },
                            "required": ["start_date", "end_date"]
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_maintenance_requests",
                "description": "Get maintenance requests and their current status, filtered by various criteria",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["Pending", "In Progress", "Scheduled", "Completed", "Cancelled", "All"],
                            "description": "Filter by request status",
                            "default": "All"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["Low", "Medium", "High", "All"],
                            "description": "Filter by priority level",
                            "default": "All"
                        },
                        "property_id": {
                            "type": "string",
                            "description": "UUID of property to filter by"
                        },
                        "unit_id": {
                            "type": "string",
                            "description": "UUID of unit to filter by"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Show requests from the last N days (e.g., 7 for last week)",
                            "minimum": 1,
                            "maximum": 365
                        },
                        "include_completed": {
                            "type": "boolean",
                            "description": "Whether to include completed requests",
                            "default": True
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_lease_expiry_info",
                "description": "Get information about upcoming lease expirations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days_ahead": {
                            "type": "integer",
                            "description": "Number of days to look ahead for expiring leases",
                            "minimum": 1,
                            "maximum": 365,
                            "default": 90
                        },
                        "property_id": {
                            "type": "string",
                            "description": "UUID of property to filter by (optional)"
                        },
                        "include_expired": {
                            "type": "boolean",
                            "description": "Whether to include recently expired leases",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_payment_status",
                "description": "Get current payment status and outstanding balances",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["overdue", "pending", "paid", "all"],
                            "description": "Filter by payment status",
                            "default": "all"
                        },
                        "property_id": {
                            "type": "string",
                            "description": "UUID of property to filter by (optional)"
                        },
                        "tenant_id": {
                            "type": "string",
                            "description": "UUID of tenant to filter by (optional)"
                        },
                        "include_history": {
                            "type": "boolean",
                            "description": "Include payment history for context",
                            "default": False
                        }
                    },
                    "required": []
                }
            }
        }
    ]