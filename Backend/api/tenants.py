from typing import List, Optional, Union
import logging
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload, selectinload
from pydantic import BaseModel, constr, EmailStr, validator, computed_field
from sqlmodel import col
# Explicitly import property decorator (though usually built-in)
# from builtins import property # No longer needed

from Backend.database import get_session
from Backend.models.tenant import Tenant, TenantStatus
from Backend.models.user import User, UserType
from Backend.models.property import Property, PropertyUnit
from Backend.models.lease import Lease, LeaseStatus
from Backend.api.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/tenants",
    tags=["tenants"],
)

# === Helper Function for Tenant Permission Checks ===
async def check_tenant_permission(
    tenant_id: int,
    session: AsyncSession,
    current_user: User,
    action: str = "view"
) -> Tenant:
    """Check if the current user has permission to access/modify the tenant."""
    # Admins can do anything
    if current_user.is_admin:
        query = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(query)
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
        return tenant

    # Tenants can view/update their own linked Tenant profile
    if current_user.user_type == UserType.TENANT:
        if tenant_id is not None:
            query = select(Tenant).where(Tenant.id == tenant_id, Tenant.user_id == current_user.id)
            result = await session.execute(query)
            tenant = result.scalar_one_or_none()
            if tenant and action in ["view", "update"]:
                return tenant
        # If tenant_id doesn't match or action not allowed for tenant
        logger.warning(f"Tenant {current_user.id} permission denied for {action} tenant {tenant_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to {action} this tenant profile")

    # Landlords can view/update/delete tenants associated with their properties via leases
    if current_user.user_type == UserType.LANDLORD:
        query = (
            select(Tenant)
            .join(Lease, Tenant.id == Lease.tenant_id)
            .join(Property, Lease.property_id == Property.id)
            .where(
                and_(
                    Tenant.id == tenant_id,
                    Property.user_id == current_user.id
                )
            )
            .limit(1) # Check if *any* link exists
        )
        result = await session.execute(query)
        tenant = result.scalar_one_or_none()

        if not tenant:
             # Alternative check: Is tenant currently in one of landlord's properties?
             query_current = (
                 select(Tenant)
                 .join(Property, Tenant.current_property_id == Property.id)
                 .where(Tenant.id == tenant_id, Property.user_id == current_user.id)
                 .limit(1)
             )
             result_current = await session.execute(query_current)
             tenant = result_current.scalar_one_or_none()

        if tenant: # If found via lease OR current_property
             return tenant
        else:
            logger.warning(f"Landlord {current_user.id} permission denied for {action} tenant {tenant_id}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to {action} this tenant")

    # Default deny
    logger.error(f"Unknown user type or permission error for user {current_user.id}, action {action}, tenant {tenant_id}")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to {action} this tenant")

# === Models ===

