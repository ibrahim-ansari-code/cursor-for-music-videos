"""
Tax Preferences Service Layer

Implements the core business logic for tax preference management including:
- Smart tax selection with priority hierarchy
- User and property default management  
- Historical usage analysis with caching
- Provincial tax rate integration
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from functools import lru_cache

from sqlalchemy import func, desc, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select, col

from Backend.models.user import User
from Backend.models.property import Property
from Backend.models.accounting.expense import Expense, ExpenseTaxDetail
from Backend.utils.tax_rates import get_provincial_tax_rate, get_default_tax_rate
from .schemas import (
    TaxPreferenceResponse, SmartTaxResponse, HistoricalTaxUsage,
    TaxPreferenceCreate
)

logger = logging.getLogger(__name__)


class TaxPreferenceService:
    """Core service for tax preference management with optimized caching."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._historical_cache: Dict[str, Tuple[List[HistoricalTaxUsage], datetime]] = {}

    async def get_smart_tax_for_context(
        self, 
        user_id: str, 
        property_id: Optional[int] = None
    ) -> SmartTaxResponse:
        """
        Get smart tax recommendation based on context and priority hierarchy:
        1. Property-specific default (if property selected and has custom tax)
        2. Provincial default (if property selected, use province tax rate)
        3. User default (if no property or property has no default)
        4. Historical usage (analyze expense_tax_details history)
        5. Empty (new user, no history)
        """
        
        # Priority 1/2: Only skip when property_id is None
        if property_id is not None:
            property_tax = await self._get_property_tax_default(property_id, user_id)
            if property_tax:
                return SmartTaxResponse(
                    tax_name=property_tax.tax_name,
                    tax_rate=property_tax.tax_rate,
                    source="property_default",
                    confidence=0.95,
                    reasoning=f"Using property-specific tax preference: {property_tax.tax_name} {property_tax.tax_rate}%"
                )
            
            # Priority 2: Provincial default based on property location
            provincial_tax = await self._get_provincial_tax_for_property(property_id, user_id)
            if provincial_tax:
                return SmartTaxResponse(
                    tax_name=provincial_tax.tax_name,
                    tax_rate=provincial_tax.tax_rate,
                    source="provincial_default",
                    confidence=0.85,
                    reasoning=f"Using provincial tax rate for property location: {provincial_tax.tax_name} {provincial_tax.tax_rate}%"
                )
        
        # Priority 3: User default
        user_tax = await self._get_user_tax_default(user_id)
        if user_tax:
            return SmartTaxResponse(
                tax_name=user_tax.tax_name,
                tax_rate=user_tax.tax_rate,
                source="user_default",
                confidence=0.75,
                reasoning=f"Using your personal tax default: {user_tax.tax_name} {user_tax.tax_rate}%"
            )
        
        # Priority 4: Historical usage analysis
        historical_tax = await self._get_most_used_tax(user_id)
        if historical_tax:
            return SmartTaxResponse(
                tax_name=historical_tax.tax_name,
                tax_rate=historical_tax.tax_rate,
                source="historical_usage",
                confidence=0.60,
                reasoning=f"Based on your usage history: {historical_tax.tax_name} {historical_tax.tax_rate}% (used {historical_tax.usage_count} times)"
            )
        
        # Priority 5: No recommendation available
        return SmartTaxResponse(
            tax_name=None,
            tax_rate=None,
            source="none",
            confidence=0.0,
            reasoning="No tax preferences or usage history found. Please select tax manually."
        )

    async def set_user_tax_default(
        self, 
        user_id: str, 
        tax_data: TaxPreferenceCreate
    ) -> TaxPreferenceResponse:
        """Set or update user's default tax preference."""
        
        # Get user record
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        # Update user's tax defaults
        user.default_tax_name = tax_data.tax_name
        user.default_tax_rate = tax_data.tax_rate
        
        await self.session.commit()
        
        return TaxPreferenceResponse(
            tax_name=tax_data.tax_name,
            tax_rate=tax_data.tax_rate,
            source="user_default"
        )

    async def set_property_tax_default(
        self, 
        user_id: str,
        property_id: int, 
        tax_data: TaxPreferenceCreate
    ) -> TaxPreferenceResponse:
        """Set or update property's default tax preference."""
        
        # Verify property ownership and get property
        property = await self._get_user_property(user_id, property_id)
        if not property:
            raise ValueError("Property not found or access denied")
        
        # Update property's tax defaults
        property.default_tax_name = tax_data.tax_name
        property.default_tax_rate = tax_data.tax_rate
        
        await self.session.commit()
        
        return TaxPreferenceResponse(
            tax_name=tax_data.tax_name,
            tax_rate=tax_data.tax_rate,
            source="property_default"
        )

    async def get_user_tax_default(self, user_id: str) -> Optional[TaxPreferenceResponse]:
        """Get user's default tax preference."""
        user_tax = await self._get_user_tax_default(user_id)
        return user_tax

    async def clear_user_tax_default(self, user_id: str) -> None:
        """Clear the user's default tax preference by setting to None."""
        
        # Get user record
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        # Clear user's tax defaults
        user.default_tax_name = None
        user.default_tax_rate = None
        
        await self.session.commit()

    async def clear_property_tax_default(self, user_id: str, property_id: int) -> None:
        """Clear a property's default tax preference by setting to None."""
        
        # Verify property ownership and get property
        property = await self._get_user_property(user_id, property_id)
        if not property:
            raise ValueError("Property not found or access denied")
        
        # Clear property's tax defaults
        property.default_tax_name = None
        property.default_tax_rate = None
        
        await self.session.commit()

    async def get_property_tax_default(
        self, 
        user_id: str, 
        property_id: int
    ) -> Optional[TaxPreferenceResponse]:
        """Get property's default tax preference."""
        property_tax = await self._get_property_tax_default(property_id, user_id)
        return property_tax

    async def get_historical_tax_usage(self, user_id: str, limit: int = 10) -> List[HistoricalTaxUsage]:
        """
        Get historical tax usage analysis for the user with caching.
        
        Uses a 5-minute cache to improve performance for frequently accessed data.
        """
        # Check cache first
        cache_key = f"{user_id}:{limit}"
        cache_expiry = timedelta(minutes=5)
        
        if cache_key in self._historical_cache:
            cached_data, timestamp = self._historical_cache[cache_key]
            if datetime.now() - timestamp < cache_expiry:
                logger.debug(f"Returning cached historical tax usage for user {user_id}")
                return cached_data
        
        # Cache miss or expired, fetch from database
        logger.debug(f"Fetching historical tax usage from database for user {user_id}")
        
        # Optimized query with explicit indexes hint for better performance
        stmt = (
            select(
                col(ExpenseTaxDetail.tax_name),
                col(ExpenseTaxDetail.tax_rate),
                func.count(col(ExpenseTaxDetail.id)).label('usage_count'),
                func.max(col(ExpenseTaxDetail.created_at)).label('last_used')
            )
            .select_from(ExpenseTaxDetail)
            .join(Expense, col(ExpenseTaxDetail.expense_id) == col(Expense.id))
            .join(Property, col(Expense.property_id) == col(Property.id))
            .where(col(Property.user_id) == user_id)
            .group_by(col(ExpenseTaxDetail.tax_name), col(ExpenseTaxDetail.tax_rate))
            .order_by(desc('usage_count'), desc('last_used'))
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.all()
        
        if not rows:
            # Cache empty result too
            self._historical_cache[cache_key] = ([], datetime.now())
            return []
        
        total_usage = sum(row.usage_count for row in rows)
        
        historical_data = [
            HistoricalTaxUsage(
                tax_name=row.tax_name,
                tax_rate=row.tax_rate,
                usage_count=row.usage_count,
                last_used=row.last_used.isoformat() if row.last_used else None,
                percentage=round((row.usage_count / total_usage) * 100, 1)
            )
            for row in rows
        ]
        
        # Cache the result
        self._historical_cache[cache_key] = (historical_data, datetime.now())
        
        # Clean up old cache entries to prevent memory leaks (keep last 100 entries)
        if len(self._historical_cache) > 100:
            oldest_keys = sorted(self._historical_cache.keys(), 
                               key=lambda k: self._historical_cache[k][1])[:50]
            for old_key in oldest_keys:
                del self._historical_cache[old_key]
        
        return historical_data

    # Private helper methods

    async def _get_property_tax_default(
        self, 
        property_id: int, 
        user_id: str
    ) -> Optional[TaxPreferenceResponse]:
        """Get property's tax default with ownership validation."""
        
        property = await self._get_user_property(user_id, property_id)
        if not property or not property.default_tax_name or not property.default_tax_rate:
            return None
        
        return TaxPreferenceResponse(
            tax_name=property.default_tax_name,
            tax_rate=property.default_tax_rate,
            source="property_default"
        )

    async def _get_provincial_tax_for_property(
        self, 
        property_id: int, 
        user_id: str
    ) -> Optional[TaxPreferenceResponse]:
        """Get provincial tax rate based on property location."""
        
        property = await self._get_user_property(user_id, property_id)
        if not property or not property.province:
            return None
        
        # Get provincial tax rate from utility
        provincial_tax = get_provincial_tax_rate(property.province)
        if not provincial_tax:
            return None
        
        tax_name, tax_rate = provincial_tax
        return TaxPreferenceResponse(
            tax_name=tax_name,
            tax_rate=tax_rate,
            source="provincial_default"
        )

    async def _get_user_tax_default(self, user_id: str) -> Optional[TaxPreferenceResponse]:
        """Get user's tax default."""
        
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not user.default_tax_name or not user.default_tax_rate:
            return None
        
        return TaxPreferenceResponse(
            tax_name=user.default_tax_name,
            tax_rate=user.default_tax_rate,
            source="user_default"
        )

    async def _get_most_used_tax(self, user_id: str) -> Optional[HistoricalTaxUsage]:
        """Get the most frequently used tax by the user."""
        
        usage_data = await self.get_historical_tax_usage(user_id, limit=1)
        return usage_data[0] if usage_data else None

    async def _get_user_property(self, user_id: str, property_id: int) -> Optional[Property]:
        """Get property with ownership validation."""
        
        stmt = (
            select(Property)
            .where(and_(col(Property.id) == property_id, col(Property.user_id) == user_id))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


# Convenience functions for integration with existing services

async def get_smart_tax_for_expense(
    session: AsyncSession,
    user_id: str,
    property_id: int
) -> Optional[Tuple[str, Decimal]]:
    """
    Get smart tax recommendation for expense creation.
    Returns (tax_name, tax_rate) tuple or None.
    """
    service = TaxPreferenceService(session)
    smart_tax = await service.get_smart_tax_for_context(user_id, property_id)
    
    if smart_tax.tax_name and smart_tax.tax_rate is not None:
        return (smart_tax.tax_name, smart_tax.tax_rate)
    
    return None


async def get_smart_tax_for_invoice(
    session: AsyncSession,
    user_id: str,
    property_id: Optional[int] = None
) -> Optional[Tuple[str, Decimal]]:
    """
    Get smart tax recommendation for invoice creation.
    Returns (tax_name, tax_rate) tuple or None.
    """
    service = TaxPreferenceService(session)
    smart_tax = await service.get_smart_tax_for_context(user_id, property_id)
    
    if smart_tax.tax_name and smart_tax.tax_rate is not None:
        return (smart_tax.tax_name, smart_tax.tax_rate)
    
    return None