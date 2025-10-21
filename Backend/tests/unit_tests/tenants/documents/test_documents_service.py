"""
Unit tests for Tenant Documents Service Layer - Strategic Coverage
Focuses on critical paths and error handling to maximize coverage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone
from io import BytesIO

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.tenants.documents.service import (
    check_user_access_to_tenant,
    check_document_belongs_to_tenant,
    calculate_expiry_info,
    enrich_document_response,
    create_document,
    list_documents,
    get_document,
    update_document,
    delete_document,
    generate_document_secure_url,
)
from Backend.models.tenant import Tenant
from Backend.models.tenant_documents import TenantDocument
from Backend.models.enums import DocumentCategory, DocumentStatus
from Backend.api.tenants.documents.schemas import DocumentUpdateRequest

pytestmark = pytest.mark.unit


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def mock_tenant():
    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.landlord_id = uuid4()
    return tenant


@pytest.fixture
def mock_document():
    doc = MagicMock(spec=TenantDocument)
    doc.id = uuid4()
    doc.tenant_id = 1
    doc.file_name = "test.pdf"
    doc.file_path = "https://blob.example.com/test.pdf"
    doc.file_size = 1024
    doc.file_type = "application/pdf"
    doc.document_category = DocumentCategory.LEASE_AGREEMENTS
    doc.document_type = "residential_tenancy_agreement"
    doc.tags = ["important"]
    doc.notes = "Test document"
    doc.expiry_date = None
    doc.status = DocumentStatus.PENDING
    doc.uploaded_by = uuid4()
    doc.uploaded_at = datetime.now(timezone.utc)
    doc.created_at = datetime.now(timezone.utc)
    doc.updated_at = datetime.now(timezone.utc)
    return doc


# ============================================================================
# ACCESS CONTROL TESTS (Covers service.py lines 66-92)
# ============================================================================

@pytest.mark.asyncio
async def test_check_user_access_to_tenant_success(mock_session, mock_tenant):
    """Test successful access check - covers line 66-73."""
    user_id = uuid4()
    mock_tenant.landlord_id = user_id

    # Mock query result
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = result

    tenant = await check_user_access_to_tenant(mock_session, user_id, 1)

    assert tenant == mock_tenant
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_user_access_to_tenant_forbidden(mock_session, mock_tenant):
    """Test forbidden access - covers lines 75-85."""
    user_id = uuid4()
    different_user = uuid4()
    mock_tenant.landlord_id = different_user

    # First query returns None (not your tenant)
    result1 = MagicMock()
    result1.scalar_one_or_none.return_value = None

    # Second query returns tenant exists
    result2 = MagicMock()
    result2.scalar_one_or_none.return_value = mock_tenant

    mock_session.execute.side_effect = [result1, result2]

    with pytest.raises(HTTPException) as exc:
        await check_user_access_to_tenant(mock_session, user_id, 1)

    assert exc.value.status_code == 403
    assert "don't have access" in exc.value.detail


@pytest.mark.asyncio
async def test_check_user_access_to_tenant_not_found(mock_session):
    """Test tenant not found - covers lines 87-90."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.side_effect = [result, result]  # Both queries return None

    with pytest.raises(HTTPException) as exc:
        await check_user_access_to_tenant(mock_session, uuid4(), 999)

    assert exc.value.status_code == 404
    assert "not found" in exc.value.detail


@pytest.mark.asyncio
async def test_check_document_belongs_to_tenant_success(mock_session, mock_document):
    """Test document ownership check - covers lines 114-121."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_document
    mock_session.execute.return_value = result

    doc = await check_document_belongs_to_tenant(mock_session, mock_document.id, 1)

    assert doc == mock_document


@pytest.mark.asyncio
async def test_check_document_belongs_to_tenant_not_found(mock_session):
    """Test document not found - covers lines 123-127."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result

    with pytest.raises(HTTPException) as exc:
        await check_document_belongs_to_tenant(mock_session, uuid4(), 1)

    assert exc.value.status_code == 404


# ============================================================================
# COMPUTED FIELDS TESTS (Covers lines 148-170)
# ============================================================================

def test_calculate_expiry_info_no_expiry():
    """Test expiry calculation with no date - covers lines 148-149."""
    is_expired, days_until = calculate_expiry_info(None)
    assert is_expired == False
    assert days_until is None


