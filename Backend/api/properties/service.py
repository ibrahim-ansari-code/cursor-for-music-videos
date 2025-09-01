import logging
from typing import Any
from uuid import UUID as PythonUUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import col

from Backend.api.units.schemas import TenantInfo
from Backend.models.enums import PropertyStatus
from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property, PropertyType
from Backend.models.units import PropertyUnit
from Backend.models.property_types.apartment_complex import PropertyApartmentComplex
from Backend.models.property_types.commercial import PropertyCommercial
from Backend.models.property_types.residential import PropertyResidential
from Backend.models.property_types.industrial import PropertyIndustrial
from Backend.models.property_types.mixed_use import PropertyMixedUse
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime

from decimal import Decimal, InvalidOperation

from .schemas import (
    OwnerResponse,
    PropertyCreate,
    PropertyDetailResponse,
    PropertyImageResponse,
    PropertyStats,
    PropertyUpdate,
    UnitResponse,
    # Type-specific schemas
    ApartmentComplexPropertyDetailsCreate,
    ApartmentComplexPropertyDetailsUpdate,
    CommercialPropertyDetailsCreate,
    CommercialPropertyDetailsUpdate,
    ResidentialPropertyDetailsCreate,
    ResidentialPropertyDetailsUpdate,
    IndustrialPropertyDetailsCreate,
    IndustrialPropertyDetailsUpdate,
    MixedUsePropertyDetailsCreate,
    MixedUsePropertyDetailsUpdate,
)

logger = logging.getLogger(__name__)


