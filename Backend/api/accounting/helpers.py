"""Utility functions for ownership validation used by accounting API modules."""

import logging
from uuid import UUID as PythonUUID
from typing import TypeVar

from fastapi import HTTPException, status
from sqlmodel import col, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.user import User
from Backend.models.property import Property
from Backend.models.lease import Lease

IDType = TypeVar('IDType', int, str, PythonUUID)
logger = logging.getLogger(__name__)


def _convert_to_uuid(user_id: PythonUUID | str | None, context: str = "user ID") -> PythonUUID:
    """
    Converts a user ID to a UUID object, accepting either a UUID or string input.
    
    Raises an HTTP 400 exception if the input is None or not a valid UUID format.
    
    Args:
        user_id: The user identifier to convert. Must be a UUID or a string representation of a UUID.
        context: Optional context string for error messages.
    
    Returns:
        The user ID as a UUID object.
    """
    if user_id is None:
        logger.error("Cannot convert None to UUID for %s", context)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User ID cannot be None for {context}"
        )
    try:
        if isinstance(user_id, PythonUUID):
            return user_id
        return PythonUUID(str(user_id))
    except (ValueError, TypeError) as e:
        logger.exception(
            "Invalid user_id format for UUID conversion: %s (type: %s)", user_id, type(user_id).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid User ID format for {context}: {user_id}"
        ) from e


def _ensure_id_is_not_none(
    entity_id: IDType | None,
    entity_name: str,
    context: str,
) -> IDType:
    """
    Ensures that the provided entity ID is not None, raising HTTP 500 if missing.
    
    Logs a critical error and aborts the request with an HTTP 500 error if the entity ID is None in the specified context. Returns the entity ID if present.
    """
    if entity_id is None:
        logger.error("Critical error: %s ID is None %s.", entity_name, context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Critical error: {entity_name} ID missing {context}."
        )
    return entity_id


async def check_property_ownership(
    property_id: int,
    session: AsyncSession,
    current_user: User
) -> Property:
    """
    Checks if a property exists and if the current user is authorized to access it.
    
    Raises a 404 error if the property does not exist, or a 403 error if the user is neither the owner nor an admin.
    
    Returns:
        The Property object if the user is authorized.
    """
    prop_query = select(Property).where(col(Property.id) == property_id)
    prop_result = await session.execute(prop_query)
    prop = prop_result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Property with ID {property_id} not found")
    if not current_user.is_admin and prop.user_id != current_user.id:
        logger.warning(
            "Authorization failure: User %s attempted to access property %s owned by user %s",
            current_user.id, property_id, prop.user_id
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to access this property's data")
    return prop


async def check_lease_ownership(
    lease_id: int,
    session: AsyncSession,
    current_user: User
) -> Lease:
    """
    Verifies that a lease exists and that the current user is authorized to access it.
    
    Checks if the lease with the given ID exists and ensures the current user is either an admin or the owner of the property associated with the lease. Raises an HTTP 404 error if the lease does not exist, or HTTP 403 if the user lacks authorization.
    
    Args:
        lease_id: The ID of the lease to verify.
        current_user: The user requesting access.
    
    Returns:
        The Lease object if the user is authorized to access it.
    
    Raises:
        HTTPException: If the lease is not found or the user is not authorized.
    """
    lease_query = select(Lease).options(selectinload(getattr(Lease, "property"))).where(col(Lease.id) == lease_id)
    lease_result = await session.execute(lease_query)
    lease = lease_result.scalar_one_or_none()
    if not lease:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Lease with ID {lease_id} not found")
    
    # Verify that the lease has an associated property
    if not lease.property:
        logger.error(
            "Data integrity error: Lease %s exists but has no associated property (property_id: %s)",
            lease_id, lease.property_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data integrity error: Lease {lease_id} has no associated property"
        )
    
    if not current_user.is_admin and lease.property.user_id != current_user.id:
        logger.warning(
            "Authorization failure: User %s attempted to access lease %s "
            "associated with property owned by user %s",
            current_user.id, lease_id, lease.property.user_id
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to access data related to this lease")
    return lease
