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
from Backend.models.tenant import Tenant, TenantStatus, TenantUnitLink
from Backend.models.user import User
from Backend.models.property import Property, PropertyUnit
from Backend.models.lease import Lease
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
    
    # Use simple select without joinedload for now - we'll fetch relationships separately
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
    
    # Convert each tenant to a response dictionary with all necessary data
    response_data = []
    for tenant in tenants:
        # Basic tenant data
        tenant_dict = {
            "id": tenant.id,
            "first_name": tenant.first_name,
            "last_name": tenant.last_name,
            "full_name": f"{tenant.first_name} {tenant.last_name}".strip(),
            "phone": tenant.phone,
            "email": tenant.email,
            "status": tenant.status,
            "created_at": tenant.created_at,
            "updated_at": tenant.updated_at,
            
            # Initialize empty related data
            "properties": [],
            "units": [],
            "leases": []
        }
        
        # Fetch current property if it exists
        if tenant.current_property_id is not None:
            property_query = select(Property).where(Property.id == tenant.current_property_id)
            property_result = await session.execute(property_query)
            current_property = property_result.scalar_one_or_none()
            
            if current_property:
                tenant_dict["properties"] = [{
                    "id": current_property.id,
                    "name": current_property.name
                }]
        
        # Fetch units for this tenant
        unit_links_query = select(TenantUnitLink).where(TenantUnitLink.tenant_id == tenant.id)
        unit_links_result = await session.execute(unit_links_query)
        unit_links = unit_links_result.scalars().all()
        
        if unit_links:
            unit_ids = [link.unit_id for link in unit_links]
            units_query = select(PropertyUnit).where(PropertyUnit.id.in_(unit_ids))
            units_result = await session.execute(units_query)
            units = units_result.scalars().all()
            
            tenant_dict["units"] = [
                {"id": unit.id, "unit_number": unit.unit_number} 
                for unit in units
            ]
        
        # Fetch leases for this tenant
        leases_query = select(Lease).where(Lease.tenant_id == tenant.id)
        leases_result = await session.execute(leases_query)
        leases = leases_result.scalars().all()
        
        # Add lease information that we need for counts
        if leases:
            active_leases = []
            now = datetime.utcnow().date()
            
            for lease in leases:
                lease_data = {
                    "id": lease.id,
                    "start_date": lease.start_date,
                    "end_date": lease.end_date,
                    "status": lease.status,
                    "monthly_rent": lease.monthly_rent
                }
                
                # Add to active_leases array if it's current
                if (lease.status == "ACTIVE" and 
                    lease.start_date <= now and 
                    lease.end_date >= now):
                    active_leases.append(lease_data)
                    
                tenant_dict["leases"].append(lease_data)
                
            # Add helpful derived properties for dashboard counting
            if active_leases:
                active_lease = active_leases[0]  # Use the first active lease
                tenant_dict["lease_start"] = active_lease["start_date"]
                tenant_dict["lease_end"] = active_lease["end_date"]
        
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
    
    # Use simple select without joinedload
    query = select(Tenant).where(Tenant.id == tenant_id)
    
    result = await session.execute(query)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        logger.warning(f"Tenant {tenant_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Convert tenant to a dictionary with all necessary data
    tenant_dict = {
        "id": tenant.id,
        "first_name": tenant.first_name,
        "last_name": tenant.last_name,
        "full_name": f"{tenant.first_name} {tenant.last_name}".strip(),
        "phone": tenant.phone,
        "email": tenant.email,
        "status": tenant.status,
        "created_at": tenant.created_at,
        "updated_at": tenant.updated_at,
        
        # Initialize empty related data
        "properties": [],
        "units": [],
        "leases": []
    }
    
    # Fetch current property if it exists
    if tenant.current_property_id is not None:
        property_query = select(Property).where(Property.id == tenant.current_property_id)
        property_result = await session.execute(property_query)
        current_property = property_result.scalar_one_or_none()
        
        if current_property:
            tenant_dict["properties"] = [{
                "id": current_property.id,
                "name": current_property.name
            }]
    
    # Fetch units for this tenant
    unit_links_query = select(TenantUnitLink).where(TenantUnitLink.tenant_id == tenant.id)
    unit_links_result = await session.execute(unit_links_query)
    unit_links = unit_links_result.scalars().all()
    
    if unit_links:
        unit_ids = [link.unit_id for link in unit_links]
        units_query = select(PropertyUnit).where(PropertyUnit.id.in_(unit_ids))
        units_result = await session.execute(units_query)
        units = units_result.scalars().all()
        
        tenant_dict["units"] = [
            {"id": unit.id, "unit_number": unit.unit_number} 
            for unit in units
        ]
    
    # Fetch leases for this tenant
    leases_query = select(Lease).where(Lease.tenant_id == tenant.id)
    leases_result = await session.execute(leases_query)
    leases = leases_result.scalars().all()
    
    # Add lease information that we need for counts
    if leases:
        active_leases = []
        now = datetime.utcnow().date()
        
        for lease in leases:
            lease_data = {
                "id": lease.id,
                "start_date": lease.start_date,
                "end_date": lease.end_date,
                "status": lease.status,
                "monthly_rent": lease.monthly_rent
            }
            
            # Add to active_leases array if it's current
            if (lease.status == "ACTIVE" and 
                lease.start_date <= now and 
                lease.end_date >= now):
                active_leases.append(lease_data)
                
            tenant_dict["leases"].append(lease_data)
            
        # Add helpful derived properties for dashboard counting
        if active_leases:
            active_lease = active_leases[0]  # Use the first active lease
            tenant_dict["lease_start"] = active_lease["start_date"]
            tenant_dict["lease_end"] = active_lease["end_date"]
    
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
    
    # Check if tenant has any associated leases
    lease_query = select(Lease).where(Lease.tenant_id == tenant_id)
    lease_result = await session.execute(lease_query)
    leases = lease_result.scalars().all()
    
    if leases:
        logger.warning(f"Cannot delete tenant {tenant_id} because they have {len(leases)} associated leases")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete tenant because they have associated leases. Please delete the leases first or remove the tenant from the leases."
        )
    
    # Check for any other database constraints (optional)
    try:
        await session.delete(tenant)
        await session.commit()
        
        logger.info(f"Tenant {tenant_id} deleted successfully")
        return None
    except Exception as e:
        logger.error(f"Error deleting tenant {tenant_id}: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant: {str(e)}"
        )