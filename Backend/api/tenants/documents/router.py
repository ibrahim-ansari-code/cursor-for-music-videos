"""
Tenant Documents API Router

REST API endpoints for tenant document management.

Endpoints:
- GET    /api/tenants/{tenant_id}/documents - List documents
- POST   /api/tenants/{tenant_id}/documents - Upload document
- GET    /api/tenants/{tenant_id}/documents/{document_id} - Get document details
- GET    /api/tenants/{tenant_id}/documents/{document_id}/secure-url - Get secure download URL
- PATCH  /api/tenants/{tenant_id}/documents/{document_id} - Update metadata
- DELETE /api/tenants/{tenant_id}/documents/{document_id} - Delete document
- GET    /api/document-types/taxonomy - Get category/type hierarchy
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.database import get_session
from Backend.api.auth import get_current_user
from Backend.models.user import User
from Backend.models.enums import DocumentCategory, DocumentStatus

from .schemas import (
    DocumentResponse,
    DocumentListResponse,
    DocumentUpdateRequest,
    TaxonomyResponse,
    SecureUrlResponse,
    CategoryInfo,
)
from . import service
from .helpers import get_all_categories


logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(
    prefix="/tenants",
    tags=["Tenant Documents"],
)

# Separate router for taxonomy endpoint (no tenant_id in path)
taxonomy_router = APIRouter(
    prefix="/document-types",
    tags=["Tenant Documents"],
)


# ============================================================================
# LIST DOCUMENTS
# ============================================================================

@router.get("/{tenant_id}/documents", response_model=DocumentListResponse)
async def list_tenant_documents(
    tenant_id: int,
    category: Optional[DocumentCategory] = Query(None, description="Filter by category"),
    document_type: Optional[str] = Query(None, description="Filter by specific document type"),
    status: Optional[DocumentStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in file name and notes"),
    limit: int = Query(20, ge=1, le=100, description="Number of documents per page"),
    offset: int = Query(0, ge=0, description="Number of documents to skip"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    List documents for a tenant with optional filtering and pagination.
    
    **Access Control**: User must own the tenant.
    
    **Query Parameters**:
    - `category`: Filter by document category (e.g., insurance_risk)
    - `document_type`: Filter by specific type (e.g., tenant_insurance_certificate)
    - `status`: Filter by status (pending/verified/rejected/expired)
    - `search`: Search in file names and notes (case-insensitive)
    - `limit`: Number of documents per page (default 20, max 100)
    - `offset`: Number of documents to skip for pagination (default 0)
    
    **Returns**: Paginated list of documents with metadata and computed fields.
    """
    return await service.list_documents(
        session=session,
        tenant_id=tenant_id,
        user_id=current_user.id,
        category=category,
        document_type=document_type,
        status_filter=status,
        search=search,
        limit=limit,
        offset=offset,
    )


# ============================================================================
# UPLOAD DOCUMENT
# ============================================================================