def test_calculate_expiry_info_expired():
    """Test expired document - covers lines 151-155."""
    past_date = date(2020, 1, 1)
    is_expired, days_until = calculate_expiry_info(past_date)
    assert is_expired == True
    assert days_until < 0


def test_calculate_expiry_info_future():
    """Test future expiry - covers lines 151-155."""
    future_date = date(2030, 12, 31)
    is_expired, days_until = calculate_expiry_info(future_date)
    assert is_expired == False
    assert days_until > 0


def test_enrich_document_response(mock_document):
    """Test document response enrichment - covers lines 168-170."""
    mock_document.expiry_date = date(2030, 12, 31)
    response = enrich_document_response(mock_document)

    assert response.id == mock_document.id
    assert response.is_expired == False
    assert response.days_until_expiry is not None


# ============================================================================
# CREATE DOCUMENT TESTS (Covers lines 230-294 - CRITICAL)
# ============================================================================

@pytest.mark.asyncio
async def test_create_document_success(mock_session):
    """Test successful document creation - covers lines 239-269."""
    user_id = uuid4()
    tenant_id = 1

    # Mock file
    file_content = b"PDF content"
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.size = len(file_content)
    mock_file.content_type = "application/pdf"

    # Mock tenant check
    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = tenant_result

    # Mock refresh to set created_at/updated_at
    async def refresh_side_effect(obj):
        obj.id = uuid4()
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = refresh_side_effect

    with patch("Backend.api.tenants.documents.service.upload_tenant_document_to_blob", new=AsyncMock(return_value="https://blob.example.com/doc.pdf")):
        result = await create_document(
            session=mock_session,
            tenant_id=tenant_id,
            user_id=user_id,
            file=mock_file,
            document_category=DocumentCategory.LEASE_AGREEMENTS,
            document_type="residential_tenancy_agreement",
            tags=["test"],
            notes="Test note",
            expiry_date=None
        )

    assert result.file_name == "test.pdf"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_document_invalid_type(mock_session):
    """Test invalid document type - covers lines 233-237."""
    user_id = uuid4()

    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = result

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"

    with pytest.raises(HTTPException) as exc:
        await create_document(
            session=mock_session,
            tenant_id=1,
            user_id=user_id,
            file=mock_file,
            document_category=DocumentCategory.LEASE_AGREEMENTS,
            document_type="invalid_type_not_in_category",  # Invalid
            tags=None,
            notes=None,
            expiry_date=None
        )

    assert exc.value.status_code == 400
    assert "Invalid document_type" in exc.value.detail


@pytest.mark.asyncio
async def test_create_document_cleanup_orphan_blob(mock_session):
    """Test orphan blob cleanup on DB error - covers lines 283-289."""
    user_id = uuid4()

    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = result

    # Mock commit to raise error (after blob upload)
    mock_session.commit.side_effect = Exception("Database error")

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.size = 1024
    mock_file.content_type = "application/pdf"

    with patch("Backend.api.tenants.documents.service.upload_tenant_document_to_blob", new=AsyncMock(return_value="https://blob.example.com/doc.pdf")), \
         patch("Backend.api.tenants.documents.service.delete_blob_by_url", new=AsyncMock(return_value=True)) as mock_delete:

        with pytest.raises(HTTPException) as exc:
            await create_document(
                session=mock_session,
                tenant_id=1,
                user_id=user_id,
                file=mock_file,
                document_category=DocumentCategory.LEASE_AGREEMENTS,
                document_type="residential_tenancy_agreement"
            )

        assert exc.value.status_code == 500
        # Verify blob cleanup was attempted
        mock_delete.assert_awaited_once_with("https://blob.example.com/doc.pdf")
        mock_session.rollback.assert_awaited_once()


# ============================================================================
# LIST DOCUMENTS TESTS (Covers lines 323-370)
# ============================================================================

@pytest.mark.asyncio
async def test_list_documents_with_filters(mock_session, mock_document):
    """Test list with filters - covers lines 329-346."""
    user_id = uuid4()

    # Mock tenant check
    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant

    # Mock count query
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    # Mock documents query
    docs_result = MagicMock()
    docs_result.scalars.return_value.all.return_value = [mock_document]

    mock_session.execute.side_effect = [tenant_result, count_result, docs_result]

    result = await list_documents(
        session=mock_session,
        tenant_id=1,
        user_id=user_id,
        category=DocumentCategory.LEASE_AGREEMENTS,
        document_type="residential_tenancy_agreement",
        status_filter=DocumentStatus.PENDING,
        search="test",
        limit=20,
        offset=0
    )

    assert result.total == 1
    assert len(result.documents) == 1


