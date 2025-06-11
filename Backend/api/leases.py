# Standard library imports
import json
import logging
import re
from datetime import date, datetime
from uuid import UUID as PythonUUID

# Third-party imports
import fitz
from fastapi import (APIRouter, Body, Depends, File, Form, HTTPException,
                     UploadFile, status)
from pydantic import BaseModel
from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlmodel import col
from decimal import Decimal

from Backend.api.auth import get_current_user
# Local application imports
from Backend.database import get_session
from Backend.models.enums import UserType
from Backend.models.lease import Lease, LeaseDocument, LeaseStatus, LeaseCreate, LeaseUpdate
from Backend.models.property import Property, PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User
from Backend.utils.azure_blob import upload_lease_to_blob
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.utils.llm_utils import analyze_lease_text

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/leases",
    tags=["leases"],
)

# --- Helper Function for Active Lease Side Effects ---


async def _apply_active_lease_side_effects(lease: Lease, session: AsyncSession) -> None:
    """
    Applies side effects when a lease becomes active by updating related tenant and property unit records.

    Sets the tenant's current property to the lease's property. If the lease specifies a unit, marks the unit as rented, assigns the tenant, and updates the unit's monthly rent. Raises an HTTP 409 error if the specified unit does not exist.
    """
    try:
        logger.info(
            "Applying active lease side effects for lease ID: %s", lease.id)
        # Update tenant's current_property_id using SQLAlchemy update statement
        logger.info("Updating tenant's current property: tenant ID=%s, property ID=%s",
                    lease.tenant_id, lease.property_id)

        stmt = (
            update(Tenant)
            .where(col(Tenant.id) == lease.tenant_id)
            .values(current_property_id=lease.property_id, updated_at=create_audit_datetime())
        )
        await session.execute(stmt)
        logger.info(
            "Tenant's current property updated successfully for lease ID: %s", lease.id)

        # Additionally, update the PropertyUnit if unit_id is present on the lease
        if lease.unit_id:
            logger.info("Updating PropertyUnit %s for active lease %s",
                        lease.unit_id, lease.id)
            # Lock the unit row for update to prevent concurrent modifications
            unit_query = select(PropertyUnit).where(
                col(PropertyUnit.id) == lease.unit_id).with_for_update()
            unit_result = await session.execute(unit_query)
            unit_to_update = unit_result.scalar_one_or_none()

            if unit_to_update:
                unit_to_update.tenant_id = lease.tenant_id
                unit_to_update.is_rented = True
                unit_to_update.monthly_rent = lease.monthly_rent  # Update unit rent from lease
                unit_to_update.updated_at = create_audit_datetime()
                # session.add(unit_to_update) # Not strictly needed as it's tracked by session.get
                logger.info("PropertyUnit %s updated for lease %s: tenant_id=%s, is_rented=%s, monthly_rent=%s",
                            unit_to_update.id, lease.id, unit_to_update.tenant_id, unit_to_update.is_rented, unit_to_update.monthly_rent)
            else:
                logger.error(
                    "PropertyUnit with ID %s not found for lease %s during side effect application. Rolling back.", lease.unit_id, lease.id)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Property unit {lease.unit_id} not found or conflict during lease activation side effects."
                )
    except HTTPException:  # Re-raise HTTPException to be caught by endpoint handler
        raise
    except Exception as e:
        logger.exception(
            "Error applying active lease side effects for lease %s", lease.id)
        raise


