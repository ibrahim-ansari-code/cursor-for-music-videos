"""
Tenant Documents Service Layer

Business logic for tenant document management including:
- CRUD operations
- File upload/download/deletion
- Access control
- Expiry calculation
- Secure URL generation

All functions use async/await pattern and implement proper error handling.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import UploadFile, HTTPException, status
from sqlmodel import select, func, and_, or_, col
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from Backend.models.tenant_documents import TenantDocument
from Backend.models.tenant import Tenant
from Backend.models.enums import DocumentCategory, DocumentStatus
from Backend.api.tenants.documents.schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUpdateRequest,
)
from Backend.api.tenants.documents.helpers import validate_document_type
from Backend.utils.azure_blob import (
    upload_tenant_document_to_blob,
    delete_blob_by_url,
    generate_secure_document_url,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ACCESS CONTROL
# ============================================================================

async def check_user_access_to_tenant(
    session: AsyncSession,
    user_id: UUID,
    tenant_id: int
) -> Tenant:
    """
    Verify user has access to a tenant.
    
    Args:
        session: Database session
        user_id: Current user's UUID
        tenant_id: Tenant ID to check
        
    Returns:
        Tenant object if access granted
        
    Raises:
        HTTPException 404: Tenant not found
        HTTPException 403: User doesn't have access to tenant
    """
    statement = select(Tenant).where(
        and_(
            Tenant.id == tenant_id,
            Tenant.landlord_id == user_id
        )
    )
    result = await session.execute(statement)
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        # Check if tenant exists at all
        exists_statement = select(Tenant).where(Tenant.id == tenant_id)
        exists_result = await session.execute(exists_statement)
        tenant_exists = exists_result.scalar_one_or_none()
        
        if tenant_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this tenant's documents"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with ID {tenant_id} not found"
            )
    
    return tenant


async def check_document_belongs_to_tenant(
    session: AsyncSession,
    document_id: UUID,
    tenant_id: int
) -> TenantDocument:
    """
    Verify a document belongs to a specific tenant.
    
    Args:
        session: Database session
        document_id: Document UUID to check
        tenant_id: Tenant ID to verify against
        
    Returns:
        TenantDocument object if check passes
        
    Raises:
        HTTPException 404: Document not found or doesn't belong to tenant
    """
    statement = select(TenantDocument).where(
        and_(
            TenantDocument.id == document_id,
            TenantDocument.tenant_id == tenant_id
        )
    )
    result = await session.execute(statement)
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found for this tenant"
        )
    
    return document


# ============================================================================
# COMPUTED FIELDS
# ============================================================================

def calculate_expiry_info(expiry_date: Optional[date]) -> Tuple[bool, Optional[int]]:
    """
    Calculate expiry status and days until expiry.
    
    Args:
        expiry_date: Document expiry date (or None)
        
    Returns:
        Tuple of (is_expired, days_until_expiry)
        - is_expired: True if past expiry date
        - days_until_expiry: Days remaining (negative if expired, None if no expiry)
    """
    if not expiry_date:
        return False, None
    
    today = date.today()
    days_until = (expiry_date - today).days
    is_expired = days_until < 0
    
    return is_expired, days_until


def enrich_document_response(document: TenantDocument) -> DocumentResponse:
    """
    Convert TenantDocument to DocumentResponse with computed fields.
    
    Args:
        document: TenantDocument SQLModel instance
        
    Returns:
        DocumentResponse with all fields including computed ones
    """
    is_expired, days_until = calculate_expiry_info(document.expiry_date)
    
    return DocumentResponse(
        id=document.id,
        tenant_id=document.tenant_id,
        file_name=document.file_name,
        file_path=document.file_path,
        file_size=document.file_size,
        file_type=document.file_type,
        document_category=document.document_category,
        document_type=document.document_type,
        tags=document.tags or [],
        notes=document.notes,
        expiry_date=document.expiry_date,
        status=document.status,
        uploaded_by=document.uploaded_by,
        uploaded_at=document.uploaded_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
        is_expired=is_expired,
        days_until_expiry=days_until,
    )


# ============================================================================
# CREATE OPERATIONS
# ============================================================================

async def create_document(
    session: AsyncSession,
    tenant_id: int,
    user_id: UUID,
    file: UploadFile,
    document_category: DocumentCategory,
    document_type: str,
    tags: Optional[List[str]] = None,
    notes: Optional[str] = None,
    expiry_date: Optional[date] = None,
) -> DocumentResponse:
    """
    Create a new tenant document with file upload.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
        user_id: Current user's UUID (for upload and access control)
        file: Uploaded file
        document_category: Document category enum
        document_type: Specific document type
        tags: Optional list of tags
        notes: Optional notes
        expiry_date: Optional expiry date
        
    Returns:
        DocumentResponse with created document details
        
    Raises:
        HTTPException 400: Invalid document type for category
        HTTPException 403: User doesn't have access to tenant
        HTTPException 500: File upload or database error
    """
    # Check user has access to tenant
    await check_user_access_to_tenant(session, user_id, tenant_id)
    
    # Validate document type exists in category
    if not validate_document_type(document_category, document_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid document_type '{document_type}' for category '{document_category.value}'"
        )

    file_url = None
    try:
        # Upload file to Azure Blob Storage
        file_url = await upload_tenant_document_to_blob(file, user_id)
        logger.info(f"Uploaded document to Azure Blob: {file_url}")

        # Create database record
        document = TenantDocument(
            tenant_id=tenant_id,
            uploaded_by=user_id,
            file_name=file.filename or "untitled",
            file_path=file_url,
            file_size=file.size or 0,
            file_type=file.content_type or "application/octet-stream",
            document_category=document_category,
            document_type=document_type,
            tags=tags or [],
            notes=notes,
            expiry_date=expiry_date,
            status=DocumentStatus.PENDING,  # Default status
        )

        session.add(document)
        await session.commit()
        await session.refresh(document)

        logger.info(
            f"Created document {document.id} for tenant {tenant_id} "
            f"(category: {document_category.value}, type: {document_type})"
        )

        return enrich_document_response(document)

    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Database integrity error creating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create document due to database constraint violation"
        )
    except Exception as e:
        await session.rollback()
        logger.error(f"Error creating document: {e}")

        # Clean up orphan blob if it was uploaded before DB error
        if file_url:
            try:
                await delete_blob_by_url(file_url)
                logger.info(f"Cleaned up orphan blob after DB error: {file_url}")
            except Exception as delete_e:
                logger.error(f"Failed to clean up orphan blob {file_url}: {delete_e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}"
        )


# ============================================================================
# READ OPERATIONS
# ============================================================================

async def list_documents(
    session: AsyncSession,
    tenant_id: int,
    user_id: UUID,
    category: Optional[DocumentCategory] = None,
    document_type: Optional[str] = None,
    status_filter: Optional[DocumentStatus] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> DocumentListResponse:
    """
    List documents for a tenant with optional filtering and pagination.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
        user_id: Current user's UUID (for access control)
        category: Filter by category (optional)
        document_type: Filter by specific type (optional)
        status_filter: Filter by status (optional)
        search: Search in file_name and notes (optional)
        limit: Number of documents per page (default 20)
        offset: Number of documents to skip (default 0)
        
    Returns:
        DocumentListResponse with paginated results
        
    Raises:
        HTTPException 403: User doesn't have access to tenant
    """
    # Check user has access to tenant
    await check_user_access_to_tenant(session, user_id, tenant_id)
    
    # Build base query
    statement = select(TenantDocument).where(TenantDocument.tenant_id == tenant_id)
    
    # Apply filters
    if category:
        statement = statement.where(TenantDocument.document_category == category)
    
    if document_type:
        statement = statement.where(TenantDocument.document_type == document_type)
    
    if status_filter:
        statement = statement.where(TenantDocument.status == status_filter)
    
    if search:
        # Search in file_name and notes (case-insensitive)
        search_pattern = f"%{search}%"
        statement = statement.where(
            or_(
                col(TenantDocument.file_name).ilike(search_pattern),
                col(TenantDocument.notes).ilike(search_pattern),
            )
        )
    
    # Get total count (before pagination)
    count_statement = select(func.count()).select_from(statement.subquery())
    count_result = await session.execute(count_statement)
    total = count_result.scalar_one()
    
    # Apply sorting and pagination
    statement = statement.order_by(col(TenantDocument.uploaded_at).desc())
    statement = statement.offset(offset).limit(limit)
    
    # Execute query
    result = await session.execute(statement)
    documents = result.scalars().all()
    
    # Enrich with computed fields
    enriched_documents = [enrich_document_response(doc) for doc in documents]
    
    return DocumentListResponse(
        documents=enriched_documents,
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_document(
    session: AsyncSession,
    tenant_id: int,
    document_id: UUID,
    user_id: UUID,
) -> DocumentResponse:
    """
    Get details of a specific document.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
        document_id: Document UUID
        user_id: Current user's UUID (for access control)
        
    Returns:
        DocumentResponse with document details
        
    Raises:
        HTTPException 403: User doesn't have access to tenant
        HTTPException 404: Document not found
    """
    # Check user has access to tenant
    await check_user_access_to_tenant(session, user_id, tenant_id)
    
    # Get document and verify it belongs to tenant
    document = await check_document_belongs_to_tenant(session, document_id, tenant_id)
    
    return enrich_document_response(document)


# ============================================================================
# UPDATE OPERATIONS
# ============================================================================

async def update_document(
    session: AsyncSession,
    tenant_id: int,
    document_id: UUID,
    user_id: UUID,
    update_data: DocumentUpdateRequest,
) -> DocumentResponse:
    """
    Update document metadata (tags, notes, status, expiry_date).
    
    Note: File itself cannot be updated. Upload new document instead.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
        document_id: Document UUID
        user_id: Current user's UUID (for access control)
        update_data: Fields to update
        
    Returns:
        DocumentResponse with updated document
        
    Raises:
        HTTPException 403: User doesn't have access to tenant
        HTTPException 404: Document not found
    """
    # Check user has access to tenant
    await check_user_access_to_tenant(session, user_id, tenant_id)
    
    # Get document and verify it belongs to tenant
    document = await check_document_belongs_to_tenant(session, document_id, tenant_id)
    
    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(document, field, value)
    
    # Update timestamp
    document.updated_at = datetime.utcnow()
    
    try:
        session.add(document)
        await session.commit()
        await session.refresh(document)
        
        logger.info(f"Updated document {document_id} for tenant {tenant_id}")
        
        return enrich_document_response(document)
        
    except IntegrityError as e:
        await session.rollback()
        logger.error(f"Database integrity error updating document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document due to database constraint violation"
        )


# ============================================================================
# DELETE OPERATIONS
# ============================================================================

async def delete_document(
    session: AsyncSession,
    tenant_id: int,
    document_id: UUID,
    user_id: UUID,
) -> None:
    """
    Delete a document (file and database record).
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
        document_id: Document UUID
        user_id: Current user's UUID (for access control)
        
    Raises:
        HTTPException 403: User doesn't have access to tenant
        HTTPException 404: Document not found
        HTTPException 500: Failed to delete file or database record
    """
    # Check user has access to tenant
    await check_user_access_to_tenant(session, user_id, tenant_id)

    # Get document and verify it belongs to tenant
    document = await check_document_belongs_to_tenant(session, document_id, tenant_id)

    try:
        file_path_to_delete = document.file_path

        # 1. Delete database record first (ensures data consistency)
        await session.delete(document)
        await session.commit()

        logger.info(f"Deleted document record {document_id} for tenant {tenant_id}")

        # 2. Delete from Azure Blob Storage after successful DB deletion
        blob_deleted = await delete_blob_by_url(file_path_to_delete)
        if not blob_deleted:
            logger.warning(
                f"Database record for document {document_id} deleted, "
                f"but failed to delete blob: {file_path_to_delete}"
            )

        logger.info(
            f"Successfully processed deletion for document {document_id} "
            f"(blob_deleted: {blob_deleted})"
        )

    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


# ============================================================================
# SECURE URL GENERATION
# ============================================================================

async def generate_document_secure_url(
    session: AsyncSession,
    tenant_id: int,
    document_id: UUID,
    user_id: UUID,
    expires_in_hours: int = 1,
    client_ip: Optional[str] = None,
) -> dict:
    """
    Generate time-limited SAS token URL for document access.
    
    Args:
        session: Database session
        tenant_id: Tenant UUID
        document_id: Document UUID
        user_id: Current user's UUID (for access control)
        expires_in_hours: Token expiration time (default 1 hour)
        client_ip: Optional client IP for restriction
        
    Returns:
        Dict with secure_url, expires_at, expires_in_seconds
        
    Raises:
        HTTPException 403: User doesn't have access to tenant
        HTTPException 404: Document not found
        HTTPException 500: Failed to generate secure URL
    """
    # Check user has access to tenant
    await check_user_access_to_tenant(session, user_id, tenant_id)
    
    # Get document and verify it belongs to tenant
    document = await check_document_belongs_to_tenant(session, document_id, tenant_id)
    
    try:
        # Generate secure URL with SAS token
        url_data = await generate_secure_document_url(
            blob_url=document.file_path,
            user_id=user_id,
            document_id=str(document_id),  # UUID string for logging
            expires_in_hours=expires_in_hours,
            client_ip=client_ip,
        )
        
        return url_data
        
    except Exception as e:
        logger.error(f"Error generating secure URL for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate secure URL: {str(e)}"
        )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "check_user_access_to_tenant",
    "check_document_belongs_to_tenant",
    "create_document",
    "list_documents",
    "get_document",
    "update_document",
    "delete_document",
    "generate_document_secure_url",
]

