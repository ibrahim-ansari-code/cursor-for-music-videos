"""
Unit tests for Azure Storage configuration parsing.
"""

import pytest
from unittest.mock import patch
import os

from Backend.config import Settings

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestAzureStorageConfig:
    """Tests for Azure Storage account name and key extraction from connection string."""
    
    def test_extract_account_name_from_connection_string(self):
        """Test parsing account name from valid connection string."""
        # Arrange
        connection_string = (
            "DefaultEndpointsProtocol=https;"
            "AccountName=briklicorestorage;"
            "AccountKey=abc123==;"
            "EndpointSuffix=core.windows.net"
        )
        
        with patch.dict(os.environ, {
            'AZURE_STORAGE_CONNECTION_STRING': connection_string,
            'DATABASE_URL': 'postgresql://test'
        }):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.AZURE_STORAGE_ACCOUNT_NAME == "briklicorestorage"
    
    def test_extract_account_key_from_connection_string(self):
        """Test parsing account key from valid connection string."""
        # Arrange
        connection_string = (
            "DefaultEndpointsProtocol=https;"
            "AccountName=testaccount;"
            "AccountKey=secretkey123==;"
            "EndpointSuffix=core.windows.net"
        )
        
        with patch.dict(os.environ, {
            'AZURE_STORAGE_CONNECTION_STRING': connection_string,
            'DATABASE_URL': 'postgresql://test'
        }):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.AZURE_STORAGE_ACCOUNT_KEY == "secretkey123=="
    
    def test_empty_connection_string_returns_empty_strings(self):
        """Test handling of empty connection string."""
        # Arrange
        with patch.dict(os.environ, {
            'AZURE_STORAGE_CONNECTION_STRING': '',
            'DATABASE_URL': 'postgresql://test'
        }):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.AZURE_STORAGE_ACCOUNT_NAME == ""
            assert settings.AZURE_STORAGE_ACCOUNT_KEY == ""
    
    def test_malformed_connection_string_returns_empty_strings(self):
        """Test handling of malformed connection string."""
        # Arrange
        malformed_string = "SomeRandomString=Value;NoAccountInfo=True"
        
        with patch.dict(os.environ, {
            'AZURE_STORAGE_CONNECTION_STRING': malformed_string,
            'DATABASE_URL': 'postgresql://test'
        }):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.AZURE_STORAGE_ACCOUNT_NAME == ""
            assert settings.AZURE_STORAGE_ACCOUNT_KEY == ""
    
    def test_connection_string_with_different_order(self):
        """Test parsing connection string with parameters in different order."""
        # Arrange
        connection_string = (
            "AccountKey=key456==;"
            "EndpointSuffix=core.windows.net;"
            "AccountName=myaccount;"
            "DefaultEndpointsProtocol=https"
        )
        
        with patch.dict(os.environ, {
            'AZURE_STORAGE_CONNECTION_STRING': connection_string,
            'DATABASE_URL': 'postgresql://test'
        }):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.AZURE_STORAGE_ACCOUNT_NAME == "myaccount"
            assert settings.AZURE_STORAGE_ACCOUNT_KEY == "key456=="
    
    def test_document_sas_expiry_default(self):
        """Test default SAS expiry hours configuration."""
        # Arrange
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}, clear=True):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.DOCUMENT_SAS_EXPIRY_HOURS == 1
    
    def test_document_sas_expiry_custom(self):
        """Test custom SAS expiry hours configuration."""
        # Arrange
        with patch.dict(os.environ, {
            'DOCUMENT_SAS_EXPIRY_HOURS': '2',
            'DATABASE_URL': 'postgresql://test'
        }):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.DOCUMENT_SAS_EXPIRY_HOURS == 2
    
    def test_document_access_logging_enabled_by_default(self):
        """Test that document access logging is enabled by default."""
        # Arrange
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://test'}, clear=True):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.DOCUMENT_ACCESS_LOGGING_ENABLED is True
    
    def test_document_access_logging_can_be_disabled(self):
        """Test disabling document access logging."""
        # Arrange
        with patch.dict(os.environ, {
            'DOCUMENT_ACCESS_LOGGING_ENABLED': 'false',
            'DATABASE_URL': 'postgresql://test'
        }):
            # Act
            settings = Settings()
            
            # Assert
            assert settings.DOCUMENT_ACCESS_LOGGING_ENABLED is False

