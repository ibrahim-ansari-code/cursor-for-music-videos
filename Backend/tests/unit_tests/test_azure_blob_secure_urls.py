"""
Unit tests for Azure Blob Storage secure URL generation utilities.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from Backend.utils.azure_blob import generate_secure_document_url, extract_blob_info_from_url
from Backend.utils.datetime_utils import utc_now

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_generate_secure_document_url_success(mocker):
    """Test successful secure URL generation with blob existence check."""
    # Arrange
    blob_url = "https://briklicorestorage.blob.core.windows.net/test-container/user_123/file.pdf"
    user_id = uuid4()
    document_id = 42
    
    # Mock blob existence check
    mock_blob_client = MagicMock()
    mock_blob_client.exists = AsyncMock(return_value=True)
    
    mock_blob_service_client = MagicMock()
    mock_blob_service_client.get_blob_client = MagicMock(return_value=mock_blob_client)
    
    mocker.patch("Backend.utils.azure_blob.blob_service_client", mock_blob_service_client)
    
    # Mock SAS token generation
    mock_sas_token = "sv=2021&sig=test123"
    mock_expiry = utc_now() + timedelta(hours=1)
    mocker.patch(
        "Backend.utils.azure_blob.generate_sas_token_for_blob",
        return_value=(mock_sas_token, mock_expiry)
    )
    
    # Act
    result = await generate_secure_document_url(
        blob_url=blob_url,
        user_id=user_id,
        document_id=document_id,
        expires_in_hours=1
    )
    
    # Assert
    assert "secure_url" in result
    assert mock_sas_token in result["secure_url"]
    assert result["expires_in_seconds"] == 3600
    mock_blob_client.exists.assert_called_once()


@pytest.mark.asyncio
async def test_generate_secure_document_url_blob_not_found(mocker):
    """Test secure URL generation when blob doesn't exist."""
    # Arrange
    blob_url = "https://briklicorestorage.blob.core.windows.net/test-container/deleted.pdf"
    user_id = uuid4()
    
    # Mock blob existence check to return False
    mock_blob_client = MagicMock()
    mock_blob_client.exists = AsyncMock(return_value=False)
    
    mock_blob_service_client = MagicMock()
    mock_blob_service_client.get_blob_client = MagicMock(return_value=mock_blob_client)
    
    mocker.patch("Backend.utils.azure_blob.blob_service_client", mock_blob_service_client)
    
    # Act & Assert
    with pytest.raises(ValueError, match="not found in storage"):
        await generate_secure_document_url(
            blob_url=blob_url,
            user_id=user_id,
            document_id="test"
        )


@pytest.mark.asyncio  
async def test_generate_secure_document_url_no_blob_client(mocker):
    """Test secure URL generation when blob service client is None (continues anyway)."""
    blob_url = "https://briklicorestorage.blob.core.windows.net/test-container/file.pdf"
    user_id = uuid4()
    
    # Mock blob_service_client as None (simulates disabled Azure)
    mocker.patch("Backend.utils.azure_blob.blob_service_client", None)
    
    # Mock SAS token generation
    mock_sas_token = "sv=2021&sig=test123"
    mock_expiry = utc_now() + timedelta(hours=1)
    mocker.patch(
        "Backend.utils.azure_blob.generate_sas_token_for_blob",
        return_value=(mock_sas_token, mock_expiry)
    )
    
    # Act - should continue without existence check
    result = await generate_secure_document_url(
        blob_url=blob_url,
        user_id=user_id,
        document_id="test"
    )
    
    # Assert - should succeed despite no blob client
    assert "secure_url" in result


@pytest.mark.asyncio
async def test_generate_secure_document_url_with_existing_query_params(mocker):
    """Test secure URL generation when blob URL already has query parameters."""
    blob_url = "https://briklicorestorage.blob.core.windows.net/test-container/file.pdf?existing=param"
    user_id = uuid4()
    
    mocker.patch("Backend.utils.azure_blob.blob_service_client", None)
    
    mock_sas_token = "sv=2021&sig=test123"
    mock_expiry = utc_now() + timedelta(hours=1)
    mocker.patch(
        "Backend.utils.azure_blob.generate_sas_token_for_blob",
        return_value=(mock_sas_token, mock_expiry)
    )
    
    # Act
    result = await generate_secure_document_url(
        blob_url=blob_url,
        user_id=user_id,
        document_id="test"
    )
    
    # Assert - should use & instead of ? for separator
    assert "?existing=param&sv=" in result["secure_url"]
    assert result["secure_url"].count('?') == 1  # Only one question mark


def test_extract_blob_info_from_url():
    """Test extraction of container and blob name from Azure URL."""
    url = "https://briklicorestorage.blob.core.windows.net/test-container/user_123/file.pdf"
    
    container, blob = extract_blob_info_from_url(url)
    
    assert container == "test-container"
    assert blob == "user_123/file.pdf"


def test_extract_blob_info_from_url_invalid():
    """Test extraction with invalid URL raises ValueError."""
    url = "https://example.com/not-azure.pdf"
    
    with pytest.raises(ValueError, match="Could not parse blob URL"):
        extract_blob_info_from_url(url)