async def _revoke_active_lease_side_effects(lease: Lease, session: AsyncSession) -> None:
    """
    Reverts changes to tenant and property unit records when a lease is deactivated.

    If the lease has an associated unit and the tenant matches, marks the unit as vacant and removes the tenant assignment. If the tenant has no other active leases, clears their current property association.
    """
    try:
        logger.info(
            "Revoking active lease side effects for lease ID: %s", lease.id)

        # Update PropertyUnit
        if lease.unit_id:
            logger.info(
                "Updating PropertyUnit %s for deactivated lease %s", lease.unit_id, lease.id)
            unit_query = select(PropertyUnit).where(
                col(PropertyUnit.id) == lease.unit_id).with_for_update()
            unit_result = await session.execute(unit_query)
            unit_to_update = unit_result.scalar_one_or_none()
            if unit_to_update and unit_to_update.tenant_id == lease.tenant_id:
                unit_to_update.is_rented = False
                unit_to_update.tenant_id = None
                unit_to_update.updated_at = create_audit_datetime()
                # session.add(unit_to_update) # Not strictly needed as it's tracked by session.get
                logger.info(
                    "PropertyUnit %s marked as vacant for lease %s", unit_to_update.id, lease.id)
            elif unit_to_update:
                logger.warning("PropertyUnit %s tenant_id %s does not match lease tenant_id %s. Skipping unit update.",
                               lease.unit_id, unit_to_update.tenant_id, lease.tenant_id)
            else:
                logger.warning(
                    "PropertyUnit %s not found during lease deactivation for lease %s.", lease.unit_id, lease.id)

        # Update Tenant's current_property_id if this was their last active lease on ANY property
        # This is a simplified check. A more robust check might ensure this specific property.
        if lease.tenant_id and lease.property_id:
            other_active_leases_query = (
                select(col(Lease.id))
                .where(
                    col(Lease.tenant_id) == lease.tenant_id,
                    col(Lease.status) == LeaseStatus.ACTIVE,
                    # Exclude the current lease being deactivated
                    col(Lease.id) != lease.id
                ).limit(1)
            )
            other_active_lease_exists = await session.scalar(other_active_leases_query)

            if not other_active_lease_exists:
                logger.info(
                    "No other active leases found for tenant %s. Clearing current_property_id.", lease.tenant_id)
                # Assuming Tenant.id is int
                tenant_to_update = await session.get(Tenant, lease.tenant_id)
                if tenant_to_update and tenant_to_update.current_property_id == lease.property_id:
                    # Only clear if current_property_id matches the property of the deactivated lease
                    stmt = (
                        update(Tenant)
                        .where(col(Tenant.id) == lease.tenant_id)
                        .values(current_property_id=None, updated_at=create_audit_datetime())
                    )
                    await session.execute(stmt)
                    logger.info(
                        "Cleared current_property_id for tenant %s.", lease.tenant_id)
                elif tenant_to_update:
                    logger.info("Tenant %s current_property_id (%s) does not match deactivated lease property_id (%s). Not clearing.",
                                lease.tenant_id, tenant_to_update.current_property_id, lease.property_id)
                else:
                    logger.warning(
                        "Tenant %s not found for clearing current_property_id.", lease.tenant_id)
            else:
                logger.info(
                    "Tenant %s has other active leases. Not clearing current_property_id.", lease.tenant_id)

    except HTTPException:  # Re-raise HTTPException to be caught by endpoint handler
        raise
    except Exception as e:
        logger.exception(
            "Error revoking active lease side effects for lease %s", lease.id)
        raise

# --- Helper Function for Permission Checks ---


async def check_lease_permission(
    lease_id: int,
    session: AsyncSession,
    current_user: User,
    action: str = "view"
) -> Lease:
    """
    Retrieves a lease by ID and checks if the current user has permission for the specified action.

    Admins have full access. Tenants may only view their own leases. Landlords may access leases for properties they own. Raises HTTP 404 if the lease does not exist, or HTTP 403 if the user is not authorized.

    Args:
        lease_id: The ID of the lease to check.
        action: The action being performed (e.g., "view", "update"). Tenants are restricted to "view".

    Returns:
        The Lease object if permission is granted.
    """
    query = (
        select(Lease)
        .options(selectinload(getattr(Lease, "property")))
        .where(col(Lease.id) == lease_id)
    )
    result = await session.execute(query)
    lease = result.scalar_one_or_none()

    if not lease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lease with ID {lease_id} not found"
        )

    # Admin can do anything
    if current_user.is_admin:
        return lease

    # Tenant check
    if current_user.user_type == UserType.TENANT:
        if lease.tenant_id == current_user.id and action == "view":
            return lease
        else:
            logger.warning(
                f"Tenant {current_user.id} permission denied for {action} lease {lease_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this lease"
            )

    # Landlord check (must own the property)
    if current_user.user_type == UserType.LANDLORD:
        if lease.property and lease.property.user_id == current_user.id:
            return lease
        else:
            logger.warning(
                f"Landlord {current_user.id} permission denied for {action} lease {lease_id} on property {lease.property_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this lease"
            )

    # Default deny if none of the above
    logger.error(
        f"Unknown user type or permission error for user {current_user.id}, action {action}, lease {lease_id}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Not authorized to {action} this lease"
    )

