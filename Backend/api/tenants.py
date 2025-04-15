from typing import List, Optional, Union
import logging
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, constr, EmailStr, validator
from sqlmodel import col

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
class TenantBase(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    status: TenantStatus = TenantStatus.ACTIVE
    user_id: Optional[int] = None
    current_property_id: Optional[int] = None

class TenantCreate(TenantBase):
    # Allow receiving full_name from frontend for backward compatibility
    full_name: Optional[str] = None
    
    @validator('first_name', 'last_name', pre=True, always=True)
    def split_full_name(cls, v, values):
        # If first_name is being validated and full_name is provided but first_name isn't
        if v is None and 'full_name' in values and values['full_name']:
            names = values['full_name'].split(' ', 1)
            if v is None and 'first_name' in values.keys():
                return names[0]
            if v is None and 'last_name' in values.keys() and len(names) > 1:
                return names[1]
        return v

class TenantUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[TenantStatus] = None
    current_property_id: Optional[int] = None
    
    # Allow receiving full_name from frontend
    full_name: Optional[str] = None
    
    @validator('first_name', 'last_name', pre=True)
    def split_full_name(cls, v, values):
        # If full_name is provided, split it into first_name and last_name
        if v is None and 'full_name' in values and values['full_name']:
            names = values['full_name'].split(' ', 1)
            if 'first_name' in values.keys() and values.get('first_name') is None:
                return names[0]
            if 'last_name' in values.keys() and values.get('last_name') is None and len(names) > 1:
                return names[1]
        return v

class TenantResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: Optional[str] = None
    email: Optional[str] = None 
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

# === API Routes ===
@router.get("/", response_model=List[dict])
async def get_tenants(
    status: Optional[TenantStatus] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get all tenants with optional filtering.
    """
    logger.info(f"User {current_user.email} is retrieving tenants")
    
    query = select(Tenant)
    
    # Apply filters if provided
    if status:
        query = query.where(Tenant.status == status)
    
    if search:
        search_term = f"%{search}%"
        # Search in both first and last name
        query = query.where(
            or_(
                col(Tenant.first_name).ilike(search_term),
                col(Tenant.last_name).ilike(search_term)
            )
        )
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    tenants = result.scalars().all()
    logger.info(f"Retrieved {len(tenants)} tenants")
    
    # Convert each tenant to a TenantResponse and include the full_name
    response_data = []
    for tenant in tenants:
        tenant_response = TenantResponse.model_validate(tenant)
        tenant_dict = tenant_response.model_dump()
        tenant_dict["full_name"] = tenant_response.full_name
        response_data.append(tenant_dict)
    
    return response_data

@router.get("/{tenant_id}", response_model=dict)
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get a specific tenant by ID.
    """
    logger.info(f"User {current_user.email} is retrieving tenant {tenant_id}")
    
    query = select(Tenant).where(Tenant.id == tenant_id)
    result = await session.execute(query)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        logger.warning(f"Tenant {tenant_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant_response = TenantResponse.model_validate(tenant)
    tenant_dict = tenant_response.model_dump()
    tenant_dict["full_name"] = tenant_response.full_name
    
    return tenant_dict

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new tenant without creating a user account.
    """
    logger.info(f"User {current_user.email} is creating a new tenant with data: {tenant_data}")
    
    try:
        # Create new tenant without requiring a user ID
        tenant = Tenant(
            first_name=tenant_data.first_name,
            last_name=tenant_data.last_name,
            phone=tenant_data.phone,
            email=tenant_data.email,
            status=tenant_data.status,
            # Don't default to current user ID to avoid unique constraint errors
            user_id=tenant_data.user_id,
            current_property_id=tenant_data.current_property_id
        )
        
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        
        logger.info(f"Tenant {tenant.id} created successfully")
        
        tenant_response = TenantResponse.model_validate(tenant)
        tenant_dict = tenant_response.model_dump()
        tenant_dict["full_name"] = tenant_response.full_name
        
        return tenant_dict
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )

@router.patch("/{tenant_id}", response_model=dict)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update an existing tenant.
    """
    logger.info(f"User {current_user.email} is updating tenant {tenant_id}")
    
    try:
        query = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(query)
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            logger.warning(f"Tenant {tenant_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        # Update tenant fields if provided
        update_data = tenant_data.model_dump(exclude_unset=True, exclude={"full_name"})
        for key, value in update_data.items():
            setattr(tenant, key, value)
        
        # Update the updated_at timestamp
        tenant.updated_at = datetime.utcnow()
        
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        
        logger.info(f"Tenant {tenant_id} updated successfully")
        
        tenant_response = TenantResponse.model_validate(tenant)
        tenant_dict = tenant_response.model_dump()
        tenant_dict["full_name"] = tenant_response.full_name
        
        return tenant_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant {tenant_id}: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
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
    logger.info(f"User {current_user.email} is deleting tenant {tenant_id}")
    
    query = select(Tenant).where(Tenant.id == tenant_id)
    result = await session.execute(query)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        logger.warning(f"Tenant {tenant_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    await session.delete(tenant)
    await session.commit()
    
    logger.info(f"Tenant {tenant_id} deleted successfully")
    return None