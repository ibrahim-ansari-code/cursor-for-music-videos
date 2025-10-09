# Standard library imports
import logging

# Third-party imports
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

# Local application imports
from Backend.api.auth import get_current_user
from Backend.database import get_session
from Backend.models.lease import LeaseStatus
from Backend.models.user import User

from .schemas import (
    LeaseAnalysisResponse,
    LeaseCreate,
    LeaseDocumentResponse,
    LeaseResponse,
    LeaseUpdate,
    LeaseUploadResponse,
    SecureDocumentUrlResponse,
)
from .service import (
    analyze_lease,
    create_lease,
    delete_lease,
    get_lease,
    get_lease_document_by_id,
    get_lease_documents,
    get_leases,
    parse_lease,
    update_lease,
    update_lease_status,
    upload_lease,
    upload_lease_document,
    validate_lease,
)
from Backend.utils.azure_blob import generate_secure_document_url

# Configure logging
logger = logging.getLogger(__name__)

# Set up API router
router = APIRouter(
    prefix="/leases",
    tags=["leases"],
)


@router.post("/", response_model=LeaseResponse, status_code=status.HTTP_201_CREATED)
async def create_lease_endpoint(
    lease_data: LeaseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new lease after validating property ownership, tenant existence, and unit association.
    
    If the user is a landlord, verifies they own the specified property.
    Ensures the tenant exists and, if a unit is specified, that it belongs to the property.
    Optionally creates a lease document record if a file URL is provided. 
    If the lease is created with ACTIVE status, applies side effects to update the tenant's current property and the unit's rental status.
    Commits all changes and returns the created lease object.
    
    Raises:
        HTTPException: If the property, tenant, or unit is invalid, or if a database error occurs.
    """
    try:
        lease = await create_lease(lease_data, current_user, session)
        return lease
    except HTTPException:
        # Re-raise HTTPExceptions as-is (they contain proper status codes and messages)
        raise
    except Exception as db_error:
        await session.rollback()
        logger.exception("Database error during lease creation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(db_error)}"
        ) from db_error


@router.post("/upload-lease", response_model=LeaseUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_lease_endpoint(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a lease PDF file to Azure Blob Storage and returns its public URL.

    Only Admin and Landlord users are authorized to perform this operation.
    The uploaded file must be a PDF; otherwise, a 400 error is returned.
    On success, returns a dictionary containing the file URL.

    Returns:
        dict: A dictionary with the key "file_url" containing the URL of the uploaded file.

    Raises:
        HTTPException: If the user is not authorized, the file is not a PDF, or the upload fails.
    """
    try:
        result = await upload_lease(file, current_user)
        return result
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        logger.exception("Failed to upload lease document")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload lease document: {str(e)}"
        )

