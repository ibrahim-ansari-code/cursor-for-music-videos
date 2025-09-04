"""
Tax Preferences API Router

Provides REST endpoints for tax preference management:
- Smart tax selection
- User default tax preferences  
- Property-specific tax preferences
- Historical usage analysis
"""

import logging
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth.dependencies import get_current_landlord_or_admin
from Backend.database import get_session
from Backend.models.user import User
from .service import TaxPreferenceService
from .schemas import (
    TaxPreferenceCreate,
    TaxPreferenceResponse,     SmartTaxResponse,
    HistoricalTaxUsage
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/smart", response_model=SmartTaxResponse)
async def get_smart_tax_recommendation(
    property_id: Optional[int] = Query(None, description="Property ID for context-aware tax selection"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """
    Get smart tax recommendation based on user context and preferences.
    
    Uses intelligent priority hierarchy:
    1. Property-specific default (if property has custom tax)
    2. Provincial default (based on property location) 
    3. User default (personal preference)
    4. Historical usage (most frequently used tax)
    5. No recommendation (new user with no history)
    """
    
    try:
        service = TaxPreferenceService(session)
        smart_tax = await service.get_smart_tax_for_context(
            user_id=str(current_user.id),
            property_id=property_id
        )
        return smart_tax
        
    except Exception as e:
        logger.error(f"Error getting smart tax recommendation for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tax recommendation"
        )


@router.get("/default", response_model=Optional[TaxPreferenceResponse])
async def get_user_tax_default(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """Get the user's default tax preference."""
    
    try:
        service = TaxPreferenceService(session)
        user_default = await service.get_user_tax_default(str(current_user.id))
        return user_default
        
    except Exception as e:
        logger.error(f"Error getting user tax default for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user tax default"
        )


@router.post("/default", response_model=TaxPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def set_user_tax_default(
    tax_data: TaxPreferenceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """Set or update the user's default tax preference."""
    
    try:
        service = TaxPreferenceService(session)
        result = await service.set_user_tax_default(
            user_id=str(current_user.id),
            tax_data=tax_data
        )
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting user tax default for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set user tax default"
        )


@router.get("/property/{property_id}", response_model=Optional[TaxPreferenceResponse])
async def get_property_tax_default(
    property_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """Get a property's default tax preference."""
    
    try:
        service = TaxPreferenceService(session)
        property_default = await service.get_property_tax_default(
            user_id=str(current_user.id),
            property_id=property_id
        )
        return property_default
        
    except Exception as e:
        logger.error(f"Error getting property tax default for property {property_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get property tax default"
        )


@router.post("/property/{property_id}", response_model=TaxPreferenceResponse, status_code=status.HTTP_201_CREATED)
async def set_property_tax_default(
    property_id: int,
    tax_data: TaxPreferenceCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """Set or update a property's default tax preference."""
    
    try:
        service = TaxPreferenceService(session)
        result = await service.set_property_tax_default(
            user_id=str(current_user.id),
            property_id=property_id,
            tax_data=tax_data
        )
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error setting property tax default for property {property_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set property tax default"
        )


@router.get("/history", response_model=List[HistoricalTaxUsage])
async def get_historical_tax_usage(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of historical tax records to return"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """
    Get historical tax usage analysis for the user.
    
    Returns the most frequently used tax types with usage statistics.
    """
    
    try:
        service = TaxPreferenceService(session)
        history = await service.get_historical_tax_usage(
            user_id=str(current_user.id),
            limit=limit
        )
        return history
        
    except Exception as e:
        logger.error(f"Error getting historical tax usage for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get historical tax usage"
        )


@router.delete("/default", status_code=status.HTTP_204_NO_CONTENT)
async def clear_user_tax_default(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """Clear the user's default tax preference."""
    
    try:
        service = TaxPreferenceService(session)
        # Clear user's tax defaults by setting them to None
        await service.clear_user_tax_default(user_id=str(current_user.id))
        
    except Exception as e:
        logger.error(f"Error clearing user tax default for user {current_user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear user tax default"
        )


@router.delete("/property/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_property_tax_default(
    property_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_landlord_or_admin)
):
    """Clear a property's default tax preference."""
    
    try:
        service = TaxPreferenceService(session)
        # Clear property's tax defaults by setting them to None
        await service.clear_property_tax_default(
            user_id=str(current_user.id),
            property_id=property_id
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error clearing property tax default for property {property_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear property tax default"
        )