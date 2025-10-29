"""
Ownership Entities API Module

Provides CRUD operations for ownership entities (companies, individuals, trusts, etc.)
that own or have stakes in property units.
"""
from .router import router

__all__ = ["router"]