# API models


class LeaseBase(BaseModel):
    start_date: date
    end_date: date
    monthly_rent: Decimal
    security_deposit: Decimal
    is_renewable: bool = True
    auto_renew: bool = False
    rent_due_day: int = 1
    late_fee_amount: Decimal | None = None
    late_fee_after_days: int | None = None
    special_terms: str | None = None
    property_id: int
    unit_id: int | None = None
    tenant_id: int


class LeaseResponse(LeaseBase):
    id: int
    status: LeaseStatus
    created_at: datetime
    updated_at: datetime
    tenant: Tenant | None
    property: Property | None

    class Config:
        from_attributes = True


class LeaseDocumentResponse(BaseModel):
    id: int
    name: str
    file_path: str
    document_type: str
    upload_date: datetime
    uploaded_by_id: PythonUUID | None = None

    class Config:
        from_attributes = True


class LeaseAnalysisResponse(BaseModel):
    monthly_rent: Decimal
    start_date: date | None = None
    end_date: date | None = None
    security_deposit: Decimal
    late_fee_amount: Decimal | None = None


class LeaseUploadResponse(BaseModel):
    file_url: str

@router.post("/upload-lease", response_model=LeaseUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_lease(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a lease PDF file to Azure Blob Storage and returns its public URL.

    Only Admin and Landlord users are authorized to perform this operation. The uploaded file must be a PDF; otherwise, a 400 error is returned. On success, returns a dictionary containing the file URL.

    Returns:
        dict: A dictionary with the key "file_url" containing the URL of the uploaded file.

    Raises:
        HTTPException: If the user is not authorized, the file is not a PDF, or the upload fails.
    """
    try:
        logger.info(
            f"Uploading lease file: {file.filename} for user ID: {current_user.id}")

        # Check if user is authorized based on their type
        user_type = current_user.user_type.upper() if isinstance(
            current_user.user_type, str) else current_user.user_type

        if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
            logger.warning(
                f"Authorization failed: User {current_user.id} with type {user_type} attempted to upload lease")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to upload leases"
            )

        # Check if file is a PDF
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are accepted"
            )

        # Upload the file to Azure Blob Storage
        file_url = await upload_lease_to_blob(file, current_user.id)

        logger.info(f"Lease file uploaded successfully: {file_url}")
        return {"file_url": file_url}

    except Exception as e:
        # Log the detailed error including stack trace
        logger.exception("Failed to upload lease document")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload lease document: {str(e)}"
        )

# API endpoints


@router.post("/", response_model=LeaseResponse, status_code=status.HTTP_201_CREATED)
async def create_lease(
    lease_data: LeaseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new lease after validating property ownership, tenant existence, and unit association.
    
    If the user is a landlord, verifies they own the specified property. Ensures the tenant exists and, if a unit is specified, that it belongs to the property. Optionally creates a lease document record if a file URL is provided. If the lease is created with ACTIVE status, applies side effects to update the tenant's current property and the unit's rental status. Commits all changes and returns the created lease object.
    
    Raises:
        HTTPException: If the property, tenant, or unit is invalid, or if a database error occurs.
    """
    logger.info("Create lease request by user: id=%s, email=%s, type=%s",
                current_user.id, current_user.email, current_user.user_type)
    file_url = getattr(lease_data, "file_url", None)
    if file_url:
        logger.info("Lease creation includes document URL: %s", file_url)

    # Fetch the property to check ownership
    property_query = select(Property).where(
        col(Property.id) == lease_data.property_id)
    property_result = await session.execute(property_query)
    target_property = property_result.scalar_one_or_none()

    if not target_property:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid property ID"
        )

    # Check ownership (Landlord must own, Admin bypasses)
    if not current_user.is_admin and target_property.user_id != current_user.id:
        logger.warning(
            f"User {current_user.id} (Landlord) attempted to create lease for property {lease_data.property_id} they don't own")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create leases for this property"
        )

    # Validate tenant
    tenant_query = select(Tenant).where(col(Tenant.id) == lease_data.tenant_id)
    tenant_exists = await session.scalar(tenant_query)
    if not tenant_exists:
        logger.error(f"Tenant not found with ID: {lease_data.tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID"
        )

    # Validate unit if provided
    if lease_data.unit_id:
        unit_query = select(col(PropertyUnit.id)).where(
            and_(col(PropertyUnit.id) == lease_data.unit_id, col(
                PropertyUnit.property_id) == lease_data.property_id)
        )
        unit_exists = await session.scalar(unit_query)
        if not unit_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid unit ID or unit does not belong to the specified property"
            )

    # Create lease using ORM
    new_lease = Lease(
        # Exclude file_url if present
        **lease_data.model_dump(exclude={"file_url"}),
        created_at=create_audit_datetime(),
        updated_at=create_audit_datetime()
    )

    try:
        session.add(new_lease)
        await session.flush()  # Get the lease ID

        # Ensure lease has a valid ID after flush, BEFORE attempting document creation
        if new_lease.id is None:
            logger.error(
                "Lease ID is None after database flush. Rolling back session.")
            # This error is critical and should abort the whole operation.
            # The outer try/except will handle the rollback.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Critical error: Lease ID missing after flush."
            )

        # If file_url is provided, create a lease document record
        if file_url:
            try:
                logger.info(
                    "Creating lease document record for lease %s with URL: %s", new_lease.id, file_url)
                # The new_lease.id check is now done above
                document = LeaseDocument(
                    name="Lease Agreement",
                    file_path=file_url,
                    document_type="contract",
                    upload_date=create_audit_datetime(),
                    lease_id=new_lease.id,
                    uploaded_by_id=current_user.id  # Store the raw string directly
                )
                session.add(document)
                logger.info(
                    "Lease document record created successfully for lease %s", new_lease.id)
            except Exception:
                logger.exception("Error creating lease document record")
                # Don't fail the whole lease creation if document record fails

        # If lease is created with status ACTIVE, update tenant's current_property_id and unit status
        if new_lease.status == LeaseStatus.ACTIVE:
            await _apply_active_lease_side_effects(new_lease, session)

        await session.commit()  # Commit lease and document (if any)
        # Refresh with relations for response
        await session.refresh(new_lease, attribute_names=['tenant', 'property'])

        logger.info("Lease created: %s with status %s by user %s",
                    new_lease.id, new_lease.status, current_user.id)
        return new_lease  # Return the ORM object, Pydantic will handle response model

    except Exception as db_error:
        await session.rollback()
        logger.exception("Database error during lease creation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(db_error)}"
        ) from db_error


