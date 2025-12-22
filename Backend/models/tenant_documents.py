"""
Tenant Documents SQLModel

Defines the database model for tenant-specific document storage and management.
Supports 14 document categories with 200+ specific types, compliance tracking,
and flexible organization via tags.

Key Features:
- Strong typing with DocumentCategory and DocumentStatus enums
- Expiry date tracking for compliance documents
- Tag-based organization
- Full audit trail (uploaded_by, timestamps)
- Integrates with Azure Blob Storage for file storage
"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import ARRAY, String, Enum as PgEnum

from Backend.models.enums import DocumentCategory, DocumentStatus


class TenantDocument(SQLModel, table=True):
    """
    SQLModel for tenant_documents table.
    
    Stores documents associated with tenants across 14 predefined categories.
    Each document can have tags, notes, expiry tracking, and workflow status.
    
    Relationships:
    - tenant_id: References tenants table (INTEGER, cascade delete)
    - uploaded_by: References users table (UUID, restrict delete for audit trail)
    
    Workflow:
    - Documents start with status=PENDING
    - Can be marked as VERIFIED after review
    - Auto-marked EXPIRED when expiry_date passes (application logic)
    - Can be REJECTED if invalid/not acceptable
    """
    
    __tablename__ = "tenant_documents"
    
    # ===== PRIMARY KEY =====
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # ===== FOREIGN KEYS =====
    tenant_id: int = Field(foreign_key="tenants.id", index=True)
    uploaded_by: UUID = Field(foreign_key="users.id")
    
    # ===== FILE METADATA =====
    document_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="User-friendly document name (defaults to file_name if not provided)"
    )
    file_name: str = Field(max_length=255, description="Original uploaded file name")
    file_path: str = Field(description="Azure Blob Storage URL")
    file_size: int = Field(gt=0, description="File size in bytes")
    file_type: str = Field(max_length=100, description="MIME type (e.g., application/pdf)")
    
    # ===== DOCUMENT CLASSIFICATION (STRONGLY TYPED) =====
    document_category: DocumentCategory = Field(
        sa_column=Column(
            PgEnum(DocumentCategory, name="document_category_enum", create_constraint=False, values_callable=lambda obj: [e.value for e in obj]),
            nullable=False
        ),
        description="Category from 14 predefined types"
    )
    document_type: str = Field(max_length=100, description="Specific type within category (200+ types)")
    
    # ===== ORGANIZATION =====
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(String)),
        description="Flexible tags for organization and filtering"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=280,
        description="Additional notes about document (max 280 chars)"
    )
    
    # ===== COMPLIANCE TRACKING =====
    expiry_date: Optional[date] = Field(
        default=None,
        description="Expiration date for compliance tracking (insurance, licenses, etc.)"
    )
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING,
        sa_column=Column(
            PgEnum(DocumentStatus, name="document_status_enum", create_constraint=False, values_callable=lambda obj: [e.value for e in obj]),
            nullable=False
        ),
        description="Document workflow status"
    )
    
    # ===== TIMESTAMPS =====
    # Note: Using naive UTC datetimes (utcnow) because database columns are TIMESTAMP WITHOUT TIME ZONE
    uploaded_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When document was uploaded (UTC)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp (UTC)"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record last update timestamp (UTC, auto-updated by trigger)"
    )
    
    class Config:
        """SQLModel configuration"""
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
                "uploaded_by": "789e4567-e89b-12d3-a456-426614174000",
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
                "uploaded_at": "2025-01-15T10:30:00Z",
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T10:30:00Z"
            }
        }

