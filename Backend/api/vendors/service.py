"""
Vendor Service - Normalized Design

Business logic for vendor management with join table support.
Handles vendor creation with deduplication and user-vendor association management.
"""
import logging
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import col

from Backend.models.user import User
from Backend.models.vendor import Vendor, UserVendor
from .schemas import VendorContactCreate, VendorContactUpdate

logger = logging.getLogger(__name__)


class VendorService:
    """Service class for vendor contact operations"""

    @staticmethod
    async def _find_or_create_vendor(
        data: VendorContactCreate,
        session: AsyncSession
    ) -> Vendor:
        """
        Find existing vendor or create new one (deduplication logic).
        
        Checks if a vendor with the same phone number already exists.
        Phone is used as the unique identifier since it's the most reliable contact method.
        """
        # Check if vendor exists by phone (primary dedup key)
        result = await session.execute(
            select(Vendor).where(col(Vendor.phone) == data.phone)
        )
        existing_vendor = result.scalar_one_or_none()
        
        if existing_vendor:
            # Vendor exists - return it without modifying
            # The central vendor record should not be modified when other users
            # add the same vendor by phone number. This prevents data conflicts.
            # User-specific notes can be stored in the UserVendor association.
            return existing_vendor
        
        # Create new vendor
        new_vendor = Vendor(
            company_name=data.company_name,
            contact_person=data.contact_person,
            trade_category=data.trade_category,
            phone=data.phone,
            email=data.email,
        )
        session.add(new_vendor)
        await session.flush()  # Get ID without committing
        return new_vendor

    @staticmethod
    async def create_vendor(
        data: VendorContactCreate,
        current_user: User,
        session: AsyncSession
    ) -> Tuple[Vendor, UserVendor]:
        """
        Create or find vendor and associate it with the current user.
        
        This method:
        1. Finds existing vendor by phone or creates new one
        2. Creates user-vendor association with user-specific data
        3. Returns both vendor and association

        Args:
            data: Vendor creation data
            current_user: The authenticated user
            session: Database session

        Returns:
            Tuple of (Vendor, UserVendor)

        Raises:
            HTTPException: If creation fails or association already exists
        """
        try:
            # Find or create vendor
            vendor = await VendorService._find_or_create_vendor(data, session)
            
            # Check if user already has this vendor
            result = await session.execute(
                select(UserVendor).where(
                    and_(
                        col(UserVendor.user_id) == current_user.id,
                        col(UserVendor.vendor_id) == vendor.id
                    )
                )
            )
            existing_association = result.scalar_one_or_none()
            
            if existing_association:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"You already have {vendor.company_name} in your contacts"
                )
            
            # Create user-vendor association
            user_vendor = UserVendor(
                user_id=current_user.id,
                vendor_id=vendor.id,
                notes=data.notes,
                is_active=data.is_active,
            )
            session.add(user_vendor)
            await session.commit()
            
            # Refresh to load relationships
            await session.refresh(user_vendor)
            await session.refresh(vendor)

            logger.info(f"Associated vendor {vendor.id} with user {current_user.id}")
            return vendor, user_vendor

        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.exception(f"Failed to create vendor for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create vendor: {str(e)}"
            )

    @staticmethod
    async def get_vendor(
        vendor_id: int,
        current_user: User,
        session: AsyncSession
    ) -> Tuple[Vendor, UserVendor]:
        """
        Get a vendor by ID with user's association data.

        Args:
            vendor_id: ID of the vendor to retrieve
            current_user: The authenticated user
            session: Database session

        Returns:
            Tuple of (Vendor, UserVendor)

        Raises:
            HTTPException: If vendor not found or user doesn't have association
        """
        # Query through join table to ensure user has access
        result = await session.execute(
            select(UserVendor)
            .options(selectinload(getattr(UserVendor, "vendor")))
            .where(col(UserVendor.vendor_id) == vendor_id)
            .where(col(UserVendor.user_id) == current_user.id)
        )
        user_vendor = result.scalar_one_or_none()

        if not user_vendor or not user_vendor.vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor with ID {vendor_id} not found in your contacts"
            )

        return user_vendor.vendor, user_vendor

    @staticmethod
    async def list_vendors(
        current_user: User,
        session: AsyncSession,
        trade_category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[list[Tuple[Vendor, UserVendor]], int]:
        """
        List vendors for the current user with optional filters.
        
        Queries through the join table to get user's vendors with their association data.

        Args:
            current_user: The authenticated user
            session: Database session
            trade_category: Filter by trade category
            is_active: Filter by user's active status for vendor
            search: Search in company_name and contact_person
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of (Vendor, UserVendor) tuples, total count)
        """
        # Build query through join table with vendor eager-loaded
        query = (
            select(UserVendor)
            .options(selectinload(getattr(UserVendor, "vendor")))
            .join(Vendor, col(UserVendor.vendor_id) == col(Vendor.id))
            .where(col(UserVendor.user_id) == current_user.id)
        )

        # Apply filters
        if trade_category:
            query = query.where(col(Vendor.trade_category) == trade_category)

        if is_active is not None:
            query = query.where(col(UserVendor.is_active) == is_active)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    col(Vendor.company_name).ilike(search_pattern),
                    col(Vendor.contact_person).ilike(search_pattern)
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination and ordering (order by vendor company name)
        query = query.order_by(col(Vendor.company_name).asc())
        query = query.limit(limit).offset(offset)

        result = await session.execute(query)
        user_vendors = result.scalars().all()

        # Return list of (Vendor, UserVendor) tuples
        vendor_list = [(uv.vendor, uv) for uv in user_vendors if uv.vendor]

        return vendor_list, total

    @staticmethod
    async def update_vendor(
        vendor_id: int,
        data: VendorContactUpdate,
        current_user: User,
        session: AsyncSession
    ) -> Tuple[Vendor, UserVendor]:
        """
        Update user's association with a vendor (notes, active status, etc.).
        
        NOTE: This updates the user_vendors join table, NOT the central vendor.
        Central vendor updates would require admin/platform privileges.

        Args:
            vendor_id: ID of the vendor
            data: Update data (notes, is_active, etc.)
            current_user: The authenticated user
            session: Database session

        Returns:
            Tuple of (Vendor, UserVendor)

        Raises:
            HTTPException: If vendor not found or update fails
        """
        vendor, user_vendor = await VendorService.get_vendor(vendor_id, current_user, session)

        try:
            # Update only user-specific fields in the join table
            update_data = data.model_dump(exclude_unset=True)
            
            # Only update fields that exist in UserVendor model
            user_vendor_fields = {'notes', 'is_active', 'is_favorite', 'personal_rating'}
            for field, value in update_data.items():
                if field in user_vendor_fields:
                    setattr(user_vendor, field, value)

            await session.commit()
            await session.refresh(user_vendor)
            await session.refresh(vendor)

            logger.info(f"Updated user-vendor association for vendor {vendor_id}, user {current_user.id}")
            return vendor, user_vendor

        except Exception as e:
            await session.rollback()
            logger.exception(f"Failed to update vendor {vendor_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update vendor: {str(e)}"
            )

    @staticmethod
    async def delete_vendor(
        vendor_id: int,
        current_user: User,
        session: AsyncSession
    ) -> None:
        """
        Remove vendor from user's contacts (delete user-vendor association).
        
        NOTE: This removes the association, NOT the vendor itself.
        The vendor remains in the central table for other users.

        Args:
            vendor_id: ID of the vendor to remove
            current_user: The authenticated user
            session: Database session

        Raises:
            HTTPException: If vendor not found or delete fails
        """
        vendor, user_vendor = await VendorService.get_vendor(vendor_id, current_user, session)

        try:
            # Delete the user-vendor association only
            await session.delete(user_vendor)
            await session.commit()

            logger.info(f"Removed vendor {vendor_id} from user {current_user.id}'s contacts")

        except Exception as e:
            await session.rollback()
            logger.exception(f"Failed to delete vendor association {vendor_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete vendor: {str(e)}"
            )

    @staticmethod
    async def bulk_delete_vendors(
        vendor_ids: list[int],
        current_user: User,
        session: AsyncSession
    ) -> int:
        """
        Remove multiple vendors from user's contacts (bulk delete associations).

        Args:
            vendor_ids: List of vendor IDs to remove
            current_user: The authenticated user
            session: Database session

        Returns:
            Number of associations deleted

        Raises:
            HTTPException: If delete fails
        """
        try:
            # Delete all associations in a single query
            delete_stmt = (
                delete(UserVendor)
                .where(col(UserVendor.user_id) == current_user.id)
                .where(col(UserVendor.vendor_id).in_(vendor_ids))
            )
            result = await session.execute(delete_stmt)
            count = result.rowcount
            
            if count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No vendors found to delete"
                )

            await session.commit()

            logger.info(f"Bulk deleted {count} vendor associations for user {current_user.id}")
            return count

        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            logger.exception(f"Failed to bulk delete vendors")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to bulk delete vendors: {str(e)}"
            )

    @staticmethod
    async def get_trade_categories(
        current_user: User,
        session: AsyncSession
    ) -> list[str]:
        """
        Get list of unique trade categories from user's vendors.

        Args:
            current_user: The authenticated user
            session: Database session

        Returns:
            List of unique trade categories
        """
        result = await session.execute(
            select(col(Vendor.trade_category))
            .join(UserVendor)
            .where(col(UserVendor.user_id) == current_user.id)
            .distinct()
            .order_by(col(Vendor.trade_category))
        )
        categories = result.scalars().all()
        return list(categories)

