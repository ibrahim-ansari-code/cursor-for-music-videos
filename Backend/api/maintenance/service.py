import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import delete, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col, and_

from Backend.models.enums import MaintenancePriority, MaintenanceStatus, UserType
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.azure_blob import upload_maintenance_photo_to_blob, generate_secure_document_url
from Backend.api.maintenance.notifications import send_maintenance_notifications

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
        
        # For non-admin users, add permission check based on user type
        if not current_user.is_admin:
            if current_user.user_type == UserType.LANDLORD:
                # Landlord must own the property
                property_query = property_query.where(col(Property.user_id) == current_user.id)
            elif current_user.user_type == UserType.TENANT:
                # Tenant must be associated with the property via a unit
                property_query = property_query.join(PropertyUnit).join(Tenant).where(
                        (col(Property.id) == property_id) & (col(Tenant.user_id) == current_user.id)
                    )
        
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
            selectinload(getattr(MaintenanceRequest, "tenant")),
            selectinload(getattr(MaintenanceRequest, "vendor"))
        ).order_by(
            # NEW status requests appear first (0 = NEW, 1 = all others)
            case(
                (col(MaintenanceRequest.status) == MaintenanceStatus.NEW, 0),
                else_=1
            ),
            # Then sort by created_at descending within each group
            col(MaintenanceRequest.created_at).desc()
        )

        # For non-admin users, filter requests based on their role.
        if not current_user.is_admin:
            if current_user.user_type == UserType.LANDLORD:
                # Landlords can see all requests for their properties.
                query = query.join(Property, col(MaintenanceRequest.property_id) == col(Property.id))
                query = query.where(col(Property.user_id) == current_user.id)
            elif current_user.user_type == UserType.TENANT:
                # Tenants can only see maintenance requests they have created.
                query = query.where(col(MaintenanceRequest.user_id) == current_user.id)

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
        
        For tenant users, automatically infers property_id and tenant_id from their profile.
        For landlords/admins, requires explicit property_id.
        """
        # Auto-infer context for tenant users (industry standard pattern)
        if current_user.user_type == UserType.TENANT:
            # Eagerly load assigned_units to get the tenant's unit
            tenant_query = select(Tenant).options(
                selectinload(getattr(Tenant, "assigned_units"))
            ).where(col(Tenant.user_id) == current_user.id)
            user_tenant = await session.scalar(tenant_query)
            
            if not user_tenant:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tenant profile found for your account. Please contact your landlord."
                )
            
            # Infer property_id, tenant_id, and unit_id from tenant profile
            actual_tenant_id = user_tenant.id
            actual_property_id = user_tenant.current_property_id
            
            if not actual_property_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No property assigned to your account. Please contact your landlord."
                )
            
            # Auto-infer unit_id from assigned_units (property_units.tenant_id)
            actual_unit_id = data.unit_id  # Use explicit if provided
            if not actual_unit_id and user_tenant.assigned_units:
                for unit in user_tenant.assigned_units:
                    if unit.property_id == actual_property_id:
                        actual_unit_id = unit.id
                        logger.info(
                            "Auto-inferred unit_id %s from assigned_units for tenant %s",
                            actual_unit_id, actual_tenant_id
                        )
                        break
            
            logger.info(
                "Tenant user %s creating maintenance request for property %s, unit %s (auto-inferred)",
                current_user.id, actual_property_id, actual_unit_id or "common area"
            )
        else:
            # Landlords/admins must provide explicit property_id
            actual_property_id = data.property_id
            actual_tenant_id = data.tenant_id
            actual_unit_id = data.unit_id  # Landlords provide explicit unit_id
            
            if not actual_property_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="property_id is required for landlord/admin users"
                )
            
            logger.info(
                "User %s creating maintenance request for property %s, unit %s",
                current_user.id, actual_property_id, actual_unit_id or "common area"
            )

        try:
            # Use the new consolidated validation method with inferred/explicit IDs
            property_entity, unit_entity, tenant_entity = await MaintenanceService._validate_and_load_entities(
                property_id=actual_property_id,
                unit_id=actual_unit_id,  # Use inferred unit_id for tenants
                tenant_id=actual_tenant_id,
                current_user=current_user,
                session=session
            )

            db_request = MaintenanceRequest(
                issue_title=data.issue_title,
                description=data.description,
                property_id=actual_property_id,  # Use inferred/explicit ID
                unit_id=actual_unit_id,  # Use inferred/explicit unit ID
                tenant_id=actual_tenant_id,  # Use inferred/explicit ID
                user_id=current_user.id,
                priority=data.priority,
                status=MaintenanceStatus.NEW,  # NEW status for tenant-submitted requests
                scheduled_date=data.scheduled_date,
                estimated_cost=data.estimated_cost,
                actual_cost=data.actual_cost,
                photos=data.photos,
                assigned_to=data.assigned_to,
                preferred_time=data.preferred_time,
                vendor_id=data.vendor_id,
                notify_tenant=data.notify_tenant
            )

            session.add(db_request)
            await session.commit()
            
            # After commit, re-query to get fresh object with all relationships loaded
            # Eagerly load ALL relationships needed for notifications to avoid lazy loading issues
            result = await session.execute(
                select(MaintenanceRequest)
                .options(
                    selectinload(getattr(MaintenanceRequest, "property")),
                    selectinload(getattr(MaintenanceRequest, "unit")),
                    selectinload(getattr(MaintenanceRequest, "tenant")),
                    selectinload(getattr(MaintenanceRequest, "vendor")),
                    selectinload(getattr(MaintenanceRequest, "user"))
                )
                .where(col(MaintenanceRequest.id) == db_request.id)
            )
            created_request = result.scalar_one_or_none()
            
            if created_request is None:
                # Edge case: Record not found after commit (shouldn't happen but defensive)
                raise HTTPException(
                    status_code=500,
                    detail="Created maintenance request not found after commit"
                )
            
            # Send notifications via orchestrator (vendor assignment, status changes, etc.)
            # Session is still valid and can be used for additional queries
            await send_maintenance_notifications(
                request=created_request,
                changes={
                    'vendor_id': (None, created_request.vendor_id),
                    'status': (None, created_request.status)
                },
                session=session
            )
            
            # Send in-app notification to landlord for NEW maintenance requests
            if current_user.user_type == UserType.TENANT:
                try:
                    from Backend.api.notifications.service import NotificationService
                    
                    # Get landlord user_id from property
                    landlord_user_id = property_entity.user_id
                    
                    # Get tenant name for actor
                    tenant_name = None
                    if tenant_entity:
                        tenant_name = f"{tenant_entity.first_name or ''} {tenant_entity.last_name or ''}".strip()
                    
                    # Create notification for landlord
                    await NotificationService.create_notification(
                        user_id=landlord_user_id,
                        type="maintenance_request_new",
                        title=f"New Maintenance Request: {data.issue_title}",
                        message=f"{tenant_name or 'A tenant'} submitted a {data.priority.value.lower()} priority maintenance request.",
                        link=f"/maintenance?request_id={created_request.id}",
                        actor_id=current_user.id,
                        actor_name=tenant_name,
                        metadata={
                            "maintenance_id": created_request.id,
                            "property_id": actual_property_id,
                            "tenant_id": actual_tenant_id,
                            "priority": data.priority.value,
                            "issue_title": data.issue_title
                        },
                        priority="high" if data.priority == MaintenancePriority.HIGH else "normal",
                        group_key=f"maintenance_property_{actual_property_id}",
                        session=session
                    )
                    
                    logger.info(
                        f"Landlord notification sent for new maintenance request {created_request.id}"
                    )
                except Exception as e:
                    # Log error but don't fail the request creation
                    logger.exception(
                        f"Failed to send landlord notification for request {created_request.id}: {str(e)}"
                    )
                    # Continue without raising - notification failures shouldn't block maintenance requests
            
            return MaintenanceRequestResponse.model_validate(created_request)

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
                selectinload(getattr(MaintenanceRequest, "tenant")),
                selectinload(getattr(MaintenanceRequest, "vendor"))
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
            .options(
                selectinload(getattr(MaintenanceRequest, "property")),
                selectinload(getattr(MaintenanceRequest, "unit")),
                selectinload(getattr(MaintenanceRequest, "tenant")),
                selectinload(getattr(MaintenanceRequest, "vendor"))
            )
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

        # Capture old values BEFORE applying updates for notification tracking
        changes: dict = {}
        if 'status' in update_data:
            changes['status'] = (req.status, update_data['status'])
        if 'vendor_id' in update_data:
            changes['vendor_id'] = (req.vendor_id, update_data['vendor_id'])
        
        # Apply updates
        for key, value in update_data.items():
            setattr(req, key, value)

        session.add(req)
        await session.commit()
        
        # Send notifications via orchestrator (vendor assignment, status changes, etc.)
        if changes:
            await send_maintenance_notifications(
                request=req,
                changes=changes,
                session=session
            )
        
        # After commit, all attributes are expired. Re-query with fresh session to get updated data
        # This is the industry-standard pattern (Stripe, Airbnb, etc.)
        result = await session.execute(
            select(MaintenanceRequest)
            .options(
                selectinload(getattr(MaintenanceRequest, "property")),
                selectinload(getattr(MaintenanceRequest, "unit")),
                selectinload(getattr(MaintenanceRequest, "tenant")),
                selectinload(getattr(MaintenanceRequest, "vendor"))
            )
            .where(col(MaintenanceRequest.id) == request_id)
        )
        updated_req = result.scalar_one_or_none()
        
        if updated_req is None:
            # Edge case: Record deleted between update and re-query (race condition)
            raise HTTPException(
                status_code=404,
                detail="Maintenance request not found after update"
            )
        
        return MaintenanceRequestResponse.model_validate(updated_req)

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
            .options(
                selectinload(getattr(MaintenanceRequest, "property")),
                selectinload(getattr(MaintenanceRequest, "vendor"))
            )
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
    async def bulk_delete_maintenance_requests(
        request_ids: list[int],
        current_user: User,
        session: AsyncSession
    ) -> None:
        logger.info(
            f"User {current_user.id} attempting to bulk delete maintenance requests: {request_ids}"
        )
        
        if not request_ids:
            return

        try:
            # Step 1: Fetch all requests in a single query with ownership validation
            query = select(MaintenanceRequest).where(
                col(MaintenanceRequest.id).in_(request_ids)
            )
            if not current_user.is_admin:
                query = query.join(Property, col(MaintenanceRequest.property_id) == col(Property.id)).where(
                    col(Property.user_id) == current_user.id
                )
            
            result = await session.execute(query)
            requests_to_delete = result.scalars().all()

            # Step 2: Validate that all requested records were found
            if len(requests_to_delete) != len(set(request_ids)):
                found_ids = {req.id for req in requests_to_delete}
                missing_ids = set(request_ids) - found_ids
                logger.warning(
                    "User %s attempted to delete non-existent or unauthorized maintenance requests: %s",
                    current_user.id,
                    missing_ids,
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="One or more maintenance requests not found or you do not have permission to delete them.",
                )

            # Step 3: Delete all verified requests using bulk delete (avoids N+1 queries)
            await session.execute(
                delete(MaintenanceRequest).where(col(MaintenanceRequest.id).in_(request_ids))
            )

            # Step 4: Commit the transaction
            await session.commit()
            logger.info(
                f"User {current_user.id} successfully deleted maintenance requests: {request_ids}"
            )

        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            logger.exception("Error during bulk deletion of maintenance requests")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected error occurred during bulk deletion: {str(e)}"
            ) from e

    @staticmethod
    async def get_maintenance_summary(
        current_user: User,
        session: AsyncSession,
        property_id: Optional[int] = None
    ) -> MaintenanceSummaryResponse:
        """
        Returns a summary of maintenance requests grouped by status for the current user.

        Args:
            current_user: The authenticated user making the request.
            session: The database session.
            property_id: Optional property ID to filter the summary by a specific property.
        """
        logger.info("User %s requesting maintenance summary (property_id=%s)", current_user.id, property_id)

        query = select(
            col(MaintenanceRequest.status),
            func.count(col(MaintenanceRequest.id))
        ).group_by(col(MaintenanceRequest.status))

        if not current_user.is_admin:
            query = query.join(Property, col(MaintenanceRequest.property_id) == col(Property.id))
            query = query.where(col(Property.user_id) == current_user.id)

        # Add property filter if specified
        if property_id is not None:
            query = query.where(col(MaintenanceRequest.property_id) == property_id)

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
        authorized_roles = {UserType.LANDLORD, UserType.ADMIN, UserType.TENANT}
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

    @staticmethod
    async def generate_photo_secure_url(
        photo_url: str,
        current_user: User,
        client_ip: str | None = None
    ) -> dict:
        """
        Generate a time-limited SAS token URL for maintenance photo access.
        
        Args:
            photo_url: The Azure Blob URL of the photo
            current_user: Current authenticated user
            client_ip: Optional client IP for restriction
            
        Returns:
            Dict with secure_url, expires_at, expires_in_seconds
        """
        # Authorization check - allow landlords, admins, and tenants
        authorized_roles = {UserType.LANDLORD, UserType.ADMIN, UserType.TENANT}
        if current_user.user_type not in authorized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access maintenance photos."
            )
        
        try:
            # Generate secure URL with SAS token
            url_data = await generate_secure_document_url(
                blob_url=photo_url,
                user_id=current_user.id,
                document_id=photo_url,  # Use URL as identifier for logging
                expires_in_hours=1,
                client_ip=client_ip,
            )
            
            return url_data
            
        except Exception as e:
            logger.error(f"Error generating secure URL for maintenance photo: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate secure URL: {str(e)}"
            )