# Minimal response models for related entities
class PropertyResponseSimple(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True

class UnitResponseSimple(BaseModel):
    id: int
    name: str # Assuming unit has a 'name' or 'unit_number' field
    property: Optional[PropertyResponseSimple] = None # Nested property info

    class Config:
        from_attributes = True

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
    # Add fields for unit and property
    unit: Optional[UnitResponseSimple] = None
    property: Optional[PropertyResponseSimple] = None
    
    class Config:
        from_attributes = True
    
    @computed_field
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

# === API Routes ===
@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    status: Optional[TenantStatus] = None,
    search: Optional[str] = None,
    property_id: Optional[int] = None, # Allow filtering by property for landlords/admins
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get tenants, respecting user roles and ownership.
    Landlords see tenants associated with their properties.
    Admins see all tenants.
    Tenants cannot list other tenants.
    """
    logger.info(f"User {current_user.email} (type: {current_user.user_type}) is retrieving tenants")

    if current_user.user_type == UserType.TENANT:
        logger.warning(f"Tenant {current_user.id} attempted to list tenants.")
        # Tenants cannot list other tenants - return empty list or raise 403
        # Returning empty list might be less disruptive for UI
        return []
        # raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to list tenants")

    # Base query joining Tenant -> Lease -> Property to check ownership
    # We select distinct Tenant records
    query = (
        select(Tenant).distinct()
        .outerjoin(Lease, Tenant.id == Lease.tenant_id)
        .outerjoin(Property, Lease.property_id == Property.id)
    )

    # Apply basic filters
    filters = []
    if status:
        filters.append(Tenant.status == status)
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                col(Tenant.first_name).ilike(search_term),
                col(Tenant.last_name).ilike(search_term),
                col(Tenant.email).ilike(search_term) # Optionally search email
            )
        )

    # Apply ownership/property filters
    if current_user.user_type == UserType.LANDLORD:
        # Landlord sees tenants linked to their properties via Leases
        # OR tenants currently residing in their property (current_property_id)
        landlord_prop_subquery = select(Property.id).where(Property.user_id == current_user.id).scalar_subquery()
        filters.append(
            or_(
                Lease.property_id.in_(landlord_prop_subquery),
                Tenant.current_property_id.in_(landlord_prop_subquery)
            )
        )
        # Additionally filter by specific property_id if provided by landlord
        if property_id:
             filters.append(or_(
                 Lease.property_id == property_id,
                 Tenant.current_property_id == property_id
             ))

    elif current_user.is_admin:
        # Admin can filter by any property_id if provided
        if property_id:
             filters.append(or_(
                 Lease.property_id == property_id,
                 Tenant.current_property_id == property_id
             ))
    # No else needed for Tenant, as they are blocked earlier

    if filters:
        query = query.where(and_(*filters))

    # Apply pagination and ordering
    query = query.order_by(Tenant.last_name, Tenant.first_name).offset(skip).limit(limit)

    result = await session.execute(query)
    tenants_orm = result.scalars().all()
    logger.info(f"Retrieved {len(tenants_orm)} tenants for user {current_user.id}")

    # Convert ORM objects to response models, fetching related unit/property info
    # This part needs optimization, fetching unit/property one by one is inefficient (N+1 problem)
    # Consider a more optimized query or batch fetching later.
    response_data = []
    for tenant in tenants_orm:
        tenant_response = TenantResponse.model_validate(tenant)
        # Find the most relevant/current unit/property for display (could be complex)
        # Simple approach: check current_property_id first, then maybe latest lease
        current_prop_id_to_check = tenant.current_property_id

        # This part is simplified; real logic might need latest lease etc.
        if current_prop_id_to_check:
             unit_query = (
                select(PropertyUnit)
                .options(selectinload(PropertyUnit.property))
                .where(PropertyUnit.tenant_id == tenant.id, PropertyUnit.property_id == current_prop_id_to_check)
                .order_by(PropertyUnit.id.desc()) # Simple tie-breaker
                .limit(1)
             )
             unit_result = await session.execute(unit_query)
             assigned_unit = unit_result.scalar_one_or_none()

             if assigned_unit and assigned_unit.property:
                  property_info = PropertyResponseSimple.model_validate(assigned_unit.property)
                  unit_info = UnitResponseSimple.model_validate(assigned_unit)
                  unit_info.property = property_info
                  tenant_response.unit = unit_info
                  tenant_response.property = property_info

        response_data.append(tenant_response)

    return response_data

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get a specific tenant by ID, checking permissions."""
    logger.info(f"User {current_user.email} requesting tenant {tenant_id}")
    tenant_orm = await check_tenant_permission(tenant_id, session, current_user, action="view")

    # Fetch the assigned unit and property (similar logic to get_tenants, needs optimization)
    tenant_response = TenantResponse.model_validate(tenant_orm)
    current_prop_id_to_check = tenant_orm.current_property_id

    if current_prop_id_to_check:
         unit_query = (
            select(PropertyUnit)
            .options(selectinload(PropertyUnit.property))
            .where(PropertyUnit.tenant_id == tenant_orm.id, PropertyUnit.property_id == current_prop_id_to_check)
            .order_by(PropertyUnit.id.desc())
            .limit(1)
         )
         unit_result = await session.execute(unit_query)
         assigned_unit = unit_result.scalar_one_or_none()

         if assigned_unit and assigned_unit.property:
              property_info = PropertyResponseSimple.model_validate(assigned_unit.property)
              unit_info = UnitResponseSimple.model_validate(assigned_unit)
              unit_info.property = property_info
              tenant_response.unit = unit_info
              tenant_response.property = property_info

    return tenant_response

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new tenant. Landlords can only assign to their own properties.
    Tenants cannot create other tenants.
    """
    logger.info(f"User {current_user.email} creating tenant: {tenant_data}")

    if current_user.user_type == UserType.TENANT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenants cannot create tenants")

    # If assigning to a property, check landlord ownership
    if tenant_data.current_property_id:
        if current_user.user_type == UserType.LANDLORD:
            prop_query = select(Property.id).where(
                and_(Property.id == tenant_data.current_property_id, Property.user_id == current_user.id)
            )
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign tenant to a property you do not own")
        # Admin doesn't need this check but we need to ensure the property exists
        elif current_user.is_admin:
             prop_query = select(Property.id).where(Property.id == tenant_data.current_property_id)
             prop_exists = await session.scalar(prop_query)
             if not prop_exists:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned property not found")

    # Check if user_id is provided and if that user exists and is a Tenant type
    if tenant_data.user_id:
        user_query = select(User).where(User.id == tenant_data.user_id)
        target_user = await session.scalar(user_query)
        if not target_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with ID {tenant_data.user_id} not found")
        if target_user.user_type != UserType.TENANT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User ID {tenant_data.user_id} does not belong to a Tenant")
        # Check if a Tenant record already exists for this user_id
        existing_tenant_query = select(Tenant.id).where(Tenant.user_id == tenant_data.user_id)
        existing_tenant = await session.scalar(existing_tenant_query)
        if existing_tenant:
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"A tenant profile already exists for user ID {tenant_data.user_id}")

    try:
        tenant = Tenant.model_validate(tenant_data) # Use Pydantic validation
        tenant.created_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()

        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        logger.info(f"Tenant {tenant.id} created successfully by user {current_user.id}")
        return TenantResponse.model_validate(tenant)
    except Exception as e:
        logger.error(f"Error creating tenant: {str(e)}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update an existing tenant, checking permissions."""
    logger.info(f"User {current_user.email} updating tenant {tenant_id}")
    tenant = await check_tenant_permission(tenant_id, session, current_user, action="update")

    # If updating current_property_id, check landlord ownership
    if tenant_data.current_property_id is not None and tenant_data.current_property_id != tenant.current_property_id:
        if current_user.user_type == UserType.LANDLORD:
            prop_query = select(Property.id).where(
                and_(Property.id == tenant_data.current_property_id, Property.user_id == current_user.id)
            )
            prop_exists = await session.scalar(prop_query)
            if not prop_exists:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign tenant to a property you do not own")
        elif current_user.is_admin:
             prop_query = select(Property.id).where(Property.id == tenant_data.current_property_id)
             prop_exists = await session.scalar(prop_query)
             if not prop_exists:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned property not found")

    try:
        update_data = tenant_data.model_dump(exclude_unset=True, exclude={"full_name"})
        for key, value in update_data.items():
            setattr(tenant, key, value)

        tenant.updated_at = datetime.utcnow()

        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        logger.info(f"Tenant {tenant_id} updated successfully by user {current_user.id}")
        return TenantResponse.model_validate(tenant)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant {tenant_id}: {str(e)}", exc_info=True)
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
    """Delete a tenant, checking permissions."""
    logger.info(f"User {current_user.email} deleting tenant {tenant_id}")

    if current_user.user_type == UserType.TENANT:
        # Tenants cannot delete tenant profiles (even their own via this endpoint perhaps? TBD)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete tenants")

    tenant = await check_tenant_permission(tenant_id, session, current_user, action="delete")

    # Check if tenant has any associated active leases
    lease_query = select(Lease.id).where(
        and_(Lease.tenant_id == tenant_id, Lease.status == LeaseStatus.ACTIVE)
    ).limit(1)
    active_lease_exists = await session.scalar(lease_query)

    if active_lease_exists:
        logger.warning(f"Cannot delete tenant {tenant_id} due to active leases")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete tenant with active leases. Please terminate or reassign leases first."
        )

    try:
        await session.delete(tenant)
        await session.commit()

        logger.info(f"Tenant {tenant_id} deleted successfully by user {current_user.id}")
        return None
    except Exception as e:
        # Catch potential DB constraint errors if tenant is linked elsewhere
        logger.error(f"Error deleting tenant {tenant_id}: {str(e)}", exc_info=True)
        await session.rollback()
        # Provide a more generic error, or specific if known constraint
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tenant. Check for related records (e.g., historical payments, messages). Error: {str(e)}"
        )