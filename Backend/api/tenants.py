from typing import List, Optional, Union
import logging
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, constr, EmailStr, validator

from Backend.database import get_session
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.user import User
from Backend.models.property import Property, PropertyUnit
from Backend.api.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
)

# === Models ===
class TenantCreate(BaseModel):
    full_name: constr(min_length=1, max_length=255)
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    current_property_id: Optional[int] = None
    unit_id: Optional[int] = None
    unit: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[float] = None
    status: Optional[str] = "Active"
    user_id: Optional[int] = None
    
    @validator('monthly_rent')
    def validate_rent(cls, v):
        if v is not None and v < 0:
            raise ValueError('Monthly rent cannot be negative')
        return v

class TenantUpdate(BaseModel):
    full_name: Optional[constr(min_length=1, max_length=255)] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    current_property_id: Optional[int] = None
    unit_id: Optional[int] = None
    unit: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[float] = None
    status: Optional[str] = None
    user_id: Optional[int] = None
    
    @validator('monthly_rent')
    def validate_rent(cls, v):
        if v is not None and v < 0:
            raise ValueError('Monthly rent cannot be negative')
        return v

class TenantResponse(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    current_property_id: Optional[int] = None
    property_name: Optional[str] = None  # Populated from relationship
    unit_id: Optional[int] = None
    unit: Optional[str] = None
    lease_start: Optional[date] = None
    lease_end: Optional[date] = None
    monthly_rent: Optional[float] = None
    status: str = "Active"
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# === API Routes ===
@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    property_id: Optional[int] = Query(None, description="Filter by property ID"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    status: Optional[str] = Query(None, description="Filter by tenant status"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all tenants with optional filtering.
    """
    try:
        query = select(Tenant).options(joinedload(Tenant.current_property))
        
        # Apply filters if provided
        if property_id:
            query = query.where(Tenant.current_property_id == property_id)
            
        if status:
            query = query.where(Tenant.status == status)
            
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Tenant.full_name.ilike(search_term),
                    Tenant.email.ilike(search_term)
                )
            )
        
        result = await session.execute(query)
        tenants = result.unique().scalars().all()
        
        # Prepare response with property names
        response_tenants = []
        for tenant in tenants:
            tenant_dict = {
                "id": tenant.id,
                "full_name": tenant.full_name,
                "phone": tenant.phone,
                "email": tenant.email,
                "current_property_id": tenant.current_property_id,
                "property_name": tenant.current_property.name if tenant.current_property else None,
                "unit_id": tenant.unit_id,
                "unit": tenant.unit,
                "lease_start": tenant.lease_start,
                "lease_end": tenant.lease_end,
                "monthly_rent": tenant.monthly_rent,
                "status": tenant.status,
                "user_id": tenant.user_id,
                "created_at": tenant.created_at,
                "updated_at": tenant.updated_at
            }
            response_tenants.append(tenant_dict)
        
        return response_tenants
    except Exception as e:
        logger.error(f"Error fetching tenants: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching tenants"
        )

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific tenant by ID.
    """
    try:
        query = select(Tenant).options(joinedload(Tenant.current_property)).where(Tenant.id == tenant_id)
        result = await session.execute(query)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Create response with property name
        response = {
            "id": tenant.id,
            "full_name": tenant.full_name,
            "phone": tenant.phone,
            "email": tenant.email,
            "current_property_id": tenant.current_property_id,
            "property_name": tenant.current_property.name if tenant.current_property else None,
            "unit_id": tenant.unit_id,
            "unit": tenant.unit,
            "lease_start": tenant.lease_start,
            "lease_end": tenant.lease_end,
            "monthly_rent": tenant.monthly_rent,
            "status": tenant.status,
            "user_id": tenant.user_id,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the tenant"
        )

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new tenant.
    """
    try:
        # Check if property exists if property_id is provided
        if tenant_data.current_property_id:
            property_query = select(Property).where(Property.id == tenant_data.current_property_id)
            property_result = await session.execute(property_query)
            property_obj = property_result.scalar_one_or_none()
            
            if not property_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Property not found"
                )
        
        # Check if unit exists if unit_id is provided
        if tenant_data.unit_id:
            unit_query = select(PropertyUnit).where(PropertyUnit.id == tenant_data.unit_id)
            unit_result = await session.execute(unit_query)
            unit_obj = unit_result.scalar_one_or_none()
            
            if not unit_obj:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Unit not found"
                )
        
        # Create new tenant instance
        new_tenant = Tenant(
            full_name=tenant_data.full_name,
            phone=tenant_data.phone,
            email=tenant_data.email,
            current_property_id=tenant_data.current_property_id,
            unit_id=tenant_data.unit_id,
            unit=tenant_data.unit,
            lease_start=tenant_data.lease_start,
            lease_end=tenant_data.lease_end,
            monthly_rent=tenant_data.monthly_rent,
            status=tenant_data.status,
            user_id=tenant_data.user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        session.add(new_tenant)
        await session.commit()
        await session.refresh(new_tenant)
        
        # Get property name if property exists
        property_name = None
        if new_tenant.current_property_id:
            property_query = select(Property).where(Property.id == new_tenant.current_property_id)
            property_result = await session.execute(property_query)
            property_obj = property_result.scalar_one_or_none()
            if property_obj:
                property_name = property_obj.name
        
        # Prepare response
        response = {
            "id": new_tenant.id,
            "full_name": new_tenant.full_name,
            "phone": new_tenant.phone,
            "email": new_tenant.email,
            "current_property_id": new_tenant.current_property_id,
            "property_name": property_name,
            "unit_id": new_tenant.unit_id,
            "unit": new_tenant.unit,
            "lease_start": new_tenant.lease_start,
            "lease_end": new_tenant.lease_end,
            "monthly_rent": new_tenant.monthly_rent,
            "status": new_tenant.status,
            "user_id": new_tenant.user_id,
            "created_at": new_tenant.created_at,
            "updated_at": new_tenant.updated_at
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the tenant: {str(e)}"
        )

@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update an existing tenant.
    """
    try:
        # Get the tenant
        query = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(query)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Check if property exists if property_id is being updated
        if tenant_data.current_property_id is not None and tenant_data.current_property_id != tenant.current_property_id:
            property_query = select(Property).where(Property.id == tenant_data.current_property_id)
            property_result = await session.execute(property_query)
            property_obj = property_result.scalar_one_or_none()
            
            if not property_obj and tenant_data.current_property_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Property not found"
                )
        
        # Check if unit exists if unit_id is being updated
        if tenant_data.unit_id is not None and tenant_data.unit_id != tenant.unit_id:
            unit_query = select(PropertyUnit).where(PropertyUnit.id == tenant_data.unit_id)
            unit_result = await session.execute(unit_query)
            unit_obj = unit_result.scalar_one_or_none()
            
            if not unit_obj and tenant_data.unit_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Unit not found"
                )
        
        # Update tenant fields
        if tenant_data.full_name is not None:
            tenant.full_name = tenant_data.full_name
        if tenant_data.phone is not None:
            tenant.phone = tenant_data.phone
        if tenant_data.email is not None:
            tenant.email = tenant_data.email
        if tenant_data.current_property_id is not None:
            tenant.current_property_id = tenant_data.current_property_id
        if tenant_data.unit_id is not None:
            tenant.unit_id = tenant_data.unit_id
        if tenant_data.unit is not None:
            tenant.unit = tenant_data.unit
        if tenant_data.lease_start is not None:
            tenant.lease_start = tenant_data.lease_start
        if tenant_data.lease_end is not None:
            tenant.lease_end = tenant_data.lease_end
        if tenant_data.monthly_rent is not None:
            tenant.monthly_rent = tenant_data.monthly_rent
        if tenant_data.status is not None:
            tenant.status = tenant_data.status
        if tenant_data.user_id is not None:
            tenant.user_id = tenant_data.user_id
            
        tenant.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(tenant)
        
        # Get property name if property exists
        property_name = None
        if tenant.current_property_id:
            property_query = select(Property).where(Property.id == tenant.current_property_id)
            property_result = await session.execute(property_query)
            property_obj = property_result.scalar_one_or_none()
            if property_obj:
                property_name = property_obj.name
        
        # Prepare response
        response = {
            "id": tenant.id,
            "full_name": tenant.full_name,
            "phone": tenant.phone,
            "email": tenant.email,
            "current_property_id": tenant.current_property_id,
            "property_name": property_name,
            "unit_id": tenant.unit_id,
            "unit": tenant.unit,
            "lease_start": tenant.lease_start,
            "lease_end": tenant.lease_end,
            "monthly_rent": tenant.monthly_rent,
            "status": tenant.status,
            "user_id": tenant.user_id,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the tenant"
        )

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a tenant.
    """
    try:
        query = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(query)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        await session.delete(tenant)
        await session.commit()
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tenant: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the tenant"
        ) 