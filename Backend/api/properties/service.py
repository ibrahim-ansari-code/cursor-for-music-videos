import logging
from uuid import UUID as PythonUUID

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col

from Backend.api.units import TenantInfo
from Backend.models.enums import PropertyStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyUnit, PropertyType
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime

from .schemas import (
    OwnerResponse,
    PropertyCreate,
    PropertyDetailResponse_Standalone,
    PropertyUpdate,
    UnitResponse,
)

logger = logging.getLogger(__name__)


class PropertyService:
    @staticmethod
    def _derive_property_status(property_obj: Property) -> PropertyStatus:
        """Derives property status based on unit occupancy."""
        # Default to the property's stored status, or ACTIVE if not set.
        current_status = property_obj.status or PropertyStatus.ACTIVE

        if not property_obj.units:
            return current_status

        occupied_units_count = sum(1 for unit in property_obj.units if unit.is_rented)
        total_units = len(property_obj.units)

        if total_units > 0:
            if occupied_units_count == 0:
                return PropertyStatus.VACANT
            elif occupied_units_count == total_units:
                return PropertyStatus.RENTED
            else:  # This covers occupied_units_count > 0 and < total_units
                return PropertyStatus.PARTIALLY_RENTED

        return current_status

    @staticmethod
    async def get_property(
        property_id: int, current_user: User, session: AsyncSession
    ) -> PropertyDetailResponse_Standalone:
        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                selectinload(getattr(Property, "units")).options(
                    selectinload(getattr(PropertyUnit, "tenant"))
                ),
            )
            .where(col(Property.id) == property_id)
        )
        result = await session.execute(query)
        property_orm = result.unique().scalar_one_or_none()

        if not property_orm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
            )

        if property_orm.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this property",
            )

        response_status = PropertyService._derive_property_status(property_orm)

        serialized_units_models = []
        if property_orm.units:
            for unit in property_orm.units:
                try:
                    unit_model = UnitResponse.model_validate(unit)
                    if unit.tenant:
                        try:
                            tenant_info_model = TenantInfo.model_validate(unit.tenant)
                            unit_model.tenant = tenant_info_model
                        except Exception as tenant_e:
                            logger.error(
                                f"Error serializing tenant for unit {unit.id}: {tenant_e}"
                            )
                            unit_model.tenant = None
                    serialized_units_models.append(unit_model)
                except Exception as e:
                    logger.error(f"Error serializing unit {unit.id}: {e}")
                    continue

        if property_orm.id is None:
            logger.error("Property ID is None after database fetch.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Critical error: Property ID missing after retrieval.",
            )

        response = PropertyDetailResponse_Standalone(
            id=property_orm.id,
            name=property_orm.name,
            address=property_orm.address,
            city=property_orm.city,
            province=property_orm.province,
            postal_code=property_orm.postal_code,
            property_type=PropertyType(property_orm.property_type),
            description=property_orm.description,
            year_built=property_orm.year_built,
            status=response_status,
            user_id=property_orm.user_id,
            created_at=property_orm.created_at,
            updated_at=property_orm.updated_at,
            owner=(
                OwnerResponse.model_validate(property_orm.owner)
                if property_orm.owner
                else None
            ),
            units=serialized_units_models,
        )
        return response

    @staticmethod
    async def get_properties(
        current_user: User,
        session: AsyncSession,
        status_filter: PropertyStatus | None,
        property_type: str | None,
        owner_id: PythonUUID | None,
    ) -> list[Property]:
        query = select(Property)
        if status_filter:
            query = query.where(col(Property.status) == status_filter)
        if property_type:
            query = query.where(col(Property.property_type) == property_type)
        if not current_user.is_admin:
            query = query.where(col(Property.user_id) == current_user.id)
        elif owner_id:
            query = query.where(col(Property.user_id) == owner_id)

        result = await session.execute(query)
        properties = result.scalars().all()

        for prop in properties:
            if prop.status is None:
                prop.status = PropertyStatus.ACTIVE

        return list(properties)

    @staticmethod
    async def create_property(
        property_data: PropertyCreate, current_user: User, session: AsyncSession
    ) -> PropertyDetailResponse_Standalone:
        new_property = Property(
            name=property_data.name,
            address=property_data.address,
            city=property_data.city,
            province=property_data.province,
            postal_code=property_data.postal_code,
            property_type=property_data.property_type,
            description=property_data.description,
            year_built=property_data.year_built,
            status=property_data.status or PropertyStatus.ACTIVE,
            user_id=current_user.id,
            created_at=create_audit_datetime(),
            updated_at=create_audit_datetime(),
        )
        session.add(new_property)

        if property_data.units:
            now = create_audit_datetime()
            for unit_name in property_data.units:
                floor = 0
                if unit_name and unit_name[0].isdigit():
                    try:
                        floor = int(unit_name[0])
                    except ValueError:
                        pass
                new_unit = PropertyUnit(
                    property=new_property,
                    name=unit_name,
                    floor=floor,
                    is_rented=False,
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_unit)

        await session.commit()
        await session.refresh(new_property)
        property_id = new_property.id

        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                joinedload(getattr(Property, "units")),
            )
            .where(col(Property.id) == property_id)
        )
        result = await session.execute(query)
        loaded_property = result.unique().scalar_one_or_none()

        if not loaded_property:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Property was created but could not be retrieved",
            )

        # Apply status derivation logic
        response_status = PropertyService._derive_property_status(loaded_property)
        
        # Serialize units with tenant info
        serialized_units = []
        if loaded_property.units:
            for unit in loaded_property.units:
                try:
                    unit_model = UnitResponse.model_validate(unit)
                    if unit.tenant:
                        try:
                            tenant_info = TenantInfo.model_validate(unit.tenant)
                            unit_model.tenant = tenant_info
                        except Exception as e:
                            logger.error(f"Error serializing tenant for unit {unit.id}: {e}")
                            unit_model.tenant = None
                    serialized_units.append(unit_model)
                except Exception as e:
                    logger.error(f"Error serializing unit {unit.id}: {e}")
                    continue
        
        # Ensure ID is not None
        if loaded_property.id is None:
            logger.error("Property ID is None after database creation.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Critical error: Property ID missing after creation.",
            )
        
        # Type assertion for the linter
        property_id_not_none: int = loaded_property.id
        
        # Construct response with derived status
        response = PropertyDetailResponse_Standalone(
            id=property_id_not_none,
            name=loaded_property.name,
            address=loaded_property.address,
            city=loaded_property.city,
            province=loaded_property.province,
            postal_code=loaded_property.postal_code,
            property_type=PropertyType(loaded_property.property_type),
            description=loaded_property.description,
            year_built=loaded_property.year_built,
            status=response_status,
            user_id=loaded_property.user_id,
            created_at=loaded_property.created_at,
            updated_at=loaded_property.updated_at,
            owner=(
                OwnerResponse.model_validate(loaded_property.owner)
                if loaded_property.owner
                else None
            ),
            units=serialized_units,
        )
        return response

    @staticmethod
    async def update_property(
        property_id: int,
        property_data: PropertyUpdate,
        current_user: User,
        session: AsyncSession,
    ) -> PropertyDetailResponse_Standalone:
        result = await session.execute(
            select(Property).where(col(Property.id) == property_id)
        )
        property_to_update = result.scalar_one_or_none()

        if not property_to_update:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
            )

        if property_to_update.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this property",
            )

        update_data = property_data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided",
            )

        for key, value in update_data.items():
            if value is not None:
                setattr(property_to_update, key, value)
        property_to_update.updated_at = create_audit_datetime()

        session.add(property_to_update)
        await session.commit()
        await session.refresh(property_to_update)

        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                selectinload(getattr(Property, "units")).options(
                    selectinload(getattr(PropertyUnit, "tenant"))
                ),
            )
            .where(col(Property.id) == property_id)
        )
        result = await session.execute(query)
        updated_property_orm = result.unique().scalar_one_or_none()

        if not updated_property_orm:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Property updated but could not be re-retrieved",
            )

        response_status = PropertyService._derive_property_status(updated_property_orm)
        serialized_units = []
        if updated_property_orm.units:
            for unit in updated_property_orm.units:
                unit_model = UnitResponse.model_validate(unit)
                if unit.tenant:
                    try:
                        tenant_info = TenantInfo.model_validate(unit.tenant)
                        unit_model.tenant = tenant_info
                    except Exception as e:
                        logger.error(
                            f"Tenant serialization error in update response: {e}"
                        )
                        unit_model.tenant = None
                else:
                    unit_model.tenant = None
                serialized_units.append(unit_model)

        if updated_property_orm.id is None:
            logger.error("Property ID is None after database update.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Critical error: Property ID missing after update.",
            )

        response = PropertyDetailResponse_Standalone(
            id=updated_property_orm.id,
            name=updated_property_orm.name,
            address=updated_property_orm.address,
            city=updated_property_orm.city,
            province=updated_property_orm.province,
            postal_code=updated_property_orm.postal_code,
            property_type=PropertyType(updated_property_orm.property_type),
            description=updated_property_orm.description,
            year_built=updated_property_orm.year_built,
            status=response_status,
            user_id=updated_property_orm.user_id,
            created_at=updated_property_orm.created_at,
            updated_at=updated_property_orm.updated_at,
            owner=(
                OwnerResponse.model_validate(updated_property_orm.owner)
                if updated_property_orm.owner
                else None
            ),
            units=serialized_units,
        )
        return response

    @staticmethod
    async def delete_property(
        property_id: int, current_user: User, session: AsyncSession
    ) -> None:
        query = select(Property).where(col(Property.id) == property_id)
        result = await session.execute(query)
        property_to_delete = result.scalar_one_or_none()

        if not property_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
            )

        if property_to_delete.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this property",
            )

        active_leases_query = select(Lease).where(
            and_(
                col(Lease.property_id) == property_id,
                col(Lease.status).in_([LeaseStatus.ACTIVE, LeaseStatus.PENDING]),
            )
        )
        active_leases_result = await session.execute(active_leases_query)
        active_leases = active_leases_result.scalars().all()

        if active_leases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete property with active leases",
            )

        await session.delete(property_to_delete)
        await session.commit() 
