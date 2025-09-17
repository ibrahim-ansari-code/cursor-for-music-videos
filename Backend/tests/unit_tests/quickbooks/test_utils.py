"""
Unit tests for QuickBooks utils module.

These tests focus on the get_or_create_integration function, particularly
the backfill logic for legacy integration records (lines 239-249).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, UTC

from Backend.api.quickbooks.utils import get_or_create_integration
from Backend.models.user import User
from Backend.models.accounting.integration import Integration, IntegrationStatus, IntegrationType

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestGetOrCreateIntegration:
    """Test the get_or_create_integration function."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = MagicMock(spec=User)
        user.id = uuid4()
        return user

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.scalar = AsyncMock()
        return session

    @pytest.fixture
    def mock_integration_with_missing_fields(self, mock_user):
        """Create a mock integration with missing consumer_id and service_id."""
        integration = MagicMock(spec=Integration)
        integration.user_id = mock_user.id
        integration.integration_type = IntegrationType.QUICKBOOKS
        integration.apideck_consumer_id = None  # Missing
        integration.apideck_service_id = None   # Missing
        integration.status = IntegrationStatus.DISCONNECTED
        return integration

    @pytest.fixture
    def mock_integration_with_empty_consumer_id(self, mock_user):
        """Create a mock integration with empty consumer_id."""
        integration = MagicMock(spec=Integration)
        integration.user_id = mock_user.id
        integration.integration_type = IntegrationType.QUICKBOOKS
        integration.apideck_consumer_id = ""    # Empty string
        integration.apideck_service_id = "quickbooks"
        integration.status = IntegrationStatus.DISCONNECTED
        return integration

    @pytest.fixture
    def mock_integration_with_empty_service_id(self, mock_user):
        """Create a mock integration with empty service_id."""
        integration = MagicMock(spec=Integration)
        integration.user_id = mock_user.id
        integration.integration_type = IntegrationType.QUICKBOOKS
        integration.apideck_consumer_id = f"brikli-{mock_user.id}-quickbooks-existing"
        integration.apideck_service_id = ""     # Empty string
        integration.status = IntegrationStatus.DISCONNECTED
        return integration

    @pytest.fixture
    def mock_integration_complete(self, mock_user):
        """Create a mock integration with all fields populated."""
        integration = MagicMock(spec=Integration)
        integration.user_id = mock_user.id
        integration.integration_type = IntegrationType.QUICKBOOKS
        integration.apideck_consumer_id = f"brikli-{mock_user.id}-quickbooks-existing"
        integration.apideck_service_id = "quickbooks"
        integration.status = IntegrationStatus.CONNECTED
        return integration

    async def test_create_new_integration_when_none_exists(self, mock_user, mock_session):
        """Test creating a new integration when none exists."""
        # Setup - no existing integration
        mock_session.scalar.return_value = None

        # Execute
        with patch('Backend.api.quickbooks.utils.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "abc123"
            result = await get_or_create_integration(
                user=mock_user,
                session=mock_session,
                integration_type=IntegrationType.QUICKBOOKS,
                service_id="quickbooks"
            )

        # Verify a new integration was created
        mock_session.add.assert_called_once()
        created_integration = mock_session.add.call_args[0][0]

        assert created_integration.user_id == mock_user.id
        assert created_integration.integration_type == IntegrationType.QUICKBOOKS
        assert created_integration.apideck_consumer_id == f"brikli-{mock_user.id}-quickbooks-abc123"
        assert created_integration.apideck_service_id == "quickbooks"
        assert created_integration.status == IntegrationStatus.DISCONNECTED

        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    async def test_backfill_missing_consumer_id_and_service_id(
        self, mock_user, mock_session, mock_integration_with_missing_fields
    ):
        """Test backfill when both consumer_id and service_id are missing."""
        # Setup - existing integration with missing fields
        mock_session.scalar.return_value = mock_integration_with_missing_fields

        # Execute
        with patch('Backend.api.quickbooks.utils.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "def456"
            result = await get_or_create_integration(
                user=mock_user,
                session=mock_session,
                integration_type=IntegrationType.QUICKBOOKS,
                service_id="quickbooks"
            )

        # Verify backfill occurred
        expected_consumer_id = f"brikli-{mock_user.id}-quickbooks-def456"
        assert mock_integration_with_missing_fields.apideck_consumer_id == expected_consumer_id
        assert mock_integration_with_missing_fields.apideck_service_id == "quickbooks"

        # Verify session operations for update
        mock_session.add.assert_called_once_with(mock_integration_with_missing_fields)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_integration_with_missing_fields)

    async def test_backfill_empty_consumer_id_only(
        self, mock_user, mock_session, mock_integration_with_empty_consumer_id
    ):
        """Test backfill when only consumer_id is empty."""
        # Setup - existing integration with empty consumer_id
        mock_session.scalar.return_value = mock_integration_with_empty_consumer_id

        # Execute
        with patch('Backend.api.quickbooks.utils.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "ghi789"
            result = await get_or_create_integration(
                user=mock_user,
                session=mock_session,
                integration_type=IntegrationType.QUICKBOOKS,
                service_id="quickbooks"
            )

        # Verify only consumer_id was backfilled
        expected_consumer_id = f"brikli-{mock_user.id}-quickbooks-ghi789"
        assert mock_integration_with_empty_consumer_id.apideck_consumer_id == expected_consumer_id
        assert mock_integration_with_empty_consumer_id.apideck_service_id == "quickbooks"  # Unchanged

        # Verify session operations for update
        mock_session.add.assert_called_once_with(mock_integration_with_empty_consumer_id)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_integration_with_empty_consumer_id)

    async def test_backfill_empty_service_id_only(
        self, mock_user, mock_session, mock_integration_with_empty_service_id
    ):
        """Test backfill when only service_id is empty."""
        # Setup - existing integration with empty service_id
        mock_session.scalar.return_value = mock_integration_with_empty_service_id
        original_consumer_id = mock_integration_with_empty_service_id.apideck_consumer_id

        # Execute
        result = await get_or_create_integration(
            user=mock_user,
            session=mock_session,
            integration_type=IntegrationType.QUICKBOOKS,
            service_id="quickbooks"
        )

        # Verify only service_id was backfilled
        assert mock_integration_with_empty_service_id.apideck_consumer_id == original_consumer_id  # Unchanged
        assert mock_integration_with_empty_service_id.apideck_service_id == "quickbooks"

        # Verify session operations for update
        mock_session.add.assert_called_once_with(mock_integration_with_empty_service_id)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(mock_integration_with_empty_service_id)

    async def test_no_update_when_all_fields_present(
        self, mock_user, mock_session, mock_integration_complete
    ):
        """Test no backfill when all fields are already present."""
        # Setup - existing integration with all fields
        mock_session.scalar.return_value = mock_integration_complete
        original_consumer_id = mock_integration_complete.apideck_consumer_id
        original_service_id = mock_integration_complete.apideck_service_id

        # Execute
        result = await get_or_create_integration(
            user=mock_user,
            session=mock_session,
            integration_type=IntegrationType.QUICKBOOKS,
            service_id="quickbooks"
        )

        # Verify no changes occurred
        assert mock_integration_complete.apideck_consumer_id == original_consumer_id
        assert mock_integration_complete.apideck_service_id == original_service_id

        # Verify no session operations for update
        mock_session.add.assert_not_called()
        mock_session.flush.assert_not_called()
        mock_session.refresh.assert_not_called()

        # Verify the existing integration was returned
        assert result == mock_integration_complete

    async def test_custom_service_id(self, mock_user, mock_session):
        """Test creating integration with custom service_id."""
        # Setup - no existing integration
        mock_session.scalar.return_value = None
        custom_service_id = "quickbooks-sandbox"

        # Execute
        with patch('Backend.api.quickbooks.utils.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "custom123"
            result = await get_or_create_integration(
                user=mock_user,
                session=mock_session,
                integration_type=IntegrationType.QUICKBOOKS,
                service_id=custom_service_id
            )

        # Verify custom service_id was used
        created_integration = mock_session.add.call_args[0][0]
        assert created_integration.apideck_service_id == custom_service_id

    async def test_different_integration_type(self, mock_user, mock_session):
        """Test creating integration with different integration type."""
        # Setup - no existing integration
        mock_session.scalar.return_value = None

        # Execute with a different integration type
        with patch('Backend.api.quickbooks.utils.uuid4') as mock_uuid:
            mock_uuid.return_value.hex = "other123"
            # Assuming there might be other integration types in the future
            result = await get_or_create_integration(
                user=mock_user,
                session=mock_session,
                integration_type=IntegrationType.QUICKBOOKS,  # Using QUICKBOOKS for now
                service_id="quickbooks"
            )

        # Verify integration type was set correctly
        created_integration = mock_session.add.call_args[0][0]
        assert created_integration.integration_type == IntegrationType.QUICKBOOKS
        assert "quickbooks" in created_integration.apideck_consumer_id