"""
Unit tests for tenant documents service secure URL generation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.tenants.documents.service import generate_document_secure_url
from Backend.models.user import User
from Backend.models.tenant_documents import TenantDocument

pytestmark = pytest.mark.unit


def create_test_user():
    """Helper to create test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type="LANDLORD",
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_email_verified=True
    )


@pytest.mark.asyncio
async def test_generate_document_secure_url_success(mocker):
    """Test successful tenant document secure URL generation."""
    user = create_test_user()
    session = AsyncMock(spec=AsyncSession)
    tenant_id = 123
    document_id = uuid4()
    
    # Mock document
    mock_document = MagicMock(spec=TenantDocument)
    mock_document.file_path = "https://briklicorestorage.blob.core.windows.net/tenant-documents/doc.pdf"
    
    # Mock access check
    mocker.patch(
        "Backend.api.tenants.documents.service.check_user_access_to_tenant",
        new=AsyncMock()
    )
    
    # Mock document check
    mocker.patch(
        "Backend.api.tenants.documents.service.check_document_belongs_to_tenant",
        new=AsyncMock(return_value=mock_document)
    )
    
    # Mock SAS generation
    mock_result = {
        "secure_url": f"{mock_document.file_path}?sv=2021&sig=test",
        "expires_at": "2024-10-09T20:30:00Z",
        "expires_in_seconds": 3600
    }
    mocker.patch(
        "Backend.api.tenants.documents.service.generate_secure_document_url",
        new=AsyncMock(return_value=mock_result)
    )
    
    result = await generate_document_secure_url(
        session=session,
        tenant_id=tenant_id,
        document_id=document_id,
        user_id=user.id,
        expires_in_hours=1
    )
    
    assert "secure_url" in result


@pytest.mark.asyncio
async def test_generate_document_secure_url_not_found(mocker):
    """Test tenant document secure URL when file not found."""
    user = create_test_user()
    session = AsyncMock(spec=AsyncSession)
    tenant_id = 123
    document_id = uuid4()
    
    mock_document = MagicMock(spec=TenantDocument)
    mock_document.file_path = "https://briklicorestorage.blob.core.windows.net/tenant-documents/deleted.pdf"
    
    mocker.patch(
        "Backend.api.tenants.documents.service.check_user_access_to_tenant",
        new=AsyncMock()
    )
    mocker.patch(
        "Backend.api.tenants.documents.service.check_document_belongs_to_tenant",
        new=AsyncMock(return_value=mock_document)
    )
    mocker.patch(
        "Backend.api.tenants.documents.service.generate_secure_document_url",
        new=AsyncMock(side_effect=ValueError("Document file not found in storage"))
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_document_secure_url(
            session=session,
            tenant_id=tenant_id,
            document_id=document_id,
            user_id=user.id
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_generate_document_secure_url_invalid_url(mocker):
    """Test tenant document secure URL with invalid URL."""
    user = create_test_user()
    session = AsyncMock(spec=AsyncSession)
    tenant_id = 123
    document_id = uuid4()
    
    mock_document = MagicMock(spec=TenantDocument)
    mock_document.file_path = "https://example.com/not-azure.pdf"
    
    mocker.patch(
        "Backend.api.tenants.documents.service.check_user_access_to_tenant",
        new=AsyncMock()
    )
    mocker.patch(
        "Backend.api.tenants.documents.service.check_document_belongs_to_tenant",
        new=AsyncMock(return_value=mock_document)
    )
    mocker.patch(
        "Backend.api.tenants.documents.service.generate_secure_document_url",
        new=AsyncMock(side_effect=ValueError("Invalid URL"))
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_document_secure_url(
            session=session,
            tenant_id=tenant_id,
            document_id=document_id,
            user_id=user.id
        )
    
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_generate_document_secure_url_server_error(mocker):
    """Test tenant document secure URL with server error."""
    user = create_test_user()
    session = AsyncMock(spec=AsyncSession)
    tenant_id = 123
    document_id = uuid4()
    
    mock_document = MagicMock(spec=TenantDocument)
    mock_document.file_path = "https://briklicorestorage.blob.core.windows.net/tenant-documents/doc.pdf"
    
    mocker.patch(
        "Backend.api.tenants.documents.service.check_user_access_to_tenant",
        new=AsyncMock()
    )
    mocker.patch(
        "Backend.api.tenants.documents.service.check_document_belongs_to_tenant",
        new=AsyncMock(return_value=mock_document)
    )
    mocker.patch(
        "Backend.api.tenants.documents.service.generate_secure_document_url",
        new=AsyncMock(side_effect=Exception("Unexpected error"))
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_document_secure_url(
            session=session,
            tenant_id=tenant_id,
            document_id=document_id,
            user_id=user.id
        )
    
    assert exc_info.value.status_code == 500