@router.get("/", response_model=list[LeaseResponse])
async def get_leases(
    status: LeaseStatus | None = None,
    property_id: int | None = None,
    tenant_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> list[Lease]:
    """
    Retrieves leases filtered by status, property, or tenant, applying access control based on user role.

    Tenants can only view their own leases. Landlords see leases for properties they own. Admin users can access all leases. Returns an empty list if a tenant attempts to filter for another tenant's leases.
    """
    query = select(Lease).options(
        selectinload(getattr(Lease, "tenant")),
        selectinload(getattr(Lease, "property")),
        selectinload(getattr(Lease, "unit"))
    )

    # Base filters from query params
    conditions = []
    if status:
        conditions.append(col(Lease.status) == status)
    if property_id:
        conditions.append(col(Lease.property_id) == property_id)
    if tenant_id:
        # Allow landlords/admins to filter by tenant_id
        if current_user.user_type != UserType.TENANT:
            conditions.append(col(Lease.tenant_id) == tenant_id)
        else:
            # If the current user is a tenant, they can only filter for *their own* tenant_id
            if current_user.id != tenant_id:
                logger.warning(
                    f"Tenant {current_user.id} attempted to filter leases for tenant {tenant_id}")
                # Return empty list if tenant tries to filter for someone else
                return []
            conditions.append(col(Lease.tenant_id) == current_user.id)

    # Apply access control based on user type
    if current_user.user_type == UserType.TENANT:
        # Tenants can only see their own leases (redundant if tenant_id filter applied, but safe)
        conditions.append(col(Lease.tenant_id) == current_user.id)
    elif current_user.user_type == UserType.LANDLORD:
        # Landlords can only see leases for properties they own
        # Join with Property table and filter by user_id
        query = query.join(Property, col(Lease.property_id) == col(
            Property.id)).where(col(Property.user_id) == current_user.id)
    # Admin sees all (no additional user_id filter needed)

    # Apply combined conditions
    if conditions:
        query = query.where(and_(*conditions))

    result = await session.execute(query)
    leases = result.scalars().unique().all()
    return list(leases)


@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific lease by ID, checking permissions."""
    lease = await check_lease_permission(lease_id, session, current_user, action="view")
    return lease


@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease(
    lease_id: int,
    lease_data: LeaseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates general lease fields for an existing lease, excluding status changes.
    
    Checks user permissions and applies updates to lease attributes such as dates, rent, deposit, and related information. Any attempt to modify the lease status is ignored; status changes must be performed via the dedicated status endpoint. Commits changes to the database and returns the updated lease. Rolls back and raises an HTTP 500 error if the update fails.
    """
    lease = await check_lease_permission(lease_id, session, current_user, action="update")

    # Update lease fields
    lease_data_dict = lease_data.model_dump(exclude_unset=True)

    # Status changes are not handled by this endpoint to avoid complex side-effects here.
    # Use the dedicated /status endpoint for status modifications.
    if 'status' in lease_data_dict:
        logger.warning(
            "Attempt to update status via general update endpoint for lease %s. "
            "Status field will be ignored. Use POST /leases/{lease_id}/status for status changes.",
            lease_id,
        )
        # Ensure status is not accidentally updated
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="`status` cannot be updated here. Use POST /leases/{lease_id}/status."
        )

    for key, value in lease_data_dict.items():
        setattr(lease, key, value)

    lease.updated_at = create_audit_datetime()  # Explicitly set updated_at

    try:
        session.add(lease)  # Add the modified object to the session
        await session.commit()
        # Refresh to get any DB-generated changes and updated relationships
        await session.refresh(lease, attribute_names=['tenant', 'property', 'unit'])

        logger.info("Lease updated: %s by user %s. Fields updated: %s",
                    lease.id, current_user.id, ", ".join(lease_data_dict.keys()))
        return lease
    except Exception as e:
        await session.rollback()
        logger.exception("Error updating lease %s", lease_id)
        # Consider specific error types if needed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lease: {str(e)}",
        ) from e


