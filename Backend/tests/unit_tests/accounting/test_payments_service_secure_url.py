"""
Unit tests for payment service secure URL generation.
"""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import HTTPException

from Backend.api.accounting.payments.service import generate_receipt_secure_url
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
async def test_generate_receipt_secure_url_success(mocker):
    """Test successful payment receipt secure URL generation."""
    user = create_test_user()
    receipt_url = "https://briklicorestorage.blob.core.windows.net/payment-receipts/receipt.pdf"
    
    mock_result = {
        "secure_url": f"{receipt_url}?sv=2021&sig=test",
        "expires_at": "2024-10-09T20:30:00Z",
        "expires_in_seconds": 3600
    }
    mocker.patch(
        "Backend.api.accounting.payments.service.generate_secure_document_url",
        new=AsyncMock(return_value=mock_result)
    )
    
    result = await generate_receipt_secure_url(receipt_url, user)
    
    assert "secure_url" in result


@pytest.mark.asyncio
async def test_generate_receipt_secure_url_unauthorized():
    """Test payment receipt secure URL generation with unauthorized user."""
    user = create_test_user(user_type=UserType.TENANT)
    receipt_url = "https://briklicorestorage.blob.core.windows.net/payment-receipts/receipt.pdf"
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_receipt_secure_url(receipt_url, user)
    
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_generate_receipt_secure_url_error(mocker):
    """Test payment receipt secure URL generation with error."""
    user = create_test_user()
    receipt_url = "https://briklicorestorage.blob.core.windows.net/payment-receipts/receipt.pdf"
    
    mocker.patch(
        "Backend.api.accounting.payments.service.generate_secure_document_url",
        new=AsyncMock(side_effect=Exception("Azure error"))
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await generate_receipt_secure_url(receipt_url, user)
    
    assert exc_info.value.status_code == 500