@router.post("/{tenant_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_tenant_document(
    tenant_id: int,
    file: UploadFile = File(..., description="Document file to upload"),
    document_category: DocumentCategory = Form(..., description="Document category"),
    document_type: str = Form(..., description="Specific document type"),
    tags: Optional[str] = Form(None, description="Comma-separated tags"),
    notes: Optional[str] = Form(None, description="Additional notes (max 280 chars)"),
    expiry_date: Optional[str] = Form(None, description="Expiry date (YYYY-MM-DD format)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload a new document for a tenant.
    
    **Access Control**: User must own the tenant.
    
    **Form Data**:
    - `file`: File to upload (PDF, DOCX, images up to 25MB)
    - `document_category`: Category enum value (required)
    - `document_type`: Specific type within category (required)
    - `tags`: Comma-separated tags (optional, max 10)
    - `notes`: Additional notes (optional, max 280 chars)
    - `expiry_date`: Expiration date in YYYY-MM-DD format (optional)
    
    **Process**:
    1. Validates document type exists in category
    2. Uploads file to Azure Blob Storage
    3. Creates database record
    4. Returns document details with secure URL
    
    **Returns**: Document details including computed expiry info.
    """
    # Parse tags from comma-separated string
    tags_list = [tag.strip() for tag in tags.split(",")] if tags else None
    
    # Parse expiry_date from string
    expiry_date_parsed = None
    if expiry_date:
        from datetime import datetime as dt
        try:
            expiry_date_parsed = dt.strptime(expiry_date, "%Y-%m-%d").date()
        except ValueError:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid expiry_date format. Use YYYY-MM-DD."
            )
    
    return await service.create_document(
        session=session,
        tenant_id=tenant_id,
        user_id=current_user.id,
        file=file,
        document_category=document_category,
        document_type=document_type,
        tags=tags_list,
        notes=notes,
        expiry_date=expiry_date_parsed,
    )


# ============================================================================
# GET DOCUMENT DETAILS
# ============================================================================

@router.get("/{tenant_id}/documents/{document_id}", response_model=DocumentResponse)
async def get_tenant_document(
    tenant_id: int,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Get details of a specific tenant document.
    
    **Access Control**: User must own the tenant.
    
    **Returns**: Document details including:
    - File metadata (name, size, type, path)
    - Classification (category, type)
    - Organization (tags, notes)
    - Compliance (expiry date, status)
    - Computed fields (is_expired, days_until_expiry)
    """
    return await service.get_document(
        session=session,
        tenant_id=tenant_id,
        document_id=document_id,
        user_id=current_user.id,
    )


# ============================================================================
# GET SECURE DOWNLOAD URL
# ============================================================================

@router.get("/{tenant_id}/documents/{document_id}/secure-url", response_model=SecureUrlResponse)
async def get_document_secure_url(
    tenant_id: int,
    document_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Generate time-limited secure URL for document access.
    
    **Access Control**: User must own the tenant.
    
    **Security Features**:
    - Time-limited SAS token (expires in 1 hour)
    - Read-only permission
    - HTTPS enforced
    - Audit logging
    
    **Returns**: Secure URL with expiration info.
    
    **Usage**: Use the `secure_url` to download or preview the document
    in browser. URL expires after 1 hour for security.
    """
    # Get client IP for audit trail (optional)
    client_ip = request.client.host if request.client else None
    
    return await service.generate_document_secure_url(
        session=session,
        tenant_id=tenant_id,
        document_id=document_id,
        user_id=current_user.id,
        expires_in_hours=1,
        client_ip=client_ip,
    )


# ============================================================================
# UPDATE DOCUMENT METADATA
# ============================================================================

@router.patch("/{tenant_id}/documents/{document_id}", response_model=DocumentResponse)
async def update_tenant_document(
    tenant_id: int,
    document_id: UUID,
    update_data: DocumentUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Update document metadata (tags, notes, status, expiry_date).
    
    **Access Control**: User must own the tenant.
    
    **Note**: File itself cannot be updated. Upload a new document instead.
    
    **Request Body**: All fields optional (only provided fields updated):
    - `tags`: Updated tags list (replaces existing)
    - `notes`: Updated notes (replaces existing, max 280 chars)
    - `status`: Updated workflow status (pending/verified/rejected/expired)
    - `expiry_date`: Updated expiry date (or null to remove)
    
    **Returns**: Updated document details.
    """
    return await service.update_document(
        session=session,
        tenant_id=tenant_id,
        document_id=document_id,
        user_id=current_user.id,
        update_data=update_data,
    )


# ============================================================================
# DELETE DOCUMENT
# ============================================================================

@router.delete("/{tenant_id}/documents/{document_id}", status_code=204)
async def delete_tenant_document(
    tenant_id: int,
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a tenant document (file and database record).
    
    **Access Control**: User must own the tenant.
    
    **Process**:
    1. Deletes file from Azure Blob Storage
    2. Deletes database record
    3. Returns 204 No Content on success
    
    **Warning**: This action cannot be undone. The file will be permanently
    deleted from storage.
    """
    await service.delete_document(
        session=session,
        tenant_id=tenant_id,
        document_id=document_id,
        user_id=current_user.id,
    )
    
    return None  # 204 No Content


# ============================================================================
# GET DOCUMENT TAXONOMY
# ============================================================================

@taxonomy_router.get("/taxonomy", response_model=TaxonomyResponse)
async def get_document_taxonomy():
    """
    Get complete document category and type taxonomy.
    
    **No Authentication Required** - This is static reference data.
    
    **Returns**: Complete hierarchy of:
    - 14 document categories
    - 200+ specific document types
    - Category metadata (labels, icons, expiry requirements)
    
    **Usage**: Use this endpoint to populate category and type dropdowns
    in the frontend. The taxonomy is static and can be cached long-term.
    
    **Example Response**:
    ```json
    {
      "categories": [
        {
          "key": "insurance_risk",
          "label": "Insurance & Risk",
          "types": ["tenant_insurance_certificate", "tenant_insurance_renewal", ...],
          "requires_expiry": true,
          "icon": "Shield"
        },
        ...
      ]
    }
    ```
    """
    categories_data = get_all_categories()
    
    category_objects = [
        CategoryInfo(
            key=cat["key"],
            label=cat["label"],
            types=cat["types"],
            requires_expiry=cat["requires_expiry"],
            icon=cat["icon"],
        )
        for cat in categories_data
    ]
    
    return TaxonomyResponse(categories=category_objects)


# ============================================================================
# EXPORTS
# ============================================================================

# Export both routers for registration in main app
__all__ = ["router", "taxonomy_router"]