@router.post("/{lease_id}/validate", response_model=LeaseResponse)
async def validate_lease(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Transitions a lease from DRAFT to PENDING status after verifying user permissions.

    Raises:
        HTTPException: If the lease is not in DRAFT status, or if a database error occurs.

    Returns:
        The updated lease object with status set to PENDING.
    """
    lease = await check_lease_permission(lease_id, session, current_user, action="validate")

    if lease.status != LeaseStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lease is not in DRAFT status (current status: {lease.status})"
        )

    # Update lease status to PENDING
    lease.status = LeaseStatus.PENDING
    # lease.updated_at = datetime.utcnow() # Handled by model?

    try:
        session.add(lease)
        await session.commit()
        await session.refresh(lease)

        logger.info("Lease validated: %s by user %s",
                    lease.id, current_user.id)
        return lease
    except Exception as e:
        await session.rollback()
        logger.exception("Error validating lease %s", lease_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate lease: {str(e)}"
        )


@router.post("/{lease_id}/status", response_model=LeaseResponse)
async def update_lease_status(
    lease_id: int,
    status_data: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the status of a lease after verifying user permissions.
    
    Validates the requested status change, applies or revokes side effects on related tenant and property unit records when transitioning to or from ACTIVE status, and commits the update. Returns the updated lease object. Raises HTTP 422 if the status is missing or invalid, and HTTP 500 for database errors.
    """
    logger.info(
        f"Lease status update request: lease ID={lease_id}, user ID={current_user.id}, data: {status_data}")

    # Check permission first using the helper function
    lease = await check_lease_permission(lease_id, session, current_user, action="update status")

    new_status_str = status_data.get("status")
    if not new_status_str:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Status is required")

    try:
        # Validate and convert to Enum
        new_status = LeaseStatus(new_status_str)
    except ValueError:
        valid_statuses = [s.value for s in LeaseStatus]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{new_status_str}'. Valid values are: {', '.join(valid_statuses)}"
        )

    original_status = lease.status
    if original_status == new_status:
        logger.info(
            f"Lease {lease_id} status already '{new_status}'. No update needed.")
        return lease  # Return current lease data if status hasn't changed

    lease.status = new_status
    # lease.updated_at = datetime.utcnow() # Handled by model?

    try:
        session.add(lease)

        # Handle tenant current_property_id update if status changed to ACTIVE
        if new_status == LeaseStatus.ACTIVE and original_status != LeaseStatus.ACTIVE:
            # If activating, apply side effects
            await _apply_active_lease_side_effects(lease, session)
        elif new_status != LeaseStatus.ACTIVE and original_status == LeaseStatus.ACTIVE:
            await _revoke_active_lease_side_effects(lease, session)

        await session.commit()
        await session.refresh(lease, attribute_names=['tenant', 'property', 'unit'])

        logger.info(
            f"Lease status updated successfully: ID {lease_id} status changed from {original_status} to {new_status} by user {current_user.id}")
        return lease

    except Exception as db_error:
        await session.rollback()
        logger.exception(
            "Database error during lease status update for lease %s", lease_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error updating lease status: {str(db_error)}"
        )


