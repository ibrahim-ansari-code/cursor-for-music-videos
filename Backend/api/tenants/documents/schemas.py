"""
Tenant Documents Pydantic Schemas

Request and response models for tenant document API endpoints.
All models use strong typing with DocumentCategory and DocumentStatus enums.

Schemas:
- DocumentUploadRequest: Upload new document (multipart form data)
- DocumentResponse: Single document details
- DocumentListResponse: Paginated list of documents
- DocumentUpdateRequest: Update document metadata
- CategoryInfo: Document category information
- TaxonomyResponse: Complete category/type hierarchy
"""

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

from Backend.models.enums import DocumentCategory, DocumentStatus


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """
    Request schema for uploading a new tenant document.

    Note: This is used with multipart/form-data uploads where the file
    is separate from these metadata fields.

    Fields:
    - document_name: Optional, user-friendly name (defaults to file name)
    - document_category: Required, strongly typed enum
    - document_type: Required, specific type within category
    - tags: Optional, max 10 tags
    - notes: Optional, max 280 characters
    - expiry_date: Optional, for compliance tracking
    """

    document_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User-friendly document name (defaults to file name if not provided)"
    )
    document_category: DocumentCategory = Field(
        ...,
        description="Category from 14 predefined types (strongly typed enum)"
    )
    document_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Specific document type within category"
    )
    tags: Optional[List[str]] = Field(
        default=[],
        max_length=10,
        description="Flexible tags for organization (max 10)"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=280,
        description="Additional notes about document (max 280 chars)"
    )
    expiry_date: Optional[date] = Field(
        default=None,
        description="Expiration date for compliance tracking"
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> List[str]:
        """
        Validate and clean tags list.
        
        - Removes duplicates
        - Strips whitespace
        - Removes empty strings
        - Enforces max 10 tags
        """
        if not v:
            return []
        
        # Strip whitespace and remove empty strings
        cleaned = [tag.strip() for tag in v if tag and tag.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for tag in cleaned:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique.append(tag)
        
        # Enforce max 10 tags
        if len(unique) > 10:
            raise ValueError("Maximum 10 tags allowed")
        
        return unique
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate notes length.
        
        - Strips whitespace
        - Enforces max 280 characters
        """
        if v:
            v = v.strip()
            if len(v) > 280:
                raise ValueError("Notes must not exceed 280 characters")
            return v if v else None
        return None
    
    class Config:
        json_schema_extra: dict = {
            "example": {
                "document_name": "2025 Liability Insurance Certificate",
                "document_category": "insurance_risk",
                "document_type": "tenant_insurance_certificate",
                "tags": ["liability", "annual"],
                "notes": "Renewed for 2025",
                "expiry_date": "2025-12-31"
            }
        }


class DocumentUpdateRequest(BaseModel):
    """
    Request schema for updating document metadata.

    All fields are optional - only provided fields will be updated.
    File itself cannot be changed (upload new document instead).

    Fields:
    - document_name: Update user-friendly name
    - tags: Update tags list
    - notes: Update notes
    - status: Change workflow status
    - expiry_date: Update or remove expiry date
    """

    document_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated user-friendly document name"
    )
    tags: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Updated tags list (replaces existing)"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=280,
        description="Updated notes (replaces existing)"
    )
    status: Optional[DocumentStatus] = Field(
        default=None,
        description="Updated workflow status"
    )
    expiry_date: Optional[date] = Field(
        default=None,
        description="Updated expiry date (or null to remove)"
    )
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate tags if provided (same logic as DocumentUploadRequest)"""
        if v is None:
            return None
        
        # Strip whitespace and remove empty strings
        cleaned = [tag.strip() for tag in v if tag and tag.strip()]
        
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for tag in cleaned:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique.append(tag)
        
        # Enforce max 10 tags
        if len(unique) > 10:
            raise ValueError("Maximum 10 tags allowed")
        
        return unique if unique else None
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate notes if provided"""
        if v is not None:
            v = v.strip()
            if len(v) > 280:
                raise ValueError("Notes must not exceed 280 characters")
            return v if v else None
        return None
    
    class Config:
        json_schema_extra: dict = {
            "example": {
                "tags": ["liability", "annual", "updated"],
                "notes": "Updated policy for 2025",
                "status": "verified",
                "expiry_date": "2025-12-31"
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class DocumentResponse(BaseModel):
    """
    Response schema for tenant document details.

    Includes all database fields plus computed fields:
    - is_expired: Whether document has passed expiry date
    - days_until_expiry: Days remaining until expiry (or None)
    """

    # Core fields
    id: UUID
    tenant_id: int  # INTEGER foreign key to tenants.id
    document_name: Optional[str] = Field(
        default=None,
        description="User-friendly document name"
    )
    file_name: str
    file_path: str
    file_size: int
    file_type: str

    # Classification (strongly typed)
    document_category: DocumentCategory
    document_type: str

    # Organization
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

    # Compliance
    expiry_date: Optional[date] = None
    status: DocumentStatus

    # Audit trail
    uploaded_by: UUID  # UUID foreign key to users.id
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime

    # Computed fields (calculated at runtime)
    is_expired: bool = Field(
        default=False,
        description="Whether document has passed expiry date"
    )
    days_until_expiry: Optional[int] = Field(
        default=None,
        description="Days remaining until expiry (negative if expired)"
    )

    class Config:
        from_attributes = True  # For SQLModel compatibility
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "document_name": "2025 Liability Insurance Certificate",
                "file_name": "Insurance_Certificate_2025.pdf",
                "file_path": "https://storage.blob.core.windows.net/tenant-documents/user_789.../insurance.pdf",
                "file_size": 245680,
                "file_type": "application/pdf",
                "document_category": "insurance_risk",
                "document_type": "tenant_insurance_certificate",
                "tags": ["liability", "annual"],
                "notes": "Renewed for 2025",
                "expiry_date": "2025-12-31",
                "status": "verified",
                "uploaded_by": "789e4567-e89b-12d3-a456-426614174000",
                "uploaded_at": "2025-01-15T10:30:00Z",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z",
                "is_expired": False,
                "days_until_expiry": 350
            }
        }


class DocumentListResponse(BaseModel):
    """
    Response schema for paginated list of documents.
    
    Used for GET /api/tenants/{tenant_id}/documents
    """
    
    documents: List[DocumentResponse]
    total: int = Field(description="Total number of documents matching filters")
    limit: int = Field(description="Number of documents per page")
    offset: int = Field(description="Number of documents skipped")
    
    class Config:
        json_schema_extra: dict = {
            "example": {
                "documents": [
                    # ... list of DocumentResponse objects
                ],
                "total": 42,
                "limit": 20,
                "offset": 0
            }
        }


# ============================================================================
# TAXONOMY SCHEMAS
# ============================================================================

class CategoryInfo(BaseModel):
    """
    Information about a document category.
    
    Used in taxonomy endpoint to describe available categories
    and their document types.
    """
    
    key: str = Field(description="Category enum value (e.g., 'insurance_risk')")
    label: str = Field(description="Human-readable label (e.g., 'Insurance & Risk')")
    types: List[str] = Field(description="List of specific document types in category")
    requires_expiry: bool = Field(description="Whether category typically requires expiry tracking")
    icon: str = Field(description="Icon name for UI display (Heroicons format)")
    
    class Config:
        json_schema_extra: dict = {
            "example": {
                "key": "insurance_risk",
                "label": "Insurance & Risk",
                "types": [
                    "tenant_insurance_certificate",
                    "tenant_insurance_renewal",
                    "business_interruption_policy",
                    "general_liability_certificate"
                ],
                "requires_expiry": True,
                "icon": "Shield"
            }
        }


class TaxonomyResponse(BaseModel):
    """
    Response schema for document taxonomy endpoint.
    
    Returns complete hierarchy of all 14 categories with their
    200+ document types. Used to populate frontend dropdowns.
    """
    
    categories: List[CategoryInfo]
    
    class Config:
        json_schema_extra: dict = {
            "example": {
                "categories": [
                    # ... list of CategoryInfo objects for all 14 categories
                ]
            }
        }


# ============================================================================
# SECURE URL RESPONSE
# ============================================================================

class SecureUrlResponse(BaseModel):
    """
    Response schema for secure document URL generation.
    
    Returns time-limited SAS token URL for document access.
    Used in GET /api/tenants/{tenant_id}/documents/{document_id}/secure-url
    """
    
    secure_url: str = Field(description="Complete URL with SAS token for secure access")
    expires_at: str = Field(description="ISO datetime when URL expires")
    expires_in_seconds: int = Field(description="Seconds until URL expires")
    
    class Config:
        json_schema_extra: dict = {
            "example": {
                "secure_url": "https://storage.blob.core.windows.net/tenant-documents/doc.pdf?sv=2021-06-08&se=...",
                "expires_at": "2025-10-19T11:30:00Z",
                "expires_in_seconds": 3600
            }
        }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "DocumentUploadRequest",
    "DocumentUpdateRequest",
    "DocumentResponse",
    "DocumentListResponse",
    "CategoryInfo",
    "TaxonomyResponse",
    "SecureUrlResponse",
]

