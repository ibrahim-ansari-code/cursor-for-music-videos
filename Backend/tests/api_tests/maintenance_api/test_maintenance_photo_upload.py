"""
Unit tests for photo upload operations in the maintenance API endpoint using hybrid API testing pattern.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from uuid import uuid4
from datetime import datetime, timezone
from io import BytesIO

from fastapi import HTTPException, UploadFile, status

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.auth import get_current_user
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()

# Create a custom TestClient that sets the proper host header
class TestClientWithHost(TestClient):
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD, is_admin=False):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=is_admin,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )

def create_test_image_file(filename="test.jpg", content_type="image/jpeg"):
    """Create a test image file with proper JPEG headers."""
    # JPEG magic bytes
    jpeg_header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    # Add some dummy data to make it look like a real image
    jpeg_data = jpeg_header + b'\x00' * 1000 + b'\xFF\xD9'  # End with JPEG footer
    
    return {
        "upload_file": (filename, BytesIO(jpeg_data), content_type)
    }

def create_test_png_file(filename="test.png"):
    """Create a test PNG file with proper PNG headers."""
    # PNG magic bytes
    png_header = b'\x89PNG\r\n\x1a\n'
    # Add IHDR chunk (required for valid PNG)
    png_data = png_header + b'\x00\x00\x00\rIHDR' + b'\x00' * 1000
    
    return {
        "upload_file": (filename, BytesIO(png_data), "image/png")
    }

def create_test_pdf_file(filename="test.pdf"):
    """Create a test PDF file with proper PDF headers."""
    # PDF magic bytes
    pdf_header = b'%PDF-1.4\n'
    pdf_data = pdf_header + b'1 0 obj\n<< /Type /Catalog >>\nendobj\n'
    
    return {
        "upload_file": (filename, BytesIO(pdf_data), "application/pdf")
    }

def create_invalid_file(filename="test.txt"):
    """Create an invalid file type for testing."""
    return {
        "upload_file": (filename, BytesIO(b"This is a text file"), "text/plain")
    }

def create_large_file(filename="large.jpg", size_mb=15):
    """Create a file that exceeds size limit."""
    # JPEG header
    jpeg_header = b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
    # Create large content
    large_content = jpeg_header + b'\x00' * (size_mb * 1024 * 1024) + b'\xFF\xD9'
    
    return {
        "upload_file": (filename, BytesIO(large_content), "image/jpeg")
    }

# =============================================================================
# PHOTO UPLOAD TESTS
# =============================================================================

def test_upload_maintenance_photo_success_jpeg():
    """Test successful upload of JPEG maintenance photo."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    fake_response = {"photo_url": "https://storage.example.com/maintenance/photo123.jpg"}
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_test_image_file()
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert "photo_url" in data
            assert data["photo_url"] == "https://storage.example.com/maintenance/photo123.jpg"


def test_upload_maintenance_photo_success_png():
    """Test successful upload of PNG maintenance photo."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    fake_response = {"photo_url": "https://storage.example.com/maintenance/photo456.png"}
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_test_png_file()
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert "photo_url" in data
            assert ".png" in data["photo_url"]


def test_upload_maintenance_photo_success_pdf():
    """Test successful upload of PDF maintenance document."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    fake_response = {"photo_url": "https://storage.example.com/maintenance/document789.pdf"}
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_test_pdf_file()
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert "photo_url" in data
            assert ".pdf" in data["photo_url"]


def test_upload_maintenance_photo_admin_success():
    """Test that admin can upload maintenance photos."""
    # Arrange
    admin_id = uuid4()
    admin_user = create_test_user(
        user_id=admin_id,
        email="admin@example.com",
        user_type=UserType.ADMIN,
        is_admin=True
    )
    
    fake_response = {"photo_url": "https://storage.example.com/maintenance/admin-photo.jpg"}
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_test_image_file()
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert "photo_url" in data


def test_upload_maintenance_photo_forbidden_tenant():
    """Test that tenants cannot upload maintenance photos."""
    # Arrange
    tenant_id = uuid4()
    tenant_user = create_test_user(
        user_id=tenant_id,
        email="tenant@example.com",
        user_type=UserType.TENANT,
        is_admin=False
    )
    
    # Mock the service layer to raise 403
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo",
        new=AsyncMock(side_effect=HTTPException(
            status_code=403,
            detail="Not authorized to upload maintenance photos."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: tenant_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_test_image_file()
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 403
            assert "Not authorized" in response.json()["detail"]


def test_upload_maintenance_photo_invalid_file_type():
    """Test error when uploading unsupported file type."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    # Mock the service layer to raise 400 for invalid file type
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo",
        new=AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF, JPG, and PNG files are allowed."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_invalid_file()
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 400
            assert "Unsupported file type" in response.json()["detail"]


def test_upload_maintenance_photo_file_too_large():
    """Test error when file exceeds size limit (10MB)."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    # Mock the service layer to raise 413 for file too large
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo",
        new=AsyncMock(side_effect=HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 10 MB."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_large_file(size_mb=15)
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 413
            assert "File too large" in response.json()["detail"]


def test_upload_maintenance_photo_no_file():
    """Test error when no file is provided."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    # Override dependencies
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Act - Send request without file
        response = client.post("/api/maintenance/upload-photo")
        
        # Assert
        assert response.status_code == 422  # Validation error for missing file


def test_upload_maintenance_photo_azure_error():
    """Test error handling when Azure Blob Storage fails."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    # Mock the service layer to raise storage error
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo",
        new=AsyncMock(side_effect=HTTPException(
            status_code=500,
            detail="Failed to upload maintenance photo: Azure storage error"
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act
            files = create_test_image_file()
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 500
            assert "Failed to upload" in response.json()["detail"]


def test_upload_maintenance_photo_with_special_filename():
    """Test upload with special characters in filename."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    # Filename with special characters should be handled properly
    fake_response = {"photo_url": "https://storage.example.com/maintenance/photo_with_special_chars.jpg"}
    
    # Mock the service layer
    with patch("Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo", new=AsyncMock(return_value=fake_response)):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - Create file with special characters in name
            files = create_test_image_file(filename="test image (1) & #2.jpg")
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 201
            data = response.json()
            assert "photo_url" in data


def test_upload_maintenance_photo_malformed_image():
    """Test handling of malformed image that has wrong magic bytes."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    # Mock the service to detect invalid file content
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo",
        new=AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF, JPG, and PNG files are allowed."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - File claims to be JPEG but has wrong content
            files = {
                "upload_file": ("fake.jpg", BytesIO(b"Not a real JPEG"), "image/jpeg")
            }
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 400
            assert "Unsupported file type" in response.json()["detail"]


def test_upload_maintenance_photo_empty_file():
    """Test error when uploading empty file."""
    # Arrange
    user_id = uuid4()
    fake_user = create_test_user(user_id=user_id, user_type=UserType.LANDLORD)
    
    # Mock the service to handle empty file
    with patch(
        "Backend.api.maintenance.router.MaintenanceService.upload_maintenance_photo",
        new=AsyncMock(side_effect=HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF, JPG, and PNG files are allowed."
        ))
    ):
        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: fake_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()
        
        with TestClientWithHost(app) as client:
            # Act - Empty file
            files = {
                "upload_file": ("empty.jpg", BytesIO(b""), "image/jpeg")
            }
            response = client.post("/api/maintenance/upload-photo", files=files)
            
            # Assert
            assert response.status_code == 400