@router.post("/{lease_id}/upload", response_model=LeaseDocumentResponse)
async def upload_lease_document(
    lease_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a document file for a specific lease and creates a corresponding database record.

    The file is stored in blob storage, and a LeaseDocument entry is created with metadata about the upload. Only users with permission for the lease can perform this action.

    Returns:
        The created LeaseDocument object containing metadata about the uploaded file.

    Raises:
        HTTPException: If the file upload or database record creation fails.
    """
    await check_lease_permission(lease_id, session, current_user, action="upload document to")

    # Upload file (replace with actual blob storage logic)
    try:
        file_url = await upload_lease_to_blob(file, current_user.id)
        logger.info(f"Lease document uploaded to blob storage: {file_url}")
    except Exception as upload_error:
        logger.exception("Failed to upload lease document to blob storage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(upload_error)}"
        )

    # Create document record
    document = LeaseDocument(
        name=file.filename or "Lease Document",
        file_path=file_url,  # Use the actual URL from blob storage
        document_type=document_type,
        lease_id=lease_id,
        uploaded_by_id=current_user.id  # Store the raw string directly
    )

    try:
        session.add(document)
        await session.commit()
        await session.refresh(document)

        logger.info(
            f"Lease document record created: {document.id} for lease {lease_id} by user {current_user.id}")
        return document
    except Exception as e:
        await session.rollback()
        logger.exception(
            "Error creating lease document record for lease %s", lease_id)
        # Consider deleting the uploaded blob if DB insert fails
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document record: {str(e)}"
        )


@router.get("/{lease_id}/documents", response_model=list[LeaseDocumentResponse])
async def get_lease_documents(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves all documents associated with a specific lease after verifying user permissions.

    Args:
        lease_id: The ID of the lease whose documents are to be retrieved.

    Returns:
        A list of LeaseDocument objects linked to the specified lease.
    """
    await check_lease_permission(lease_id, session, current_user, action="view documents for")

    # Get documents
    query = select(LeaseDocument).where(
        col(LeaseDocument.lease_id) == lease_id)
    result = await session.execute(query)
    documents = result.scalars().all()

    return documents

# Analyze and Parse endpoints likely need permission checks too,
# depending on whether they operate on existing leases or just raw files.
# Assuming they operate on files before a lease is created/saved,
# we only need to check if the user *can* create leases (Landlord/Admin).


@router.post("/analyze", response_model=LeaseAnalysisResponse)
async def analyze_lease(
    file: UploadFile = File(...),
    # property_id: int = Form(...), # property_id might not be needed if analyzing before creation
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Analyze a lease document (check user can create leases)."""
    # Check if user is authorized to perform actions related to lease creation
    user_type = current_user.user_type.upper() if isinstance(
        current_user.user_type, str) else current_user.user_type
    if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to analyze leases")

    try:
        logger.info(f"Starting lease analysis by user {current_user.id}")
        content = await file.read()
        # Assuming UTF-8, handle potential decoding errors
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning(
                "Failed to decode lease file as UTF-8, trying latin-1")
            try:
                text_content = content.decode('latin-1')
            except UnicodeDecodeError as decode_err:
                logger.error(
                    f"Failed to decode lease file content: {decode_err}")
                raise HTTPException(
                    status_code=400, detail="Could not decode file content.")

        logger.debug(f"File content preview: {text_content[:100]}...")
        analysis_result = await analyze_lease_text(text_content)
        logger.info("Lease analysis completed successfully")
        logger.debug(f"Analysis result: {analysis_result}")

        # Safely extract and convert data
        monthly_rent_raw = analysis_result.get(
            'rent_payment', {}).get('monthly_rent', '0')
        security_deposit_raw = analysis_result.get(
            'deposits', {}).get('security_deposit', '0')

        def parse_currency(value_str):
            if not isinstance(value_str, str):
                value_str = str(value_str)
            # Remove currency symbols, commas, and whitespace
            cleaned_str = re.sub(r"[$,\s]", "", value_str)
            try:
                return Decimal(cleaned_str)
            except Exception:
                logger.warning(
                    f"Could not parse currency value: {value_str!r}")
                return Decimal("0.0")  # Default to 0 if parsing fails

        response_data = {
            "monthly_rent": parse_currency(monthly_rent_raw),
            "start_date": analysis_result.get('term_details', {}).get('lease_start_date'),
            "end_date": analysis_result.get('term_details', {}).get('lease_end_date'),
            "security_deposit": parse_currency(security_deposit_raw),
            "tenant_name": analysis_result.get('core_identifiers', {}).get('tenant_name'),
            "unit": analysis_result.get('core_identifiers', {}).get('unit_number')
        }

        # Validate date formats (ensure they are YYYY-MM-DD or can be parsed)
        # Convert empty strings to None for optional date fields
        start_date_str = response_data["start_date"]
        end_date_str = response_data["end_date"]

        try:
            response_data["start_date"] = date.fromisoformat(
                start_date_str) if start_date_str else None
            response_data["end_date"] = date.fromisoformat(
                end_date_str) if end_date_str else None
        except ValueError as date_err:
            logger.error(
                f"Invalid date format received from LLM after defaulting: {date_err} for start: '{start_date_str}', end: '{end_date_str}'")
            # If still invalid after defaulting in llm_utils, set to None to prevent Pydantic error
            response_data["start_date"] = None
            response_data["end_date"] = None

        logger.info(f"Formatted response data: {response_data}")
        return LeaseAnalysisResponse(**response_data)

    except ValueError as e:
        logger.error(f"Validation error in lease analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Error analyzing lease")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to analyze lease: {str(e)}")


@router.post("/parse", response_model=LeaseAnalysisResponse)
async def parse_lease(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Parses a lease PDF file, extracting structured lease information using LLM analysis.
    
    Checks that the user is an Admin or Landlord before processing. Reads the uploaded PDF, extracts its text, and analyzes it with an external language model utility to identify key lease details such as rent, deposit, dates, tenant name, and unit. Safely parses currency and date fields, returning a structured response. Raises HTTP 400 for empty files, HTTP 403 for unauthorized users, HTTP 422 for parsing errors, and HTTP 500 for unexpected failures.
    
    Returns:
        LeaseAnalysisResponse: Structured lease data extracted from the document.
    """
    # Check if user is authorized
    user_type = current_user.user_type.upper() if isinstance(
        current_user.user_type, str) else current_user.user_type
    if user_type not in [UserType.ADMIN.value, UserType.LANDLORD.value, 'ADMIN', 'LANDLORD']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to parse leases")
    logger.info(f"User {current_user.id} authorized to parse lease")

    try:
        await file.seek(0)  # Reset file pointer to the beginning
        content = await file.read()
        if not content:
            logger.error("File content is empty after reading.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Uploaded file content is empty or could not be read.")

        pdf_document = fitz.open(stream=content, filetype="pdf")
        text = "".join(getattr(page, "get_text")() for page in pdf_document)
        pdf_document.close()

        logger.info(
            f"Sending lease text for analysis (first 100 chars): {text[:100]!r}")
        raw_parsed_data = await analyze_lease_text(text)
        logger.info(
            f"Raw LLM parsed data:\n{json.dumps(raw_parsed_data, indent=2)}")

        # --- Safely extract and parse data (improved parsing logic) ---
        parsed_data = {}
        try:
            # Function to safely parse currency strings
            def parse_currency(value_str):
                if not isinstance(value_str, str):
                    value_str = str(value_str)
                # Remove currency symbols, commas, and whitespace
                cleaned_str = re.sub(r"[$,\s]", "", value_str)
                # Handle potential edge cases like empty strings or non-numeric chars
                if not cleaned_str or not re.match(r"^\d*\.?\d+$", cleaned_str):
                    logger.warning(
                        f"Could not parse currency value: {value_str!r}. Defaulting to 0.0")
                    return Decimal("0.0")
                try:
                    return Decimal(cleaned_str)
                except Exception:
                    logger.warning(
                        f"Could not convert cleaned currency value to float: {cleaned_str!r}. Defaulting to 0.0")
                    return Decimal("0.0")

            parsed_data['monthly_rent'] = parse_currency(
                raw_parsed_data.get('rent_payment', {}).get('monthly_rent', '0'))
            parsed_data['security_deposit'] = parse_currency(
                raw_parsed_data.get('deposits', {}).get('security_deposit', '0'))

            # Safely get dates and tenant name
            parsed_data['start_date'] = raw_parsed_data.get(
                'term_details', {}).get('lease_start_date')
            parsed_data['end_date'] = raw_parsed_data.get(
                'term_details', {}).get('lease_end_date')
            parsed_data['tenant_name'] = raw_parsed_data.get(
                'core_identifiers', {}).get('tenant_name')
            parsed_data['unit'] = raw_parsed_data.get(
                'core_identifiers', {}).get('unit_number')

            # Validate and convert dates
            start_date_str = parsed_data.get('start_date')
            end_date_str = parsed_data.get('end_date')

            try:
                parsed_data['start_date'] = date.fromisoformat(
                    start_date_str) if start_date_str else None
                parsed_data['end_date'] = date.fromisoformat(
                    end_date_str) if end_date_str else None
            except ValueError as date_err:
                logger.error(
                    f"Invalid date format for start_date: '{start_date_str}' or end_date: '{end_date_str}' after LLM defaulting - setting to None. Error: {date_err}")
                # Ensure keys exist before setting to None if parsing failed
                parsed_data['start_date'] = None
                parsed_data['end_date'] = None

        except Exception as parse_error:  # Catch broader errors during parsing
            logger.exception(
                "Error processing LLM response data: %s", parse_error)
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"Error processing parsed lease data: {parse_error}")

        logger.info(f"Restructured data: {parsed_data}")
        return LeaseAnalysisResponse(**parsed_data)

    except Exception as e:
        logger.exception("Failed to parse lease document")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to parse lease document: {str(e)}")


@router.delete("/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lease(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Deletes a lease by ID after verifying user permissions.
    
    If the lease is active, revokes associated side effects (such as updating tenant and property unit records) before deletion. Lease documents are deleted via cascading, and related payments have their lease reference set to NULL if the database schema is configured accordingly.
    
    Raises an HTTP 409 error if the lease cannot be deleted due to foreign key constraints, or HTTP 500 for other database errors.
    """
    logger.info("Delete request for lease %s by user %s",
                lease_id, current_user.id)
    # Use "update" action for permission check as it covers ownership logic for landlords
    lease = await check_lease_permission(lease_id, session, current_user, action="delete")

    try:
        # If lease is active, revoke side effects before deleting
        if lease.status == LeaseStatus.ACTIVE:
            logger.info(
                "Lease %s is active, revoking side effects before deletion.", lease_id)
            await _revoke_active_lease_side_effects(lease, session)

        await session.delete(lease)
        await session.commit()
        logger.info(
            "Lease %s deleted successfully by user %s", lease_id, current_user.id)
        # No return content needed for 204
    except Exception as e:
        await session.rollback()
        logger.exception("Error deleting lease %s", lease_id)
        # Check for foreign key violation, which might indicate migrations not applied
        if "violates foreign key constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete lease because it is still referenced by other records. "
                       "Ensure migrations are applied to handle this automatically.",
            ) from e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lease: {str(e)}",
        ) from e