class PropertyService:
    @staticmethod
    def calculate_property_stats(units: list[PropertyUnit]) -> PropertyStats:
        """Calculate statistics for a property based on its units."""
        total_units = len(units)
        vacant_units = sum(1 for unit in units if not unit.is_rented)
        occupied_units = total_units - vacant_units
        
        # Calculate monthly revenue with error handling for invalid data
        monthly_revenue = Decimal("0.00")
        for unit in units:
            if unit.is_rented and unit.monthly_rent:
                try:
                    monthly_revenue += Decimal(str(unit.monthly_rent))
                except (TypeError, ValueError, InvalidOperation) as e:
                    logger.warning(f"Invalid monthly_rent value for unit {getattr(unit, 'id', 'unknown')}: {unit.monthly_rent}")
                    continue
        
        occupancy_rate = (occupied_units / total_units * 100) if total_units > 0 else 0.0
        
        return PropertyStats(
            total_units=total_units,
            vacant_units=vacant_units,
            occupied_units=occupied_units,
            monthly_revenue=monthly_revenue,
            occupancy_rate=occupancy_rate
        )
    
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
    async def _create_type_specific_details(
        property_id: int,
        property_type: PropertyType,
        details: ApartmentComplexPropertyDetailsCreate | CommercialPropertyDetailsCreate | ResidentialPropertyDetailsCreate | IndustrialPropertyDetailsCreate | MixedUsePropertyDetailsCreate,
        session: AsyncSession
    ) -> None:
        """Create type-specific property details based on property type."""
        if property_type == PropertyType.APARTMENT_COMPLEX and isinstance(details, ApartmentComplexPropertyDetailsCreate):
            apartment_complex = PropertyApartmentComplex(
                property_id=property_id,
                **details.model_dump(exclude_unset=True)
            )
            session.add(apartment_complex)
        elif property_type == PropertyType.COMMERCIAL and isinstance(details, CommercialPropertyDetailsCreate):
            commercial = PropertyCommercial(
                property_id=property_id,
                **details.model_dump(exclude_unset=True)
            )
            session.add(commercial)
        elif property_type == PropertyType.RESIDENTIAL and isinstance(details, ResidentialPropertyDetailsCreate):
            residential = PropertyResidential(
                property_id=property_id,
                **details.model_dump(exclude_unset=True)
            )
            session.add(residential)
        elif property_type == PropertyType.INDUSTRIAL and isinstance(details, IndustrialPropertyDetailsCreate):
            industrial = PropertyIndustrial(
                property_id=property_id,
                **details.model_dump(exclude_unset=True)
            )
            session.add(industrial)
        elif property_type == PropertyType.MIXED_USE and isinstance(details, MixedUsePropertyDetailsCreate):
            mixed_use = PropertyMixedUse(
                property_id=property_id,
                **details.model_dump(exclude_unset=True)
            )
            session.add(mixed_use)
    
    @staticmethod
    async def _get_type_specific_details(
        property_id: int,
        property_type: PropertyType,
        session: AsyncSession
    ) -> Any | None:
        """Retrieve type-specific property details based on property type."""
        from .schemas import (
            ApartmentComplexPropertyDetailsResponse,
            CommercialPropertyDetailsResponse,
            ResidentialPropertyDetailsResponse,
            IndustrialPropertyDetailsResponse,
            MixedUsePropertyDetailsResponse,
        )
        result = None
        
        if property_type == PropertyType.APARTMENT_COMPLEX:
            apt_query = select(PropertyApartmentComplex).where(
                col(PropertyApartmentComplex.property_id) == property_id
            )
            apt_result = await session.execute(apt_query)
            apt_details = apt_result.scalar_one_or_none()
            if apt_details:
                return ApartmentComplexPropertyDetailsResponse.model_validate(apt_details)
        elif property_type == PropertyType.COMMERCIAL:
            com_query = select(PropertyCommercial).where(
                col(PropertyCommercial.property_id) == property_id
            )
            com_result = await session.execute(com_query)
            com_details = com_result.scalar_one_or_none()
            if com_details:
                return CommercialPropertyDetailsResponse.model_validate(com_details)
        elif property_type == PropertyType.RESIDENTIAL:
            res_query = select(PropertyResidential).where(
                col(PropertyResidential.property_id) == property_id
            )
            res_result = await session.execute(res_query)
            res_details = res_result.scalar_one_or_none()
            if res_details:
                return ResidentialPropertyDetailsResponse.model_validate(res_details)
        elif property_type == PropertyType.INDUSTRIAL:
            ind_query = select(PropertyIndustrial).where(
                col(PropertyIndustrial.property_id) == property_id
            )
            ind_result = await session.execute(ind_query)
            ind_details = ind_result.scalar_one_or_none()
            if ind_details:
                return IndustrialPropertyDetailsResponse.model_validate(ind_details)
        elif property_type == PropertyType.MIXED_USE:
            mix_query = select(PropertyMixedUse).where(
                col(PropertyMixedUse.property_id) == property_id

            )
            mix_result = await session.execute(mix_query)
            mix_details = mix_result.scalar_one_or_none()
            if mix_details:
                return MixedUsePropertyDetailsResponse.model_validate(mix_details)
        
        return None
    
    @staticmethod
    async def _update_type_specific_details(
        property_id: int,
        property_type: PropertyType,
        details: Any,  # Will be one of the Update schemas
        session: AsyncSession
    ) -> None:
        """Update type-specific property details based on property type."""
        # Import from already imported modules
        pass
        
        if property_type == PropertyType.APARTMENT_COMPLEX and isinstance(details, ApartmentComplexPropertyDetailsUpdate):
            # Check if record exists
            apt_query = select(PropertyApartmentComplex).where(
                col(PropertyApartmentComplex.property_id) == property_id
            )
            apt_result = await session.execute(apt_query)
            apt_existing = apt_result.scalar_one_or_none()
            
            if apt_existing:
                # Update existing
                update_data = details.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(apt_existing, key, value)
                apt_existing.updated_at = create_audit_datetime()
            else:
                # Create new
                new_apt = PropertyApartmentComplex(
                    property_id=property_id,
                    **details.model_dump(exclude_unset=True)
                )
                session.add(new_apt)
                
        elif property_type == PropertyType.COMMERCIAL and isinstance(details, CommercialPropertyDetailsUpdate):
            com_query = select(PropertyCommercial).where(
                col(PropertyCommercial.property_id) == property_id
            )
            com_result = await session.execute(com_query)
            com_existing = com_result.scalar_one_or_none()
            
            if com_existing:
                update_data = details.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(com_existing, key, value)
                com_existing.updated_at = create_audit_datetime()
            else:
                new_com = PropertyCommercial(
                    property_id=property_id,
                    **details.model_dump(exclude_unset=True)
                )
                session.add(new_com)
                
        elif property_type == PropertyType.RESIDENTIAL and isinstance(details, ResidentialPropertyDetailsUpdate):
            res_query = select(PropertyResidential).where(
                col(PropertyResidential.property_id) == property_id
            )
            res_result = await session.execute(res_query)
            res_existing = res_result.scalar_one_or_none()
            
            if res_existing:
                update_data = details.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(res_existing, key, value)
                res_existing.updated_at = create_audit_datetime()
            else:
                new_res = PropertyResidential(
                    property_id=property_id,
                    **details.model_dump(exclude_unset=True)
                )
                session.add(new_res)
                
        elif property_type == PropertyType.INDUSTRIAL and isinstance(details, IndustrialPropertyDetailsUpdate):
            ind_query = select(PropertyIndustrial).where(
                col(PropertyIndustrial.property_id) == property_id
            )
            ind_result = await session.execute(ind_query)
            ind_existing = ind_result.scalar_one_or_none()
            
            if ind_existing:
                update_data = details.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(ind_existing, key, value)
                ind_existing.updated_at = create_audit_datetime()
            else:
                new_ind = PropertyIndustrial(
                    property_id=property_id,
                    **details.model_dump(exclude_unset=True)
                )
                session.add(new_ind)
                
        elif property_type == PropertyType.MIXED_USE and isinstance(details, MixedUsePropertyDetailsUpdate):
            mix_query = select(PropertyMixedUse).where(
                col(PropertyMixedUse.property_id) == property_id
            )
            mix_result = await session.execute(mix_query)
            mix_existing = mix_result.scalar_one_or_none()
            
            if mix_existing:
                update_data = details.model_dump(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(mix_existing, key, value)
                mix_existing.updated_at = create_audit_datetime()
            else:
                new_mix = PropertyMixedUse(
                    property_id=property_id,
                    **details.model_dump(exclude_unset=True)
                )
                session.add(new_mix)

    @staticmethod
    async def get_property(
        property_id: int, current_user: User, session: AsyncSession
    ) -> PropertyDetailResponse:
        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                selectinload(getattr(Property, "units")).options(
                    selectinload(getattr(PropertyUnit, "tenant"))
                ),
                selectinload(getattr(Property, "images")),
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
            # Sort units by ID to maintain consistent ordering
            sorted_units = sorted(property_orm.units, key=lambda x: x.id or 0)
            for unit in sorted_units:
                try:
                    unit_model = UnitResponse.model_validate(unit)
                    if unit.tenant:
                        try:
                            tenant_info_model = TenantInfo.model_validate(unit.tenant)
                            unit_model.tenant = tenant_info_model
                        except Exception as tenant_e:
                            logger.error(
                                f"Error serializing tenant for unit {unit.id} (tenant_id: {getattr(unit.tenant, 'id', 'unknown')}): {tenant_e}. "
                                f"Tenant data: first_name={getattr(unit.tenant, 'first_name', None)}, "
                                f"last_name={getattr(unit.tenant, 'last_name', None)}, "
                                f"company_name={getattr(unit.tenant, 'company_name', None)}, "
                                f"tenant_type={getattr(unit.tenant, 'tenant_type', None)}"
                            )
                            unit_model.tenant = None
                    serialized_units_models.append(unit_model)
                except Exception as e:
                    logger.error(
                        f"Error serializing unit {unit.id}: {e}. "
                        f"Unit data: name={getattr(unit, 'name', None)}, "
                        f"is_rented={getattr(unit, 'is_rented', None)}, "
                        f"monthly_rent={getattr(unit, 'monthly_rent', None)}, "
                        f"tenant_id={getattr(unit, 'tenant_id', None)}"
                    )
                    continue

        if property_orm.id is None:
            logger.error("Property ID is None after database fetch.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Critical error: Property ID missing after retrieval.",
            )

        # Calculate stats for the property
        stats = PropertyService.calculate_property_stats(property_orm.units)
        
        # Get type-specific details if available
        type_specific_details = await PropertyService._get_type_specific_details(
            property_id=property_orm.id,
            property_type=PropertyType(property_orm.property_type),
            session=session
        )
        
        response = PropertyDetailResponse(
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
            # Google Maps fields
            latitude=property_orm.latitude,
            longitude=property_orm.longitude,
            place_id=property_orm.place_id,
            formatted_address=property_orm.formatted_address,
            google_maps_data=property_orm.google_maps_data,
            # Property details
            property_details=property_orm.property_details,
            type_specific_details=type_specific_details,
            user_id=property_orm.user_id,
            created_at=property_orm.created_at,
            updated_at=property_orm.updated_at,
            owner=(
                OwnerResponse.model_validate(property_orm.owner)
                if property_orm.owner
                else None
            ),
            units=serialized_units_models,
            stats=stats,
            images=[PropertyImageResponse.model_validate(img) for img in property_orm.images] if property_orm.images else [],
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
        from sqlalchemy.orm import selectinload
        
        query = select(Property).options(selectinload(getattr(Property, "images")))
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
    ) -> PropertyDetailResponse:
        # Validate type-specific details before creating property
        if property_data.type_specific_details:
            try:
                # Map property type to its corresponding schema class for validation
                # The type_specific_details is already validated by Pydantic union at this point
                # We re-validate here to catch custom validation errors with proper messages
                details_dict = property_data.type_specific_details.model_dump()
                
                if property_data.property_type == PropertyType.APARTMENT_COMPLEX:
                    ApartmentComplexPropertyDetailsCreate.model_validate(details_dict)
                elif property_data.property_type == PropertyType.COMMERCIAL:
                    CommercialPropertyDetailsCreate.model_validate(details_dict)
                elif property_data.property_type == PropertyType.RESIDENTIAL:
                    ResidentialPropertyDetailsCreate.model_validate(details_dict)
                elif property_data.property_type == PropertyType.INDUSTRIAL:
                    IndustrialPropertyDetailsCreate.model_validate(details_dict)
                elif property_data.property_type == PropertyType.MIXED_USE:
                    MixedUsePropertyDetailsCreate.model_validate(details_dict)
                    
            except (ValueError, ValidationError) as e:
                # Convert validation error to HTTP 422
                error_message = str(e)
                if isinstance(e, ValidationError):
                    # Extract validation errors for better error messages
                    errors = e.errors()
                    if errors:
                        # Get the first error and format it properly
                        first_error = errors[0]
                        field_path = ".".join(str(loc) for loc in first_error.get('loc', []))
                        msg = first_error.get('msg', '')
                        
                        # Check for specific error types
                        if first_error.get('type') == 'missing':
                            error_message = f"Missing required field: {field_path}"
                        elif 'assertion_error' in first_error.get('type', ''):
                            # This is from our custom validators
                            error_message = msg
                        else:
                            error_message = f"{field_path}: {msg}" if field_path else msg
                            
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=error_message
                )
            except Exception as e:
                logger.error(f"Validation error for type-specific details: {e}")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid type-specific details: {str(e)}"
                )
        
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
            # Google Maps fields
            latitude=property_data.latitude,
            longitude=property_data.longitude,
            place_id=property_data.place_id,
            formatted_address=property_data.formatted_address,
            google_maps_data=property_data.google_maps_data,
            # Property details JSONB
            property_details=property_data.property_details,
            user_id=current_user.id,
            created_at=create_audit_datetime(),
            updated_at=create_audit_datetime(),
        )
        session.add(new_property)

        # Flush to get property ID without committing transaction
        await session.flush()
        property_id = new_property.id
        
        # Create type-specific property details before commit for atomicity
        if property_data.type_specific_details and property_id:
            await PropertyService._create_type_specific_details(
                property_id=property_id,
                property_type=property_data.property_type,
                details=property_data.type_specific_details,
                session=session
            )

        # Create units - prioritize detailed_units over simple units
        now = create_audit_datetime()
        
        if property_data.detailed_units:
            # Create detailed units with all specifications
            for unit_data in property_data.detailed_units:
                new_unit = PropertyUnit(
                    property=new_property,
                    name=unit_data.name,
                    description=unit_data.description,
                    size=unit_data.size,
                    monthly_rent=unit_data.monthly_rent,
                    bedrooms=unit_data.bedrooms,
                    bathrooms=unit_data.bathrooms,
                    floor=unit_data.floor,
                    is_rented=unit_data.is_rented,
                    created_at=now,
                    updated_at=now,
                )
                session.add(new_unit)
        elif property_data.units:
            # Legacy support: create basic units from names only
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

        # Single atomic commit for all related data
        await session.commit()
        await session.refresh(new_property)

        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                joinedload(getattr(Property, "units")),
                selectinload(getattr(Property, "images")),
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
            # Sort units by ID to maintain consistent ordering
            sorted_units = sorted(loaded_property.units, key=lambda x: x.id or 0)
            for unit in sorted_units:
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
        
        # Calculate stats for the property
        stats = PropertyService.calculate_property_stats(loaded_property.units)
        
        # Get type-specific details if they were created
        type_specific_details = None
        if property_data.type_specific_details:
            type_specific_details = await PropertyService._get_type_specific_details(
                property_id=property_id_not_none,
                property_type=PropertyType(loaded_property.property_type),
                session=session
            )
        
        # Construct response with derived status
        response = PropertyDetailResponse(
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
            # Google Maps fields
            latitude=loaded_property.latitude,
            longitude=loaded_property.longitude,
            place_id=loaded_property.place_id,
            formatted_address=loaded_property.formatted_address,
            google_maps_data=loaded_property.google_maps_data,
            # Property details
            property_details=loaded_property.property_details,
            type_specific_details=type_specific_details,
            user_id=loaded_property.user_id,
            created_at=loaded_property.created_at,
            updated_at=loaded_property.updated_at,
            owner=(
                OwnerResponse.model_validate(loaded_property.owner)
                if loaded_property.owner
                else None
            ),
            units=serialized_units,
            stats=stats,
            images=[PropertyImageResponse.model_validate(img) for img in loaded_property.images] if loaded_property.images else [],
        )
        return response

    @staticmethod
    async def update_property(
        property_id: int,
        property_data: PropertyUpdate,
        current_user: User,
        session: AsyncSession,
    ) -> PropertyDetailResponse:
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

        update_data = property_data.model_dump(exclude_unset=True, exclude={'type_specific_details'})
        if not update_data and not property_data.type_specific_details:
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
        
        # Update type-specific details if provided
        if property_data.type_specific_details:
            await PropertyService._update_type_specific_details(
                property_id=property_id,
                property_type=PropertyType(property_to_update.property_type),
                details=property_data.type_specific_details,
                session=session
            )
            await session.commit()

        query = (
            select(Property)
            .options(
                joinedload(getattr(Property, "owner")),
                selectinload(getattr(Property, "units")).options(
                    selectinload(getattr(PropertyUnit, "tenant"))
                ),
                selectinload(getattr(Property, "images")),
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
            # Sort units by ID to maintain consistent ordering
            sorted_units = sorted(updated_property_orm.units, key=lambda x: x.id or 0)
            for unit in sorted_units:
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

        # Calculate stats for the property
        stats = PropertyService.calculate_property_stats(updated_property_orm.units)

        response = PropertyDetailResponse(
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
            stats=stats,
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
