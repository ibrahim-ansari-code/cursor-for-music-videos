"""
API tests for Tenant Documents endpoints - Strategic Coverage
Focuses on error paths and edge cases to maximize router coverage.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from io import BytesIO

from fastapi import HTTPException, status

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType, DocumentCategory, DocumentStatus
from Backend.api.auth import get_current_user
from Backend.database import get_session

pytestmark = pytest.mark.unit


# ============================================================================
# FIXTURES & HELPERS
# ============================================================================

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    # Patch startup event to prevent database connection
    with patch('Backend.api.app.startup_event', new=AsyncMock()):
        yield
    app.dependency_overrides.clear()


class TestClientWithHost(TestClient):
    def __init__(self, *args, **kwargs):
        # Don't raise server exceptions (like database startup failures)
        kwargs.setdefault('raise_server_exceptions', False)
        super().__init__(*args, **kwargs)
    
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, user_type=UserType.LANDLORD, is_admin=False):
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=is_admin,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )


def create_test_pdf_file(filename="test.pdf", size_bytes=1024):
    """Create a test PDF file for multipart uploads."""
    pdf_header = b'%PDF-1.4\n'
    pdf_data = pdf_header + b'test content' * (size_bytes // 12)
    return {
        "file": (filename, BytesIO(pdf_data), "application/pdf")
    }


# ============================================================================
# GET /tenants/{id}/documents - LIST TESTS
# ============================================================================

def test_list_documents_success():
    """Test listing documents - covers router.py lines 86+."""
    mock_user = create_test_user()

    mock_response = {
        "documents": [],
        "total": 0,
        "limit": 20,
        "offset": 0
    }

    # Set up dependency overrides
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    # Mock the service layer
    with patch("Backend.api.tenants.documents.service.list_documents", new=AsyncMock(return_value=mock_response)):
        client = TestClientWithHost(app)
        response = client.get("/api/tenants/1/documents")

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    assert "documents" in response.json()


def test_list_documents_with_filters():
    """Test listing with query parameters - covers router lines with filters."""
    mock_user = create_test_user()

    mock_response = {"documents": [], "total": 0, "limit": 20, "offset": 0}

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.list_documents", new=AsyncMock(return_value=mock_response)):
        client = TestClientWithHost(app)
        response = client.get(
            "/api/tenants/1/documents",
            params={
                "category": "lease_agreements",
                "status": "pending",
                "search": "test",
                "limit": 10,
                "offset": 5
            }
        )

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"


def test_list_documents_forbidden():
    """Test forbidden access - covers router error path."""
    mock_user = create_test_user()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.list_documents", new=AsyncMock(side_effect=HTTPException(status_code=403, detail="Forbidden"))):
        client = TestClientWithHost(app)
        response = client.get("/api/tenants/999/documents")

    assert response.status_code == 403


# ============================================================================
# POST /tenants/{id}/documents - UPLOAD TESTS (Covers lines 137-152)
# ============================================================================

def test_upload_document_success():
    """Test successful document upload - covers router lines 137+."""
    from Backend.api.tenants.documents.schemas import DocumentResponse
    from datetime import datetime
    
    mock_user = create_test_user()

    # Create proper DocumentResponse object
    mock_doc_response = DocumentResponse(
        id=uuid4(),
        tenant_id=1,
        file_name="test.pdf",
        file_path="https://blob.example.com/test.pdf",
        file_size=1024,
        file_type="application/pdf",
        document_category=DocumentCategory.LEASE_AGREEMENTS,
        document_type="residential_tenancy_agreement",
        tags=[],
        notes=None,
        expiry_date=None,
        status=DocumentStatus.PENDING,
        uploaded_by=mock_user.id,
        uploaded_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_expired=False,
        days_until_expiry=None
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.create_document", new=AsyncMock(return_value=mock_doc_response)):
        client = TestClientWithHost(app)
        files = create_test_pdf_file()
        data = {
            "document_category": "lease_agreements",
            "document_type": "residential_tenancy_agreement"
        }
        response = client.post(
            "/api/tenants/1/documents",
            files=files,
            data=data
        )

    assert response.status_code == 201, f"Expected 201 but got {response.status_code}: {response.json()}"


def test_upload_document_with_metadata():
    """Test upload with tags, notes, expiry - covers router lines 140-147."""
    from Backend.api.tenants.documents.schemas import DocumentResponse
    from datetime import datetime, date
    
    mock_user = create_test_user()

    # Create proper DocumentResponse object
    mock_doc_response = DocumentResponse(
        id=uuid4(),
        tenant_id=1,
        file_name="test.pdf",
        file_path="https://blob.example.com/test.pdf",
        file_size=1024,
        file_type="application/pdf",
        document_category=DocumentCategory.INSURANCE_RISK,
        document_type="tenant_insurance_certificate",
        tags=["important", "insurance"],
        notes="Annual insurance renewal",
        expiry_date=date(2025, 12, 31),
        status=DocumentStatus.PENDING,
        uploaded_by=mock_user.id,
        uploaded_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_expired=False,
        days_until_expiry=70
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.create_document", new=AsyncMock(return_value=mock_doc_response)):
        client = TestClientWithHost(app)
        files = create_test_pdf_file()
        data = {
            "document_category": "insurance_risk",
            "document_type": "tenant_insurance_certificate",
            "tags": "important,insurance",
            "notes": "Annual insurance renewal",
            "expiry_date": "2025-12-31"
        }
        response = client.post(
            "/api/tenants/1/documents",
            files=files,
            data=data
        )

    assert response.status_code == 201, f"Expected 201 but got {response.status_code}: {response.text}"


def test_upload_document_validation_error():
    """Test upload validation error - covers router line 152."""
    mock_user = create_test_user()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.create_document", new=AsyncMock(side_effect=HTTPException(status_code=400, detail="Invalid document type"))):
        client = TestClientWithHost(app)
        files = create_test_pdf_file()
        data = {
            "document_category": "lease_agreements",
            "document_type": "invalid_type"
        }
        response = client.post(
            "/api/tenants/1/documents",
            files=files,
            data=data
        )

    assert response.status_code == 400


# ============================================================================
# GET /tenants/{id}/documents/{doc_id} - GET DOCUMENT TESTS
# ============================================================================

def test_get_document_success():
    """Test get document by ID - covers router line 188+."""
    from Backend.api.tenants.documents.schemas import DocumentResponse
    from datetime import datetime
    
    mock_user = create_test_user()
    doc_id = uuid4()

    mock_doc = DocumentResponse(
        id=doc_id,
        tenant_id=1,
        file_name="test.pdf",
        file_path="https://blob.example.com/test.pdf",
        file_size=1024,
        file_type="application/pdf",
        document_category=DocumentCategory.LEASE_AGREEMENTS,
        document_type="residential_tenancy_agreement",
        tags=[],
        notes=None,
        expiry_date=None,
        status=DocumentStatus.PENDING,
        uploaded_by=mock_user.id,
        uploaded_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_expired=False,
        days_until_expiry=None
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.get_document", new=AsyncMock(return_value=mock_doc)):
        client = TestClientWithHost(app)
        response = client.get(f"/api/tenants/1/documents/{doc_id}")

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"


def test_get_document_not_found():
    """Test document not found error."""
    mock_user = create_test_user()
    doc_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.get_document", new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Not found"))):
        client = TestClientWithHost(app)
        response = client.get(f"/api/tenants/1/documents/{doc_id}")

    assert response.status_code == 404


# ============================================================================
# GET /tenants/{id}/documents/{doc_id}/secure-url - SECURE URL TESTS (Lines 225-227)
# ============================================================================

def test_get_secure_url_success():
    """Test secure URL generation - covers router lines 225-227."""
    mock_user = create_test_user()
    doc_id = uuid4()

    mock_url_data = {
        "secure_url": "https://blob.example.com/test.pdf?sas=token",
        "expires_at": datetime.now(timezone.utc).isoformat(),
        "expires_in_seconds": 3600
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.generate_document_secure_url", new=AsyncMock(return_value=mock_url_data)):
        client = TestClientWithHost(app)
        response = client.get(f"/api/tenants/1/documents/{doc_id}/secure-url")

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    assert "secure_url" in response.json()


def test_get_secure_url_with_custom_expiry():
    """Test secure URL generation - covers router endpoint."""
    from datetime import datetime
    
    mock_user = create_test_user()
    doc_id = uuid4()

    mock_url_data = {
        "secure_url": "https://example.com/doc.pdf?sas=token",
        "expires_at": datetime.now().isoformat() + "Z",
        "expires_in_seconds": 3600
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.generate_document_secure_url", new=AsyncMock(return_value=mock_url_data)):
        client = TestClientWithHost(app)
        response = client.get(f"/api/tenants/1/documents/{doc_id}/secure-url")

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"


# ============================================================================
# PATCH /tenants/{id}/documents/{doc_id} - UPDATE TESTS (Lines 264, 297)
# ============================================================================

def test_update_document_success():
    """Test document metadata update - covers router line 264+."""
    from Backend.api.tenants.documents.schemas import DocumentResponse
    from datetime import datetime
    
    mock_user = create_test_user()
    doc_id = uuid4()

    mock_updated_doc = DocumentResponse(
        id=doc_id,
        tenant_id=1,
        file_name="test.pdf",
        file_path="https://blob.example.com/test.pdf",
        file_size=1024,
        file_type="application/pdf",
        document_category=DocumentCategory.LEASE_AGREEMENTS,
        document_type="residential_tenancy_agreement",
        tags=[],
        notes="Updated",
        expiry_date=None,
        status=DocumentStatus.VERIFIED,
        uploaded_by=mock_user.id,
        uploaded_at=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_expired=False,
        days_until_expiry=None
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.update_document", new=AsyncMock(return_value=mock_updated_doc)):
        client = TestClientWithHost(app)
        response = client.patch(
            f"/api/tenants/1/documents/{doc_id}",
            json={"status": "verified", "notes": "Updated"}
        )

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"


def test_update_document_error():
    """Test update error handling - covers router line 297."""
    mock_user = create_test_user()
    doc_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.update_document", new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Not found"))):
        client = TestClientWithHost(app)
        response = client.patch(
            f"/api/tenants/1/documents/{doc_id}",
            json={"status": "verified"}
        )

    assert response.status_code == 404


# ============================================================================
# DELETE /tenants/{id}/documents/{doc_id} - DELETE TESTS (Lines 304, 342, 344)
# ============================================================================

def test_delete_document_success():
    """Test successful document deletion - covers router lines 304+."""
    mock_user = create_test_user()
    doc_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.delete_document", new=AsyncMock(return_value=None)):
        client = TestClientWithHost(app)
        response = client.delete(f"/api/tenants/1/documents/{doc_id}")

    assert response.status_code == 204


def test_delete_document_not_found():
    """Test delete not found error - covers router line 342."""
    mock_user = create_test_user()
    doc_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.delete_document", new=AsyncMock(side_effect=HTTPException(status_code=404, detail="Not found"))):
        client = TestClientWithHost(app)
        response = client.delete(f"/api/tenants/1/documents/{doc_id}")

    assert response.status_code == 404


def test_delete_document_server_error():
    """Test delete server error - covers router line 344."""
    mock_user = create_test_user()
    doc_id = uuid4()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with patch("Backend.api.tenants.documents.service.delete_document", new=AsyncMock(side_effect=Exception("Azure error"))):
        client = TestClientWithHost(app)
        response = client.delete(f"/api/tenants/1/documents/{doc_id}")

    assert response.status_code == 500


# ============================================================================
# GET /document-types/taxonomy - TAXONOMY TESTS (Line 355)
# ============================================================================

def test_get_taxonomy_success():
    """Test taxonomy endpoint - covers router line 355."""
    mock_taxonomy = {
        "categories": [
            {
                "key": "lease_agreements",
                "label": "Lease & Core Agreements",
                "icon": "DocumentText",
                "requires_expiry": False,
                "types": ["residential_tenancy_agreement"]
            }
        ]
    }

    with patch("Backend.api.tenants.documents.router.get_all_categories", return_value=mock_taxonomy["categories"]):
        client = TestClientWithHost(app)
        response = client.get("/api/document-types/taxonomy")

    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    assert "categories" in response.json()
