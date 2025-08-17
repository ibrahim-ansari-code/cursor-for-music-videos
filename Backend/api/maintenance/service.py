import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col, and_

from Backend.models.enums import MaintenancePriority, MaintenanceStatus, UserType
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.azure_blob import upload_maintenance_photo_to_blob

from .helpers import check_permission, validate_file_content, validate_file_size
from .schemas import (
    MaintenanceRequestCreate,
    MaintenanceRequestResponse,
    MaintenanceRequestUpdate,
    MaintenanceSummaryResponse,
    PropertyInfo,
    UnitInfo,
    TenantInfo,
)

logger = logging.getLogger(__name__)


class MaintenanceService:
    @staticmethod
    async def _validate_and_load_entities(
        property_id: int,
        unit_id: Optional[int],
        tenant_id: Optional[int],
        current_user: User,
        session: AsyncSession
    ) -> tuple[Property, Optional[PropertyUnit], Optional[Tenant]]:
        """
        Validates and loads property, unit, and tenant entities in a single optimized query.
        Checks ownership permissions for non-admin users.
        Returns a tuple of (property, unit, tenant) entities.
        """
        # Build optimized query to load all entities at once
        property_query = select(Property).where(col(Property.id) == property_id)
        
        # For non-admin users, add ownership check
        if not current_user.is_admin:
            property_query = property_query.where(col(Property.user_id) == current_user.id)
        
        result = await session.execute(property_query)
        property_entity = result.scalar_one_or_none()
        
        if not property_entity:
            if not current_user.is_admin:
                # Check if property exists but user doesn't own it
                check_result = await session.execute(
                    select(col(Property.id)).where(col(Property.id) == property_id)
                )
                if check_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=403,
                        detail="You do not have permission to access this property."
                    )
            raise HTTPException(
                status_code=404,
                detail="Property not found."
            )
        
        # Validate and load unit if provided
        unit_entity = None
        if unit_id is not None:
            unit_result = await session.execute(
                select(PropertyUnit).where(
                    and_(
                        PropertyUnit.id == unit_id,
                        PropertyUnit.property_id == property_id
                    )
                )
            )
            unit_entity = unit_result.scalar_one_or_none()
            
            if not unit_entity:
                # Check if unit exists but belongs to different property
                unit_check = await session.execute(
                    select(col(PropertyUnit.property_id)).where(col(PropertyUnit.id) == unit_id)
                )
                unit_property_id = unit_check.scalar_one_or_none()
                
                if unit_property_id:
                    raise HTTPException(
                        status_code=400,
                        detail="The specified unit does not belong to the specified property."
                    )
                raise HTTPException(
                    status_code=404,
                    detail="Unit not found."
                )
        
        # Validate and load tenant if provided
        tenant_entity = None
        if tenant_id is not None:
            tenant_result = await session.execute(
                select(Tenant).where(col(Tenant.id) == tenant_id)
            )
            tenant_entity = tenant_result.scalar_one_or_none()
            
            if not tenant_entity:
                raise HTTPException(
                    status_code=404,
                    detail="Tenant not found."
                )
            
            # TODO: Add validation that tenant is associated with the unit/property
            # This should check the lease or tenant assignment
        
        return property_entity, unit_entity, tenant_entity
    @staticmethod
    async def list_maintenance_requests(
        current_user: User,
        session: AsyncSession,
        req_status: Optional[MaintenanceStatus] = None,
        priority: Optional[MaintenancePriority] = None,
        property_id: Optional[int] = None,
        unit_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        assigned_to: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MaintenanceRequestResponse]:
        """
        Retrieves a list of maintenance requests with optional filtering and pagination.
        """
        logger.info(
            "User %s listing maintenance requests with filters: status=%s, priority=%s, property_id=%s, unit_id=%s, tenant_id=%s, assigned_to=%s",
            current_user.id, req_status, priority, property_id, unit_id, tenant_id, assigned_to
        )

        query = select(MaintenanceRequest).options(
            selectinload(getattr(MaintenanceRequest, "property")),
            selectinload(getattr(MaintenanceRequest, "unit")),
            selectinload(getattr(MaintenanceRequest, "tenant"))  
        ).order_by(col(MaintenanceRequest.created_at).desc())  # Add ordering for better UX

        if not current_user.is_admin:
            query = query.join(Property, col(MaintenanceRequest.property_id) == col(Property.id))
            query = query.where(col(Property.user_id) == current_user.id)

        if req_status is not None:
            query = query.where(col(MaintenanceRequest.status) == req_status)
        if priority is not None:
            query = query.where(col(MaintenanceRequest.priority) == priority)
        if property_id is not None:
            query = query.where(col(MaintenanceRequest.property_id) == property_id)
        if unit_id is not None:
            query = query.where(col(MaintenanceRequest.unit_id) == unit_id)
        if tenant_id is not None:
            query = query.where(col(MaintenanceRequest.tenant_id) == tenant_id)
        if assigned_to is not None:
            query = query.where(col(MaintenanceRequest.assigned_to) == assigned_to)

        query = query.offset(offset).limit(limit)

        result = await session.execute(query)
        requests = result.unique().scalars().all()
        return [MaintenanceRequestResponse.model_validate(req) for req in requests]

    @staticmethod
    async def create_maintenance_request(
        data: MaintenanceRequestCreate,
        current_user: User,
        session: AsyncSession
    ) -> MaintenanceRequestResponse:
        """
        Creates a new maintenance request for a property.
        """
        logger.info(
            "User %s creating maintenance request for property %s",
            current_user.id, data.property_id
        )

        try:
            # Use the new consolidated validation method
            property_entity, unit_entity, tenant_entity = await MaintenanceService._validate_and_load_entities(
                property_id=data.property_id,
                unit_id=data.unit_id,
                tenant_id=data.tenant_id,
                current_user=current_user,
                session=session
            )

            db_request = MaintenanceRequest(
                issue_title=data.issue_title,
                description=data.description,
                property_id=data.property_id,
                unit_id=data.unit_id,
                tenant_id=data.tenant_id,
                user_id=current_user.id,
                priority=data.priority,
                status=MaintenanceStatus.PENDING,
                scheduled_date=data.scheduled_date,
                estimated_cost=data.estimated_cost,
                actual_cost=data.actual_cost,
                photos=data.photos,
                assigned_to=data.assigned_to
            )

            session.add(db_request)
            await session.commit()
            
            # Efficiently load all relationships in a single refresh
            await session.refresh(
                db_request,
                attribute_names=["property", "unit", "tenant"]
            )
            
            return MaintenanceRequestResponse.model_validate(db_request)

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error creating maintenance request")
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create maintenance request: {str(e)}"
            ) from e

    @staticmethod
    async def get_maintenance_request(
        request_id: int,
        current_user: User,
        session: AsyncSession
    ) -> MaintenanceRequestResponse:
        """
        Retrieves a maintenance request by its ID after verifying user permissions.
        """
        result = await session.execute(
            select(MaintenanceRequest)
            .options(
                selectinload(getattr(MaintenanceRequest, "property")),
                selectinload(getattr(MaintenanceRequest, "unit")),
                selectinload(getattr(MaintenanceRequest, "tenant"))
            )
            .where(col(MaintenanceRequest.id) == request_id)
        )
        req = result.scalar_one_or_none()

        if not req:
            raise HTTPException(
                status_code=404, detail="Maintenance request not found"
            )

        await check_permission(req, current_user, session)
        return MaintenanceRequestResponse.model_validate(req)

    @staticmethod
    async def update_maintenance_request(
        request_id: int,
        data: MaintenanceRequestUpdate,
        current_user: User,
        session: AsyncSession
    ) -> MaintenanceRequestResponse:
        """
        Updates an existing maintenance request with new data, validating property and unit ownership.
        """
        result = await session.execute(
            select(MaintenanceRequest)
            .options(selectinload(getattr(MaintenanceRequest, "property")))
            .where(col(MaintenanceRequest.id) == request_id)
        )
        req = result.scalar_one_or_none()

        if not req:
            raise HTTPException(
                status_code=404, detail="Maintenance request not found"
            )

        await check_permission(req, current_user, session)

        update_data = data.model_dump(exclude_unset=True)

        # Check if property or unit is being changed - if so, validate the new values
        if ('property_id' in update_data and update_data['property_id'] != req.property_id) or \
           ('unit_id' in update_data and update_data['unit_id'] != req.unit_id) or \
           ('tenant_id' in update_data and update_data['tenant_id'] != req.tenant_id):
            
            # Use consolidated validation for new property/unit/tenant
            new_property_id = update_data.get('property_id', req.property_id)
            new_unit_id = update_data.get('unit_id', req.unit_id)
            new_tenant_id = update_data.get('tenant_id', req.tenant_id)
            
            # Validate the new entities using our consolidated method
            property_entity, unit_entity, tenant_entity = await MaintenanceService._validate_and_load_entities(
                property_id=new_property_id,
                unit_id=new_unit_id,
                tenant_id=new_tenant_id,
                current_user=current_user,
                session=session
            )

        for key, value in update_data.items():
            setattr(req, key, value)

        session.add(req)
        await session.commit()
        
        # Efficiently refresh with all relationships instead of re-querying
        await session.refresh(
            req,
            attribute_names=["property", "unit", "tenant"]
        )
        
        return MaintenanceRequestResponse.model_validate(req)

    @staticmethod
    async def delete_maintenance_request(
        request_id: int,
        current_user: User,
        session: AsyncSession
    ) -> None:
        """
        Deletes a maintenance request by its ID after verifying user permissions.
        """
        result = await session.execute(
            select(MaintenanceRequest)
            .options(selectinload(getattr(MaintenanceRequest, "property")))
            .where(col(MaintenanceRequest.id) == request_id)
        )
        req = result.scalar_one_or_none()

        if not req:
            raise HTTPException(
                status_code=404, detail="Maintenance request not found"
            )

        await check_permission(req, current_user, session)
        await session.delete(req)
        await session.commit()
        logger.info(
            f"User {current_user.id} deleted maintenance request {request_id}"
        )

    @staticmethod
    async def get_maintenance_summary(
        current_user: User,
        session: AsyncSession
    ) -> MaintenanceSummaryResponse:
        """
        Returns a summary of maintenance requests grouped by status for the current user.
        """
        logger.info("User %s requesting maintenance summary", current_user.id)

        query = select(
            col(MaintenanceRequest.status),
            func.count(col(MaintenanceRequest.id))
        ).group_by(col(MaintenanceRequest.status))
        
        if not current_user.is_admin:
            query = query.join(Property, col(MaintenanceRequest.property_id) == col(Property.id))
            query = query.where(col(Property.user_id) == current_user.id)
        
        result = await session.execute(query)

        summary = {status.value.lower().replace(" ", "_"): 0 for status in MaintenanceStatus}
        summary["total_requests"] = 0

        for status_value, count in result:
            status_key = status_value.value.lower().replace(" ", "_")
            if status_key in summary:
                summary[status_key] = count
            summary["total_requests"] += count

        return MaintenanceSummaryResponse(**summary)

    @staticmethod
    async def upload_maintenance_photo(
        upload_file,
        current_user: User
    ) -> dict:
        """
        Uploads a maintenance photo to Azure Blob Storage and returns its public URL.
        """
        authorized_roles = {UserType.LANDLORD, UserType.ADMIN}
        if current_user.user_type not in authorized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to upload maintenance photos."
            )

        if not await validate_file_content(upload_file):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type. Only PDF, JPG, and PNG files are allowed."
            )

        MAX_SIZE = 10 * 1024 * 1024  # 10 MB in bytes
        await validate_file_size(upload_file, MAX_SIZE)

        try:
            url = await upload_maintenance_photo_to_blob(upload_file, current_user.id)
            return {"photo_url": url}
        except Exception as e:
            logger.exception("Failed to upload maintenance photo to blob storage")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload maintenance photo: {str(e)}"
            )