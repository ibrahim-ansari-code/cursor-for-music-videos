"""
Ownership Entity Router

API endpoints for managing ownership entities (companies, individuals, etc.)
that own or have stakes in property units.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user
from Backend.api.ownership_entities.schemas import (
    OwnershipEntityCreate,
    OwnershipEntityUpdate,
    OwnershipEntityResponse,
    OwnershipEntityWithStats,
    OwnershipEntityListResponse
)
from Backend.api.ownership_entities.service import (
    get_ownership_entity,
    get_ownership_entities,
    create_ownership_entity,
    update_ownership_entity,
    delete_ownership_entity,
    get_entity_with_stats
)
from Backend.database import get_session
from Backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ownership-entities",
    tags=["ownership-entities"],
)


@router.get("", response_model=OwnershipEntityListResponse)
async def list_ownership_entities(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by name or legal name"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get all ownership entities for the current user.

    Supports pagination, search, and filtering by entity type.
    """
    skip = (page - 1) * page_size

    entities, total = await get_ownership_entities(
        session=session,
        user_id=current_user.id,
        skip=skip,
        limit=page_size,
        search=search,
        entity_type=entity_type
    )

    total_pages = (total + page_size - 1) // page_size  # Ceiling division

    return OwnershipEntityListResponse(
        entities=[OwnershipEntityResponse.model_validate(e) for e in entities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("", response_model=OwnershipEntityResponse, status_code=status.HTTP_201_CREATED)
async def create_new_ownership_entity(
    entity_data: OwnershipEntityCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new ownership entity.

    The entity will be associated with the current user.
    """
    entity = await create_ownership_entity(
        session=session,
        entity_data=entity_data,
        user_id=current_user.id
    )

    logger.info(f"User {current_user.id} created ownership entity {entity.id}: {entity.name}")

    return OwnershipEntityResponse.model_validate(entity)


@router.get("/{entity_id}", response_model=OwnershipEntityResponse)
async def get_ownership_entity_by_id(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific ownership entity by ID.

    Returns 404 if the entity doesn't exist or doesn't belong to the current user.
    """
    entity = await get_ownership_entity(
        session=session,
        entity_id=entity_id,
        user_id=current_user.id
    )

    return OwnershipEntityResponse.model_validate(entity)


@router.get("/{entity_id}/stats", response_model=OwnershipEntityWithStats)
async def get_ownership_entity_statistics(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Get ownership entity with statistics.

    Includes total units owned and total monthly rent.
    """
    entity_with_stats = await get_entity_with_stats(
        session=session,
        entity_id=entity_id,
        user_id=current_user.id
    )

    return entity_with_stats


@router.put("/{entity_id}", response_model=OwnershipEntityResponse)
async def update_ownership_entity_by_id(
    entity_id: UUID,
    entity_data: OwnershipEntityUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Update an existing ownership entity.

    Only fields provided in the request body will be updated.
    Returns 404 if the entity doesn't exist or doesn't belong to the current user.
    """
    entity = await update_ownership_entity(
        session=session,
        entity_id=entity_id,
        entity_data=entity_data,
        user_id=current_user.id
    )

    logger.info(f"User {current_user.id} updated ownership entity {entity.id}")

    return OwnershipEntityResponse.model_validate(entity)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ownership_entity_by_id(
    entity_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an ownership entity.

    Returns 404 if the entity doesn't exist or doesn't belong to the current user.
    Returns 400 if the entity is still referenced by units.
    """
    await delete_ownership_entity(
        session=session,
        entity_id=entity_id,
        user_id=current_user.id
    )

    logger.info(f"User {current_user.id} deleted ownership entity {entity_id}")

    return None
