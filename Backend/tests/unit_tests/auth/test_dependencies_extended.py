"""
Extended unit tests for auth dependencies to improve coverage.
"""
import pytest
from datetime import datetime, UTC
from uuid import uuid4
from fastapi import HTTPException

from Backend.api.auth.dependencies import (
    get_current_admin_user,
    get_current_verified_user,
    parse_user_name
)
from Backend.models.user import User
from Backend.models.enums import UserType


@pytest.fixture
def mock_user():
    """Create a mock user."""
    return User(
        id=uuid4(),
        email="test@example.com",
        user_type=UserType.LANDLORD,
        is_active=True,
        is_email_verified=True,
        is_admin=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC)
    )


class TestExtendedAuthDependencies:
    """Extended test cases for auth dependencies."""

    async def test_get_current_admin_user_success(self, mock_user):
        """Test get_current_admin_user with admin user."""
        # Arrange
        mock_user.is_admin = True
        
        # Act
        user = await get_current_admin_user(mock_user)
        
        # Assert
        assert user == mock_user

    async def test_get_current_admin_user_not_admin(self, mock_user):
        """Test get_current_admin_user with non-admin user."""
        # Arrange
        mock_user.is_admin = False
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Not enough permissions" in str(exc_info.value.detail)

    async def test_get_current_verified_user_success(self, mock_user):
        """Test get_current_verified_user with verified user."""
        # Arrange
        mock_user.is_email_verified = True
        
        # Act
        user = await get_current_verified_user(mock_user)
        
        # Assert
        assert user == mock_user

    async def test_get_current_verified_user_unverified(self, mock_user):
        """Test get_current_verified_user with unverified user."""
        # Arrange
        mock_user.is_email_verified = False
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_verified_user(mock_user)
        
        assert exc_info.value.status_code == 403
        assert "Email verification required" in str(exc_info.value.detail)

    def test_parse_user_name_full_name(self):
        """Test parse_user_name with full name."""
        # Arrange
        user_metadata = {"full_name": "John Doe"}
        
        # Act
        first_name, last_name = parse_user_name(user_metadata)
        
        # Assert
        assert first_name == "John"
        assert last_name == "Doe"

    def test_parse_user_name_single_name(self):
        """Test parse_user_name with single name."""
        # Arrange
        user_metadata = {"full_name": "John"}
        
        # Act
        first_name, last_name = parse_user_name(user_metadata)
        
        # Assert
        assert first_name == "John"
        assert last_name == ""

    def test_parse_user_name_multiple_parts(self):
        """Test parse_user_name with multiple name parts."""
        # Arrange
        user_metadata = {"full_name": "John David Doe"}
        
        # Act
        first_name, last_name = parse_user_name(user_metadata)
        
        # Assert
        assert first_name == "John"
        assert last_name == "David Doe"

    def test_parse_user_name_empty(self):
        """Test parse_user_name with empty metadata."""
        # Arrange
        user_metadata = {}
        
        # Act
        first_name, last_name = parse_user_name(user_metadata)
        
        # Assert
        assert first_name is None
        assert last_name is None

    def test_parse_user_name_none_value(self):
        """Test parse_user_name with None full_name."""
        # Arrange
        user_metadata = {"full_name": None}
        
        # Act
        first_name, last_name = parse_user_name(user_metadata)
        
        # Assert
        assert first_name is None
        assert last_name is None

    def test_parse_user_name_whitespace(self):
        """Test parse_user_name with whitespace."""
        # Arrange
        user_metadata = {"full_name": "  John   Doe  "}
        
        # Act
        first_name, last_name = parse_user_name(user_metadata)
        
        # Assert
        # The function doesn't strip whitespace, so the first part includes leading spaces
        assert first_name == ""  # Empty because the first split part is just spaces
        assert last_name == " John   Doe  "  # Everything after the first space