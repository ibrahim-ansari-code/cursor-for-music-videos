"""
Ownership Entity Service Layer

Handles business logic for ownership entity CRUD operations.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col
from fastapi import HTTPException, status

from Backend.models.ownership_entity import OwnershipEntity
from Backend.api.ownership_entities.schemas import (
    OwnershipEntityCreate,
    OwnershipEntityUpdate,
    OwnershipEntityWithStats
)


async def get_ownership_entity(
    session: AsyncSession,
    entity_id: UUID,
    user_id: UUID
) -> OwnershipEntity:
    """
    Get a single ownership entity by ID.

    Args:
        session: Database session
        entity_id: UUID of the ownership entity
        user_id: UUID of the requesting user

    Returns:
        OwnershipEntity model instance

    Raises:
        HTTPException: 404 if entity not found or doesn't belong to user
    """
    result = await session.execute(
        select(OwnershipEntity).where(
            and_(
                col(OwnershipEntity.id) == entity_id,
                col(OwnershipEntity.user_id) == user_id
            )
        )
    )
    entity = result.scalar_one_or_none()

    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ownership entity with ID {entity_id} not found"
        )

    return entity


async def get_ownership_entities(
    session: AsyncSession,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    entity_type: Optional[str] = None
) -> tuple[list[OwnershipEntity], int]:
    """
    Get all ownership entities for a user with optional filtering.

    Args:
        session: Database session
        user_id: UUID of the user
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        search: Optional search term for name/legal_name
        entity_type: Optional filter by entity type

    Returns:
        Tuple of (list of entities, total count)
    """
    # Build filter conditions
    filters = [col(OwnershipEntity.user_id) == user_id]
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                col(OwnershipEntity.name).ilike(search_term),
                col(OwnershipEntity.legal_name).ilike(search_term)
            )
        )
    if entity_type:
        filters.append(col(OwnershipEntity.entity_type) == entity_type.lower())

    # Get total count using a more efficient query
    count_query = select(func.count()).where(and_(*filters))
    total_result = await session.execute(count_query)
    total = total_result.scalar_one()

    # Build data query with filters
    query = select(OwnershipEntity).where(and_(*filters))
    
    # Apply pagination and ordering
    query = query.order_by(OwnershipEntity.name).offset(skip).limit(limit)

    # Execute query
    result = await session.execute(query)
    entities = result.scalars().all()

    return list(entities), total


async def create_ownership_entity(
    session: AsyncSession,
    entity_data: OwnershipEntityCreate,
    user_id: UUID
) -> OwnershipEntity:
    """
    Create a new ownership entity.

    Args:
        session: Database session
        entity_data: OwnershipEntityCreate schema
        user_id: UUID of the user creating the entity

    Returns:
        Created OwnershipEntity model instance
    """
    # Create entity model
    entity = OwnershipEntity(
        user_id=user_id,
        **entity_data.model_dump()
    )

    session.add(entity)
    await session.commit()
    await session.refresh(entity)

    return entity


async def update_ownership_entity(
    session: AsyncSession,
    entity_id: UUID,
    entity_data: OwnershipEntityUpdate,
    user_id: UUID
) -> OwnershipEntity:
    """
    Update an existing ownership entity.

    Args:
        session: Database session
        entity_id: UUID of the entity to update
        entity_data: OwnershipEntityUpdate schema with fields to update
        user_id: UUID of the requesting user

    Returns:
        Updated OwnershipEntity model instance

    Raises:
        HTTPException: 404 if entity not found or doesn't belong to user
    """
    # Get existing entity
    entity = await get_ownership_entity(session, entity_id, user_id)

    # Update fields
    update_data = entity_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entity, field, value)

    await session.commit()
    await session.refresh(entity)

    return entity


async def delete_ownership_entity(
    session: AsyncSession,
    entity_id: UUID,
    user_id: UUID
) -> None:
    """
    Delete an ownership entity.

    Args:
        session: Database session
        entity_id: UUID of the entity to delete
        user_id: UUID of the requesting user

    Raises:
        HTTPException: 404 if entity not found or doesn't belong to user
        HTTPException: 400 if entity is still referenced by units
    """
    # Get existing entity
    entity = await get_ownership_entity(session, entity_id, user_id)

    # TODO: Check if entity is referenced by any units
    # This will be implemented once we have the unit-entity relationship
    # For now, we'll allow deletion

    await session.delete(entity)
    await session.commit()


async def get_entity_with_stats(
    session: AsyncSession,
    entity_id: UUID,
    user_id: UUID
) -> OwnershipEntityWithStats:
    """
    Get ownership entity with statistics (total units, total rent, etc.)

    Args:
        session: Database session
        entity_id: UUID of the entity
        user_id: UUID of the requesting user

    Returns:
        OwnershipEntityWithStats schema

    TODO: Implement statistics calculation once unit-entity relationship is established
    """
    entity = await get_ownership_entity(session, entity_id, user_id)

    # For now, return with zero stats
    # This will be updated once we have the unit_type_details integration
    return OwnershipEntityWithStats(
        **entity.model_dump(),
        total_units=0,
        total_monthly_rent=0.0
    )
