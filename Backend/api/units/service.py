import logging
from typing import List

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import and_, nulls_last
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col

from Backend.api.leases.schemas import LeaseResponse
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User

from .schemas import (
    UnitCreate, UnitCreateResponse, UnitResponse, UnitUpdate,
    BulkUnitCreate, BulkUnitCreateResponse, UnitSearchFilters
)

logger = logging.getLogger(__name__)


class UnitService:
    @staticmethod
    async def get_unit_or_404(unit_id: int, session: AsyncSession, current_user: User) -> PropertyUnit:
        """Retrieve a unit by ID, ensuring the current user has permission."""
        result = await session.execute(
            select(PropertyUnit)
            # Load property for permission check, and tenant for potential use in response
            .options(
                joinedload(getattr(PropertyUnit, "property")),
                selectinload(getattr(PropertyUnit, "tenant"))
            )
            .where(col(PropertyUnit.id) == unit_id)
        )
        unit = result.unique().scalar_one_or_none()

        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

        # Permission check: User must own the parent property or be an admin
        if not current_user.is_admin and unit.property and unit.property.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this unit"
            )
        return unit

    @staticmethod
    async def create_unit(
        property_id: int,
        unit_data: UnitCreate,
        session: AsyncSession,
        current_user: User
    ) -> UnitCreateResponse:
        """Create a new unit, ensuring user owns the property."""
        # Check if property exists and user has permission
        result = await session.execute(select(Property).where(col(Property.id) == property_id))
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

        # Permission check using user_id
        if not current_user.is_admin and property_obj.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to add units to this property"
            )

        # Create the new unit
        new_unit = PropertyUnit(
            **unit_data.model_dump(),
            property_id=property_id
        )
        session.add(new_unit)
        try:
            await session.commit()
            await session.refresh(new_unit)
            logger.info(
                f"Created unit {new_unit.id} for property {property_id} by user {current_user.id}")
            # Use the specific create response model which omits tenant info
            return UnitCreateResponse.model_validate(new_unit)
        except ValidationError as e:  # Catch Pydantic validation errors specifically
            logger.error(f"Response validation error for new unit: {e.errors()}")
            # Don't rollback if commit succeeded but response failed
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unit created, but failed to serialize response: {e.errors()}"
            )
        except Exception as e:
            await session.rollback()
            logger.error(
                f"Error creating unit for property {property_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while creating the unit."
            )

    @staticmethod
    async def update_unit(
        unit_id: int,
        unit_data: UnitUpdate,
        session: AsyncSession,
        current_user: User
    ) -> UnitResponse:
        """
        Updates a property unit with partial or full data, enforcing permission and data consistency.

        Validates user authorization, applies requested updates, and ensures consistency between tenant assignment and rental status. Checks for tenant existence when assigning a tenant, and automatically clears or sets related fields to maintain logical integrity (e.g., vacating a unit clears tenant and rent unless explicitly set). Returns the updated unit with tenant information.

        Raises:
            HTTPException: If the unit or tenant does not exist, if no update data is provided, or if an error occurs during update or response serialization.
        """
        # get_unit_or_404 already performs the ownership check
        unit_to_update = await UnitService.get_unit_or_404(unit_id, session, current_user)

        update_data = unit_data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided"
            )

        # Check if assigning a tenant
        new_tenant_id = update_data.get('tenant_id')
        if new_tenant_id is not None:
            # Verify tenant exists
            tenant_result = await session.execute(select(Tenant).where(Tenant.id == new_tenant_id))
            if not tenant_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant with ID {new_tenant_id} not found"
                )

        tenant_id_updated = 'tenant_id' in update_data
        rent_explicitly_set = 'monthly_rent' in update_data

        # Apply updates from request (excluding is_rented which is managed internally)
        for key, value in update_data.items():
            if key == 'is_rented':
                logger.warning("Attempted to directly update is_rented field - this is managed internally")
                continue
            if hasattr(unit_to_update, key):
                setattr(unit_to_update, key, value)
            else:
                logger.warning(
                    f"Attempted to update non-existent field '{key}' on PropertyUnit")

        # --- Logic to handle tenant assignment and rental status ---
        # Note: is_rented is now derived from tenant assignment/lease status
        
        # Scenario 1: Explicitly setting tenant_id to null (vacating)
        if tenant_id_updated and new_tenant_id is None:
            unit_to_update.is_rented = False  # Vacant units are not rented
            if not rent_explicitly_set:  # Clear rent only if not explicitly set in this request
                unit_to_update.monthly_rent = None

        # Scenario 2: Explicitly assigning a tenant (making rented)
        elif tenant_id_updated and new_tenant_id is not None:
            unit_to_update.is_rented = True  # Assigning a tenant implies rented

        try:
            session.add(unit_to_update)
            await session.commit()

            # Re-fetch with tenant loaded for response
            query = (
                select(PropertyUnit)
                .options(selectinload(getattr(PropertyUnit, "tenant")))
                .where(col(PropertyUnit.id) == unit_id)
            )
            result = await session.execute(query)
            final_unit = result.unique().scalar_one_or_none()

            if not final_unit:
                logger.error(f"Failed to re-fetch unit {unit_id} after update.")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Updated unit could not be found.")

            logger.info(
                f"Unit {final_unit.id} updated successfully by user {current_user.id}")
            return UnitResponse.model_validate(final_unit)

        except ValidationError as e:
            logger.error(
                f"Response validation error for unit {unit_id}: {e.errors()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unit updated, but failed to serialize response: {e.errors()}"
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating unit {unit_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while updating the unit: {str(e)}"
            )

    @staticmethod
    async def delete_unit(
        unit_id: int,
        session: AsyncSession,
        current_user: User
    ) -> None:
        """
        Deletes a property unit after verifying permissions and ensuring no active leases exist.

        Raises:
            HTTPException: If the unit has an active lease (400) or if an error occurs during deletion (500).
        """
        # get_unit_or_404 already performs the ownership check
        unit_to_delete = await UnitService.get_unit_or_404(unit_id, session, current_user)

        # Add check for active leases associated with the unit
        active_lease_query = select(col(Lease.id)).where(
            and_(col(Lease.unit_id) == unit_id, col(
                Lease.status) == LeaseStatus.ACTIVE)
        ).limit(1)
        active_lease_exists = await session.scalar(active_lease_query)
        if active_lease_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Cannot delete unit with an active lease.")

        await session.delete(unit_to_delete)
        try:
            await session.commit()
            logger.info(
                f"Unit {unit_id} deleted successfully by user {current_user.id}")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error deleting unit {unit_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while deleting the unit."
            )

    @staticmethod
    async def get_unit(
        unit_id: int,
        session: AsyncSession,
        current_user: User
    ) -> UnitResponse:
        """
        Retrieves a single unit by its ID, ensuring the user has permission.
        """
        # The helper function performs the fetch, permission check, and eager loads the tenant.
        unit = await UnitService.get_unit_or_404(unit_id, session, current_user)
        return UnitResponse.model_validate(unit)

    @staticmethod
    async def get_units_for_property(
        property_id: int,
        session: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[UnitResponse]:
        """
        Retrieves all units for a specified property, ensuring the user has permission to access them.

        Checks that the property exists and that the current user is either an admin or the owner of the property. Returns a list of units for the property, including tenant information, ordered by unit name.
        """
        # Check if property exists and user has permission
        result = await session.execute(select(Property).where(col(Property.id) == property_id))
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

        # Permission check using user_id
        if not current_user.is_admin and property_obj.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view units for this property"
            )

        # Retrieve units for the property, explicitly loading tenant info
        result = await session.execute(
            select(PropertyUnit)
            .options(
                selectinload(getattr(PropertyUnit, "tenant")),
            )
            .where(col(PropertyUnit.property_id) == property_id)
            .order_by(col(PropertyUnit.id))  # Order by ID to maintain creation order
            .offset(skip)
            .limit(limit)
        )
        units = result.unique().scalars().all()

        # Convert ORM objects to Pydantic response models
        return [UnitResponse.model_validate(unit) for unit in units]

    @staticmethod
    async def create_units_bulk(
        property_id: int,
        bulk_data: BulkUnitCreate,
        session: AsyncSession,
        current_user: User
    ) -> BulkUnitCreateResponse:
        """Create multiple units for a property in a single transaction."""
        # Check if property exists and user has permission
        result = await session.execute(select(Property).where(col(Property.id) == property_id))
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")

        # Permission check using user_id
        if not current_user.is_admin and property_obj.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to add units to this property"
            )

        created_units = []
        failed_units = []

        # Process each unit
        for idx, unit_data in enumerate(bulk_data.units):
            try:
                # Create the new unit
                new_unit = PropertyUnit(
                    **unit_data.model_dump(),
                    property_id=property_id
                )
                session.add(new_unit)
                await session.flush()  # Flush to get the ID without committing
                created_units.append(UnitCreateResponse.model_validate(new_unit))
            except ValidationError as e:
                failed_units.append({
                    "index": idx,
                    "data": unit_data.model_dump(),
                    "error": str(e)
                })
                logger.error(f"Failed to create unit at index {idx}: {e}")
            except Exception as e:
                failed_units.append({
                    "index": idx,
                    "data": unit_data.model_dump(),
                    "error": str(e)
                })
                logger.error(f"Unexpected error creating unit at index {idx}: {e}")

        # Commit all successful units
        if created_units:
            try:
                await session.commit()
                logger.info(
                    f"Bulk created {len(created_units)} units for property {property_id} by user {current_user.id}"
                )
            except Exception as e:
                await session.rollback()
                logger.error(f"Failed to commit bulk unit creation: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save units to database"
                )

        return BulkUnitCreateResponse(
            created=created_units,
            failed=failed_units
        )

    @staticmethod
    async def search_units(
        filters: UnitSearchFilters,
        session: AsyncSession,
        current_user: User,
        skip: int = 0,
        limit: int = 100
    ) -> List[UnitResponse]:
        """
        Search for units across all properties owned by the user.
        
        Applies various filters to find units matching the criteria.
        Admin users can search across all properties.
        """
        # Base query
        query = (
            select(PropertyUnit)
            .join(Property)
            .options(
                selectinload(getattr(PropertyUnit, "tenant")),
                joinedload(getattr(PropertyUnit, "property"))
            )
        )
        
        # Apply ownership filter for non-admin users
        if not current_user.is_admin:
            query = query.where(col(Property.user_id) == current_user.id)
        
        # Apply property filter if specified
        if filters.property_ids:
            query = query.where(col(PropertyUnit.property_id).in_(filters.property_ids))
        
        # Apply rent filters
        if filters.min_rent is not None:
            query = query.where(col(PropertyUnit.monthly_rent) >= filters.min_rent)
        if filters.max_rent is not None:
            query = query.where(col(PropertyUnit.monthly_rent) <= filters.max_rent)
        
        # Apply bedroom filters
        if filters.min_bedrooms is not None:
            query = query.where(col(PropertyUnit.bedrooms) >= filters.min_bedrooms)
        if filters.max_bedrooms is not None:
            query = query.where(col(PropertyUnit.bedrooms) <= filters.max_bedrooms)
        
        # Apply bathroom filter
        if filters.min_bathrooms is not None:
            query = query.where(col(PropertyUnit.bathrooms) >= filters.min_bathrooms)
        
        # Apply rental status filter
        if filters.is_rented is not None:
            query = query.where(col(PropertyUnit.is_rented) == filters.is_rented)
        
        # Apply ordering and pagination
        # Use NULLS LAST to ensure consistent ordering when monthly_rent is null
        query = query.order_by(nulls_last(col(PropertyUnit.monthly_rent)), PropertyUnit.name)
        query = query.offset(skip).limit(limit)
        
        # Execute query
        result = await session.execute(query)
        units = result.unique().scalars().all()
        
        # Convert to response models
        return [UnitResponse.model_validate(unit) for unit in units]
    
    @staticmethod
    async def get_unit_lease(
        unit_id: int,
        session: AsyncSession,
        current_user: User
    ) -> LeaseResponse:
        """
        Get the active lease for a unit.
        
        Retrieves the currently active lease associated with the specified unit.
        Ensures the user has permission to access the unit and its lease information.
        """
        # First verify the unit exists and user has permission
        unit = await UnitService.get_unit_or_404(unit_id, session, current_user)
        
        # Query for active lease
        result = await session.execute(
            select(Lease)
            .options(
                joinedload(getattr(Lease, "tenant")),
                joinedload(getattr(Lease, "property"))
            )
            .where(
                and_(
                    col(Lease.unit_id) == unit_id,
                    col(Lease.status) == LeaseStatus.ACTIVE
                )
            )
        )
        lease = result.unique().scalar_one_or_none()
        
        if not lease:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active lease found for this unit"
            )
        
        return LeaseResponse.model_validate(lease)