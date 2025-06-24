"""
Expenses API module.

This module provides endpoints for managing property-related expenses,
including receipt parsing, CRUD operations, and tax calculations.
"""

from .router import router

__all__ = ["router"]