@router.get("/{lease_id}", response_model=LeaseResponse)
async def get_lease_endpoint(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific lease by ID, checking permissions."""
    lease = await get_lease(lease_id, current_user, session)
    return lease


@router.get("/", response_model=list[LeaseResponse])
async def get_leases_endpoint(
    status: LeaseStatus | None = None,
    property_id: int | None = None,
    tenant_id: int | None = None,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves leases filtered by status, property, or tenant, applying access control based on user role.

    Tenants can only view their own leases. Landlords see leases for properties they own. Admin users can access all leases. Returns an empty list if a tenant attempts to filter for another tenant's leases.
    """
    leases = await get_leases(current_user, session, lease_status=status, property_id=property_id, tenant_id=tenant_id)
    return leases


@router.get("/{lease_id}/documents", response_model=list[LeaseDocumentResponse])
async def get_lease_documents_endpoint(
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
    documents = await get_lease_documents(lease_id, current_user, session)
    return documents


@router.put("/{lease_id}", response_model=LeaseResponse)
async def update_lease_endpoint(
    lease_id: int,
    lease_data: LeaseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates general lease fields for an existing lease, excluding status changes.
    
    Checks user permissions and applies updates to lease attributes such as dates, rent, deposit, and related information.
    Any attempt to modify the lease status is ignored; status changes must be performed via the dedicated status endpoint.
    Commits changes to the database and returns the updated lease. Rolls back and raises an HTTP 500 error if the update fails.
    """
    try:
        lease = await update_lease(lease_id, lease_data, current_user, session)
        return lease
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        await session.rollback()
        logger.exception("Error updating lease %s", lease_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update lease: {str(e)}",
        ) from e
    

@router.post("/{lease_id}/status", response_model=LeaseResponse)
async def update_lease_status_endpoint(
    lease_id: int,
    status_data: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the status of a lease after verifying user permissions.
    
    Validates the requested status change, applies or revokes side effects on related tenant and property unit records
    when transitioning to or from ACTIVE status, and commits the update. Returns the updated lease object. 
    Raises HTTP 422 if the status is missing or invalid, and HTTP 500 for database errors.
    """
    try:
        lease = await update_lease_status(lease_id, status_data, current_user, session)
        return lease
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as db_error:
        await session.rollback()
        logger.exception("Database error during lease status update for lease %s", lease_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error updating lease status: {str(db_error)}"
        )


@router.post("/{lease_id}/validate", response_model=LeaseResponse)
async def validate_lease_endpoint(
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
    try:
        lease = await validate_lease(lease_id, current_user, session)
        return lease
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        await session.rollback()
        logger.exception("Error validating lease %s", lease_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate lease: {str(e)}"
        )


@router.post("/{lease_id}/upload", response_model=LeaseDocumentResponse)
async def upload_lease_document_endpoint(
    lease_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Uploads a document file for a specific lease and creates a corresponding database record.

    The file is stored in blob storage, and a LeaseDocument entry is created with metadata about the upload.
    Only users with permission for the lease can perform this action.

    Returns:
        The created LeaseDocument object containing metadata about the uploaded file.

    Raises:
        HTTPException: If the file upload or database record creation fails.
    """
    try:
        document = await upload_lease_document(lease_id, document_type, file, current_user, session)
        return document
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        await session.rollback()
        logger.exception("Error creating lease document record for lease %s", lease_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save document record: {str(e)}"
        )


@router.get("/{lease_id}/documents/{document_id}/secure-url", response_model=SecureDocumentUrlResponse)
async def get_document_secure_url(
    lease_id: int,
    document_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a time-limited, authenticated URL for secure document preview.
    
    This endpoint implements the industry-standard SAS (Shared Access Signature) pattern
    used by Dropbox, Box, SharePoint, and other major SaaS platforms.
    
    Security Features:
        - Requires JWT authentication
        - Verifies lease access permission
        - Generates 1-hour expiring SAS token
        - Read-only access (no write/delete)
        - HTTPS enforced
        - Optional IP restriction
        - Audit logging enabled
    
    Args:
        lease_id: The ID of the lease containing the document
        document_id: The ID of the document to access
        request: FastAPI Request object (for client IP)
        
    Returns:
        SecureDocumentUrlResponse containing:
            - secure_url: Azure Blob URL with SAS token appended
            - expires_at: ISO 8601 UTC datetime when URL expires
            - expires_in_seconds: Seconds until expiration (3600 for 1 hour)
            
    Raises:
        HTTPException 403: If user lacks permission to access the lease
        HTTPException 404: If lease or document not found
        HTTPException 500: If SAS token generation fails
        
    Example Response:
        {
            "secure_url": "https://storage.blob.core.windows.net/lease-uploads/doc.pdf?sv=2021...",
            "expires_at": "2024-10-09T20:30:00Z",
            "expires_in_seconds": 3600
        }
    """
    try:
        # Get document and verify it belongs to the specified lease
        document = await get_lease_document_by_id(
            lease_id=lease_id,
            document_id=document_id,
            current_user=current_user,
            session=session
        )
        
        # Get client IP for optional restriction (currently not enforced)
        client_ip = request.client.host if request.client else None
        
        # Generate secure URL with SAS token
        # Note: document.id is guaranteed to exist (primary key from database)
        secure_url_data = await generate_secure_document_url(
            blob_url=document.file_path,
            user_id=current_user.id,
            document_id=document.id or document_id,  # Fallback for type checker
            expires_in_hours=None,  # Use config default (1 hour)
            client_ip=None  # Set to client_ip to enable IP restriction
        )
        
        return secure_url_data
        
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except ValueError as ve:
        logger.error(f"Configuration error generating SAS token: {ve}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error. Please contact support."
        )
    except Exception:
        logger.exception(f"Error generating secure URL for document {document_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate secure URL. Please contact support."
        )


@router.post("/analyze", response_model=LeaseAnalysisResponse)
async def analyze_lease_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Analyze a lease document (check user can create leases)."""
    result = await analyze_lease(file, current_user)
    return result


@router.post("/parse", response_model=LeaseAnalysisResponse)
async def parse_lease_endpoint(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Parses a lease PDF file, extracting structured lease information using LLM analysis.
    
    Checks that the user is an Admin or Landlord before processing.
    Reads the uploaded PDF, extracts its text, and analyzes it with an external language model utility
    to identify key lease details such as rent, deposit, dates, tenant name, and unit.
    Safely parses currency and date fields, returning a structured response.
    Raises HTTP 400 for empty files, HTTP 403 for unauthorized users, HTTP 422 for parsing errors, and HTTP 500 for unexpected failures.
    
    Returns:
        LeaseAnalysisResponse: Structured lease data extracted from the document.
    """
    result = await parse_lease(file, current_user)
    return result


@router.delete("/{lease_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lease_endpoint(
    lease_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    """
    Deletes a lease by ID after verifying user permissions.
    
    If the lease is active, revokes associated side effects (such as updating tenant and property unit records) before deletion.
    Lease documents are deleted via cascading, and related payments have their lease reference set to NULL
    
    Raises an HTTP 409 error if the lease cannot be deleted due to foreign key constraints, or HTTP 500 for other database errors.
    """
    await delete_lease(lease_id, current_user, session)
