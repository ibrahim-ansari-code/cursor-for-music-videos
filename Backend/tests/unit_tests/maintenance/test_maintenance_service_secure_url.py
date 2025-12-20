"""
Unit tests for MaintenanceService secure URL generation.
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException

from Backend.api.maintenance.service import MaintenanceService
from Backend.models.user import User
from Backend.models.enums import UserType

pytestmark = pytest.mark.unit


def create_test_user(user_type=UserType.LANDLORD):
    """Helper to create test user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        is_email_verified=True
    )


@pytest.mark.asyncio
async def test_generate_photo_secure_url_success(mocker):
    """Test successful photo secure URL generation."""
    user = create_test_user()
    photo_url = "https://briklicorestorage.blob.core.windows.net/maintenance-photos/photo.jpg"
    
    mock_result = {
        "secure_url": f"{photo_url}?sv=2021&sig=test",
        "expires_at": "2024-10-09T20:30:00Z",
        "expires_in_seconds": 3600
    }
    mocker.patch(
        "Backend.api.maintenance.service.generate_secure_document_url",
        new=AsyncMock(return_value=mock_result)
    )
    
    result = await MaintenanceService.generate_photo_secure_url(photo_url, user)
    
    assert "secure_url" in result
    assert "?sv=" in result["secure_url"]


@pytest.mark.asyncio
async def test_generate_photo_secure_url_unauthorized():
    """Test photo secure URL generation with unauthorized user."""
    # Use a user type that's NOT authorized (only LANDLORD, ADMIN, TENANT are authorized)
    # Create a user with a different user type by directly setting it
    user = create_test_user()
    user.user_type = "VENDOR"  # Not an authorized type
    photo_url = "https://briklicorestorage.blob.core.windows.net/maintenance-photos/photo.jpg"

    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.generate_photo_secure_url(photo_url, user)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_generate_photo_secure_url_generation_error(mocker):
    """Test photo secure URL generation when SAS generation fails."""
    user = create_test_user()
    photo_url = "https://briklicorestorage.blob.core.windows.net/maintenance-photos/photo.jpg"
    
    mocker.patch(
        "Backend.api.maintenance.service.generate_secure_document_url",
        new=AsyncMock(side_effect=Exception("Azure error"))
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.generate_photo_secure_url(photo_url, user)
    
    assert exc_info.value.status_code == 500