@pytest.mark.asyncio
async def test_list_documents_pagination(mock_session):
    """Test pagination - covers lines 354-355."""
    user_id = uuid4()

    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant

    count_result = MagicMock()
    count_result.scalar_one.return_value = 0

    docs_result = MagicMock()
    docs_result.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [tenant_result, count_result, docs_result]

    result = await list_documents(
        session=mock_session,
        tenant_id=1,
        user_id=user_id,
        limit=10,
        offset=20
    )

    assert result.limit == 10
    assert result.offset == 20


# ============================================================================
# GET DOCUMENT TESTS (Covers lines 395-400)
# ============================================================================

@pytest.mark.asyncio
async def test_get_document_success(mock_session, mock_document):
    """Test get document - covers lines 395-400."""
    user_id = uuid4()

    # Mock tenant check
    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant

    # Mock document check
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_document

    mock_session.execute.side_effect = [tenant_result, doc_result]

    result = await get_document(
        session=mock_session,
        tenant_id=1,
        document_id=mock_document.id,
        user_id=user_id
    )

    assert result.id == mock_document.id


# ============================================================================
# UPDATE DOCUMENT TESTS (Covers lines 434-464)
# ============================================================================

@pytest.mark.asyncio
async def test_update_document_success(mock_session, mock_document):
    """Test document update - covers lines 440-455."""
    user_id = uuid4()

    # Mock tenant check
    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant

    # Mock document check
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_document

    mock_session.execute.side_effect = [tenant_result, doc_result]

    update_data = DocumentUpdateRequest(
        tags=["updated"],
        notes="Updated notes",
        status=DocumentStatus.VERIFIED
    )

    result = await update_document(
        session=mock_session,
        tenant_id=1,
        document_id=mock_document.id,
        user_id=user_id,
        update_data=update_data
    )

    assert result.id == mock_document.id
    mock_session.commit.assert_awaited_once()


# ============================================================================
# DELETE DOCUMENT TESTS (Covers lines 491-534 - NEW CODE)
# ============================================================================

@pytest.mark.asyncio
async def test_delete_document_success(mock_session, mock_document):
    """Test successful deletion - DB first, then blob - covers lines 507-526."""
    user_id = uuid4()

    # Mock tenant check
    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant

    # Mock document check
    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_document

    mock_session.execute.side_effect = [tenant_result, doc_result]

    with patch("Backend.api.tenants.documents.service.delete_blob_by_url", new=AsyncMock(return_value=True)):
        await delete_document(
            session=mock_session,
            tenant_id=1,
            document_id=mock_document.id,
            user_id=user_id
        )

    mock_session.delete.assert_called_once_with(mock_document)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_document_blob_fails(mock_session, mock_document):
    """Test deletion when blob fails but DB succeeds - covers lines 518-521."""
    user_id = uuid4()

    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_document

    mock_session.execute.side_effect = [tenant_result, doc_result]

    # Blob deletion fails
    with patch("Backend.api.tenants.documents.service.delete_blob_by_url", new=AsyncMock(return_value=False)):
        await delete_document(
            session=mock_session,
            tenant_id=1,
            document_id=mock_document.id,
            user_id=user_id
        )

    # DB should still be deleted
    mock_session.delete.assert_called_once()
    mock_session.commit.assert_awaited_once()


# ============================================================================
# SECURE URL TESTS (Covers lines 555-578)
# ============================================================================

@pytest.mark.asyncio
async def test_generate_secure_url_success(mock_session, mock_document):
    """Test secure URL generation - covers lines 560-570."""
    user_id = uuid4()

    mock_tenant = MagicMock()
    mock_tenant.landlord_id = user_id
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = mock_document

    mock_session.execute.side_effect = [tenant_result, doc_result]

    mock_url_data = {
        "secure_url": "https://blob.example.com/test.pdf?sas=token",
        "expires_at": datetime.now(timezone.utc),
        "expires_in_seconds": 3600
    }

    with patch("Backend.api.tenants.documents.service.generate_secure_document_url", new=AsyncMock(return_value=mock_url_data)):
        result = await generate_document_secure_url(
            session=mock_session,
            tenant_id=1,
            document_id=mock_document.id,
            user_id=user_id,
            expires_in_hours=1
        )

    assert "secure_url" in result
    assert result["expires_in_seconds"] == 3600
