"""
Unit tests for Azure Blob SAS token generation and upload functions.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
from uuid import uuid4
from io import BytesIO

from azure.core.exceptions import ResourceExistsError

from Backend.utils.azure_blob import (
    extract_blob_info_from_url,
    generate_sas_token_for_blob,
    generate_secure_document_url,
    _upload_to_blob,
)

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestExtractBlobInfoFromUrl:
    """Tests for extract_blob_info_from_url function."""
    
    def test_extract_valid_blob_url(self):
        """Test extracting container and blob name from valid URL."""
        # Arrange
        blob_url = "https://storage.blob.core.windows.net/lease-uploads/user_123/document.pdf"
        
        # Act
        container_name, blob_name = extract_blob_info_from_url(blob_url)
        
        # Assert
        assert container_name == "lease-uploads"
        assert blob_name == "user_123/document.pdf"
    
    def test_extract_url_with_nested_path(self):
        """Test extracting from URL with deeply nested blob path."""
        # Arrange
        blob_url = "https://storage.blob.core.windows.net/container/folder1/folder2/file.pdf"
        
        # Act
        container_name, blob_name = extract_blob_info_from_url(blob_url)
        
        # Assert
        assert container_name == "container"
        assert blob_name == "folder1/folder2/file.pdf"
    
    def test_extract_invalid_url_format(self):
        """Test error handling for invalid URL format."""
        # Arrange
        invalid_url = "https://storage.blob.core.windows.net/just-container"
        
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid blob URL format"):
            extract_blob_info_from_url(invalid_url)
    
    def test_extract_malformed_url(self):
        """Test error handling for malformed URL."""
        # Arrange
        malformed_url = "not-a-url"
        
        # Act & Assert
        with pytest.raises(ValueError):
            extract_blob_info_from_url(malformed_url)


class TestGenerateSasTokenForBlob:
    """Tests for generate_sas_token_for_blob function."""
    
    @patch('Backend.utils.azure_blob.settings')
    @patch('Backend.utils.azure_blob.generate_blob_sas')
    @patch('Backend.utils.azure_blob.utc_now')
    def test_generate_sas_token_success(self, mock_utc_now, mock_generate_sas, mock_settings):
        """Test successful SAS token generation."""
        # Arrange
        mock_settings.AZURE_STORAGE_ACCOUNT_NAME = "testaccount"
        mock_settings.AZURE_STORAGE_ACCOUNT_KEY = "testkey=="
        
        current_time = datetime(2024, 10, 9, 18, 0, 0)
        mock_utc_now.return_value = current_time
        
        mock_generate_sas.return_value = "sv=2021&se=2024-10-09T19:00:00Z&sp=r&sig=abc123"
        
        blob_url = "https://testaccount.blob.core.windows.net/lease-uploads/user_123/doc.pdf"
        
        # Act
        sas_token, expiry_time = generate_sas_token_for_blob(blob_url, expires_in_hours=1)
        
        # Assert
        assert sas_token == "sv=2021&se=2024-10-09T19:00:00Z&sp=r&sig=abc123"
        assert expiry_time == current_time + timedelta(hours=1)
        assert mock_generate_sas.called
    
    @patch('Backend.utils.azure_blob.settings')
    def test_generate_sas_token_missing_account_name(self, mock_settings):
        """Test error when Azure account name is not configured."""
        # Arrange
        mock_settings.AZURE_STORAGE_ACCOUNT_NAME = ""
        mock_settings.AZURE_STORAGE_ACCOUNT_KEY = "testkey=="
        
        # Act & Assert
        with pytest.raises(ValueError, match="AZURE_STORAGE_ACCOUNT_NAME not configured"):
            generate_sas_token_for_blob("https://test.com/container/blob")
    
    @patch('Backend.utils.azure_blob.settings')
    def test_generate_sas_token_missing_account_key(self, mock_settings):
        """Test error when Azure account key is not configured."""
        # Arrange
        mock_settings.AZURE_STORAGE_ACCOUNT_NAME = "testaccount"
        mock_settings.AZURE_STORAGE_ACCOUNT_KEY = ""
        
        # Act & Assert
        with pytest.raises(ValueError, match="AZURE_STORAGE_ACCOUNT_KEY not configured"):
            generate_sas_token_for_blob("https://test.com/container/blob")
    
    @patch('Backend.utils.azure_blob.settings')
    @patch('Backend.utils.azure_blob.generate_blob_sas')
    @patch('Backend.utils.azure_blob.utc_now')
    def test_generate_sas_token_with_ip_restriction(self, mock_utc_now, mock_generate_sas, mock_settings):
        """Test SAS token generation with IP restriction."""
        # Arrange
        mock_settings.AZURE_STORAGE_ACCOUNT_NAME = "testaccount"
        mock_settings.AZURE_STORAGE_ACCOUNT_KEY = "testkey=="
        
        current_time = datetime(2024, 10, 9, 18, 0, 0)
        mock_utc_now.return_value = current_time
        
        mock_generate_sas.return_value = "sv=2021&sp=r&sig=xyz"
        
        blob_url = "https://testaccount.blob.core.windows.net/lease-uploads/doc.pdf"
        client_ip = "192.168.1.1"
        
        # Act
        sas_token, expiry_time = generate_sas_token_for_blob(blob_url, allowed_ip=client_ip)
        
        # Assert
        assert sas_token is not None
        # Verify IP was passed to generate_blob_sas
        call_kwargs = mock_generate_sas.call_args[1]
        assert call_kwargs['ip'] == client_ip


class TestGenerateSecureDocumentUrl:
    """Tests for generate_secure_document_url function."""
    
    @patch('Backend.utils.azure_blob.blob_service_client')
    @patch('Backend.utils.azure_blob.settings')
    @patch('Backend.utils.azure_blob.generate_sas_token_for_blob')
    def test_generate_secure_url_success(self, mock_gen_sas, mock_settings, mock_blob_service):
        """Test successful secure URL generation with audit logging."""
        # Arrange
        mock_settings.DOCUMENT_SAS_EXPIRY_HOURS = 1
        mock_settings.DOCUMENT_ACCESS_LOGGING_ENABLED = True
        
        # Mock blob client to return exists() = True
        mock_blob_client = AsyncMock()
        mock_blob_client.exists = AsyncMock(return_value=True)
        mock_blob_service.get_blob_client.return_value = mock_blob_client
        
        expiry_time = datetime(2024, 10, 9, 19, 0, 0)
        mock_gen_sas.return_value = ("sv=2021&sig=abc", expiry_time)
        
        blob_url = "https://storage.blob.core.windows.net/lease-uploads/doc.pdf"
        user_id = uuid4()
        document_id = 123
        
        # Act
        import asyncio
        result = asyncio.run(generate_secure_document_url(
            blob_url=blob_url,
            user_id=user_id,
            document_id=document_id
        ))
        
        # Assert
        assert result["secure_url"] == f"{blob_url}?sv=2021&sig=abc"
        assert result["expires_at"] == "2024-10-09T19:00:00Z"
        assert result["expires_in_seconds"] == 3600
    
    @patch('Backend.utils.azure_blob.blob_service_client')
    @patch('Backend.utils.azure_blob.settings')
    @patch('Backend.utils.azure_blob.generate_sas_token_for_blob')
    def test_generate_secure_url_custom_expiry(self, mock_gen_sas, mock_settings, mock_blob_service):
        """Test secure URL generation with custom expiry time."""
        # Arrange
        mock_settings.DOCUMENT_SAS_EXPIRY_HOURS = 1
        mock_settings.DOCUMENT_ACCESS_LOGGING_ENABLED = False
        
        # Mock blob client to return exists() = True
        mock_blob_client = AsyncMock()
        mock_blob_client.exists = AsyncMock(return_value=True)
        mock_blob_service.get_blob_client.return_value = mock_blob_client
        
        expiry_time = datetime(2024, 10, 9, 22, 0, 0)  # 4 hours
        mock_gen_sas.return_value = ("sv=2021&sig=xyz", expiry_time)
        
        blob_url = "https://storage.blob.core.windows.net/container/blob"
        
        # Act
        import asyncio
        result = asyncio.run(generate_secure_document_url(
            blob_url=blob_url,
            user_id=uuid4(),
            document_id=456,
            expires_in_hours=4
        ))
        
        # Assert
        assert result["expires_in_seconds"] == 4 * 3600
        mock_gen_sas.assert_called_once()
        call_kwargs = mock_gen_sas.call_args[1]
        assert call_kwargs['expires_in_hours'] == 4


class TestUploadToBlobContainerCreation:
    """Tests for _upload_to_blob container auto-creation feature."""
    
    @patch('Backend.utils.azure_blob.blob_service_client')
    @patch('Backend.utils.azure_blob.settings')
    async def test_upload_creates_new_container(self, mock_settings, mock_blob_service):
        """Test that upload creates container if it doesn't exist."""
        # Arrange
        mock_settings.AZURE_BLOB_PUBLIC_URL = "https://storage.blob.core.windows.net"
        
        # Mock file
        mock_file = AsyncMock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.file = BytesIO(b"test content")
        mock_file.size = 100
        mock_file.seek = AsyncMock()
        mock_file.close = AsyncMock()
        
        # Mock container client - simulate container doesn't exist
        mock_container_client = MagicMock()
        mock_container_client.create_container = AsyncMock()  # First upload - creates container
        mock_container_client.get_blob_client = MagicMock()
        mock_blob_service.get_container_client.return_value = mock_container_client
        
        # Mock blob client
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = AsyncMock(return_value=None)
        mock_container_client.get_blob_client.return_value = mock_blob_client
        
        user_id = uuid4()
        
        # Act
        result = await _upload_to_blob(
            file=mock_file,
            user_id=user_id,
            container_name="tenant-documents",
            default_filename_prefix="tenant_document",
            safe_filename_suffix_limit=100
        )
        
        # Assert
        mock_container_client.create_container.assert_called_once()  # Container was created
        mock_blob_client.upload_blob.assert_called_once()  # File was uploaded
        assert "tenant-documents" in result
        assert result.startswith("https://storage.blob.core.windows.net")
    
    @patch('Backend.utils.azure_blob.blob_service_client')
    @patch('Backend.utils.azure_blob.settings')
    async def test_upload_handles_existing_container(self, mock_settings, mock_blob_service):
        """Test that upload handles ResourceExistsError gracefully when container already exists."""
        # Arrange
        mock_settings.AZURE_BLOB_PUBLIC_URL = "https://storage.blob.core.windows.net"
        
        # Mock file
        mock_file = AsyncMock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/pdf"
        mock_file.file = BytesIO(b"test content")
        mock_file.size = 100
        mock_file.seek = AsyncMock()
        mock_file.close = AsyncMock()
        
        # Mock container client - simulate container already exists
        mock_container_client = MagicMock()
        mock_container_client.create_container = AsyncMock(side_effect=ResourceExistsError("Container exists"))
        mock_container_client.get_blob_client = MagicMock()
        mock_blob_service.get_container_client.return_value = mock_container_client
        
        # Mock blob client
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = AsyncMock(return_value=None)
        mock_container_client.get_blob_client.return_value = mock_blob_client
        
        user_id = uuid4()
        
        # Act
        result = await _upload_to_blob(
            file=mock_file,
            user_id=user_id,
            container_name="tenant-documents",
            default_filename_prefix="tenant_document",
            safe_filename_suffix_limit=100
        )
        
        # Assert
        mock_container_client.create_container.assert_called_once()  # Attempted to create
        mock_blob_client.upload_blob.assert_called_once()  # Upload still succeeded
        assert "tenant-documents" in result
        # Verify upload continued despite ResourceExistsError

