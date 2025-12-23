"""
Unit tests for the Tenant Invitations service layer.

Tests business logic for invitation creation, validation, acceptance, and revocation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from Backend.api.tenant_invitations.service import (
    TenantInvitationService,
    normalize_email,
    TOKEN_LENGTH,
    INVITATION_EXPIRY_DAYS,
)
from Backend.api.tenant_invitations.schemas import (
    InvitationCreateRequest,
    InvitationResponse,
)
from Backend.models.tenant_portal_invitation import (
    TenantPortalInvitation,
    InvitationStatus,
    hash_token,
)
from Backend.models.tenant import Tenant
from Backend.models.enums import TenantType, UserType
from Backend.models.user import User

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_landlord():
    """Create a mock landlord user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "landlord@example.com"
    user.first_name = "Test"
    user.last_name = "Landlord"
    user.user_type = UserType.LANDLORD
    return user


@pytest.fixture
def mock_tenant_user():
    """Create a mock tenant user."""
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "tenant@example.com"
    user.first_name = "John"
    user.last_name = "Doe"
    user.user_type = UserType.TENANT
    return user


@pytest.fixture
def mock_tenant(mock_landlord):
    """Create a mock tenant."""
    tenant = MagicMock(spec=Tenant)
    tenant.id = 1
    tenant.email = "tenant@example.com"
    tenant.first_name = "John"
    tenant.last_name = "Doe"
    tenant.tenant_type = TenantType.INDIVIDUAL
    tenant.landlord_id = mock_landlord.id
    tenant.user_id = None  # Not linked yet
    tenant.current_property = None
    tenant.assigned_units = []
    return tenant


@pytest.fixture
def mock_invitation(mock_tenant, mock_landlord):
    """Create a mock invitation."""
    invitation = MagicMock(spec=TenantPortalInvitation)
    invitation.id = uuid4()
    invitation.tenant_id = mock_tenant.id
    invitation.invited_by = mock_landlord.id
    invitation.email = mock_tenant.email
    invitation.invitation_token = "test_token_12345678901234567890123456789012"
    invitation.status = InvitationStatus.PENDING
    invitation.created_at = datetime.now(timezone.utc)
    invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    invitation.accepted_at = None
    invitation.revoked_at = None
    invitation.tenant = mock_tenant
    invitation.inviter = mock_landlord
    return invitation


# =============================================================================
# hash_token Tests
# =============================================================================

def test_hash_token_produces_hex_string():
    """Test hash_token produces a valid hex string."""
    result = hash_token("test_token_12345678901234567890123456789012")
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 produces 64 hex chars


def test_hash_token_deterministic():
    """Test hash_token produces same output for same input."""
    token = "same_token_12345678901234567890123456789"
    assert hash_token(token) == hash_token(token)


def test_hash_token_different_inputs():
    """Test hash_token produces different outputs for different inputs."""
    assert hash_token("token_a_12345678901234567890123456789") != hash_token("token_b_12345678901234567890123456789")


# =============================================================================
# normalize_email Tests
# =============================================================================

def test_normalize_email_strips_whitespace():
    """Test email normalization strips whitespace."""
    assert normalize_email("  test@example.com  ") == "test@example.com"


def test_normalize_email_lowercase():
    """Test email normalization converts to lowercase."""
    assert normalize_email("Test@EXAMPLE.COM") == "test@example.com"


def test_normalize_email_unicode_nfc():
    """Test email normalization applies Unicode NFC."""
    # Combining character é (e + combining acute) vs precomposed é
    combining = "cafe\u0301@example.com"  # e + combining acute
    precomposed = "café@example.com"  # precomposed é
    assert normalize_email(combining) == normalize_email(precomposed)


def test_normalize_email_combined():
    """Test email normalization with multiple transformations."""
    assert normalize_email("  Test.User@EXAMPLE.COM  ") == "test.user@example.com"


# =============================================================================
# create_invitation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_create_invitation_success(mock_session, mock_landlord, mock_tenant):
    """Test successful invitation creation."""
    # Setup mock query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant
    
    # No existing invitation
    mock_existing_result = MagicMock()
    mock_existing_result.scalar_one_or_none.return_value = None
    
    # Mock for expire old invitations (update statement)
    mock_expire_result = MagicMock()
    
    mock_session.execute.side_effect = [mock_result, mock_expire_result, mock_existing_result]
    
    # Mock refresh to set ID and timestamps
    def refresh_side_effect(obj):
        obj.id = uuid4()
        obj.created_at = datetime.now(timezone.utc)
        obj.expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)
    mock_session.refresh.side_effect = refresh_side_effect
    
    # Mock email sending
    with patch.object(
        TenantInvitationService, '_send_invitation_email', new_callable=AsyncMock
    ) as mock_send_email:
        mock_send_email.return_value = True
        
        request = InvitationCreateRequest(tenant_id=mock_tenant.id)
        result = await TenantInvitationService.create_invitation(
            db=mock_session,
            landlord_id=mock_landlord.id,
            request=request,
        )
    
    assert result is not None
    assert result.tenant_id == mock_tenant.id
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_invitation_tenant_not_found(mock_session, mock_landlord):
    """Test invitation creation when tenant not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    request = InvitationCreateRequest(tenant_id=999)
    result = await TenantInvitationService.create_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        request=request,
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_create_invitation_tenant_no_email(mock_session, mock_landlord, mock_tenant):
    """Test invitation creation when tenant has no email."""
    mock_tenant.email = None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = mock_result
    
    request = InvitationCreateRequest(tenant_id=mock_tenant.id)
    result = await TenantInvitationService.create_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        request=request,
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_create_invitation_tenant_already_has_access(mock_session, mock_landlord, mock_tenant):
    """Test invitation creation when tenant already has portal access."""
    mock_tenant.user_id = uuid4()  # Already linked
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = mock_result
    
    request = InvitationCreateRequest(tenant_id=mock_tenant.id)
    result = await TenantInvitationService.create_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        request=request,
    )
    
    assert result is None


@pytest.mark.asyncio
async def test_create_invitation_returns_existing_pending(mock_session, mock_landlord, mock_tenant, mock_invitation):
    """Test that creating invitation returns existing pending one."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant
    
    # Mock for expire old invitations (update statement)
    mock_expire_result = MagicMock()
    
    mock_existing_result = MagicMock()
    mock_existing_result.scalar_one_or_none.return_value = mock_invitation
    
    mock_session.execute.side_effect = [mock_result, mock_expire_result, mock_existing_result]
    
    request = InvitationCreateRequest(tenant_id=mock_tenant.id)
    result = await TenantInvitationService.create_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        request=request,
    )
    
    assert result is not None
    assert result.id == mock_invitation.id
    # Should not create new invitation
    mock_session.add.assert_not_called()


# =============================================================================
# revoke_invitation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_revoke_invitation_success(mock_session, mock_landlord, mock_invitation):
    """Test successful invitation revocation."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.revoke_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        invitation_id=mock_invitation.id,
    )
    
    assert result.success is True
    assert "revoked" in result.message.lower()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_revoke_invitation_not_found(mock_session, mock_landlord):
    """Test revocation when invitation not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.revoke_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        invitation_id=uuid4(),
    )
    
    assert result.success is False
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_revoke_invitation_already_accepted(mock_session, mock_landlord, mock_invitation):
    """Test revocation when invitation already accepted."""
    mock_invitation.status = InvitationStatus.ACCEPTED
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.revoke_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        invitation_id=mock_invitation.id,
    )
    
    assert result.success is False
    assert "ACCEPTED" in result.message


# =============================================================================
# validate_token Tests
# =============================================================================

@pytest.mark.asyncio
async def test_validate_token_success(mock_session, mock_invitation, mock_landlord):
    """Test successful token validation."""
    mock_invitation.tenant.tenant_type = TenantType.INDIVIDUAL
    mock_invitation.tenant.first_name = "John"
    mock_invitation.tenant.last_name = "Doe"
    mock_invitation.inviter = mock_landlord
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.validate_token(
        db=mock_session,
        token=mock_invitation.invitation_token,
    )
    
    assert result.valid is True
    assert result.email == mock_invitation.email
    assert result.tenant_name is not None


@pytest.mark.asyncio
async def test_validate_token_invalid(mock_session):
    """Test validation with invalid token."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.validate_token(
        db=mock_session,
        token="invalid_token_12345678901234567890123",
    )
    
    assert result.valid is False
    assert "invalid" in result.message.lower()


@pytest.mark.asyncio
async def test_validate_token_expired(mock_session, mock_invitation):
    """Test validation with expired token."""
    mock_invitation.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.validate_token(
        db=mock_session,
        token=mock_invitation.invitation_token,
    )
    
    assert result.valid is False
    assert "expired" in result.message.lower()


@pytest.mark.asyncio
async def test_validate_token_already_accepted(mock_session, mock_invitation):
    """Test validation with already accepted token."""
    mock_invitation.status = InvitationStatus.ACCEPTED
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.validate_token(
        db=mock_session,
        token=mock_invitation.invitation_token,
    )
    
    assert result.valid is False
    assert "accepted" in result.message.lower()


# =============================================================================
# accept_invitation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_accept_invitation_success(mock_session, mock_invitation, mock_tenant_user):
    """Test successful invitation acceptance."""
    mock_tenant_user.email = mock_invitation.email
    mock_invitation.tenant.user_id = None
    
    # Mock invitation query
    mock_inv_result = MagicMock()
    mock_inv_result.scalar_one_or_none.return_value = mock_invitation
    
    # Mock user query
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = mock_tenant_user
    
    mock_session.execute.side_effect = [mock_inv_result, mock_user_result]
    
    # Mock seat availability check
    with patch('Backend.api.tenant_invitations.service.SeatManagementService.get_seat_availability', new_callable=AsyncMock) as mock_seat_check:
        mock_seat_check.return_value = {
            "used": 5,
            "limit": 10,
            "available": 5
        }
        
        result = await TenantInvitationService.accept_invitation(
            db=mock_session,
            token=mock_invitation.invitation_token,
            user_id=mock_tenant_user.id,
        )
    
    assert result.success is True
    assert result.tenant_id == mock_invitation.tenant_id
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_accept_invitation_email_mismatch(mock_session, mock_invitation, mock_tenant_user):
    """Test acceptance fails when email doesn't match (returns generic message)."""
    mock_tenant_user.email = "different@example.com"
    mock_invitation.email = "tenant@example.com"
    
    mock_inv_result = MagicMock()
    mock_inv_result.scalar_one_or_none.return_value = mock_invitation
    
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = mock_tenant_user
    
    mock_session.execute.side_effect = [mock_inv_result, mock_user_result]
    
    result = await TenantInvitationService.accept_invitation(
        db=mock_session,
        token=mock_invitation.invitation_token,
        user_id=mock_tenant_user.id,
    )
    
    assert result.success is False
    # Generic message to prevent enumeration (doesn't reveal email mismatch)
    assert "unable to accept" in result.message.lower()


@pytest.mark.asyncio
async def test_accept_invitation_tenant_already_linked(mock_session, mock_invitation, mock_tenant_user):
    """Test acceptance fails when tenant already linked."""
    mock_tenant_user.email = mock_invitation.email
    mock_invitation.tenant.user_id = uuid4()  # Already linked
    
    mock_inv_result = MagicMock()
    mock_inv_result.scalar_one_or_none.return_value = mock_invitation
    
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = mock_tenant_user
    
    mock_session.execute.side_effect = [mock_inv_result, mock_user_result]
    
    result = await TenantInvitationService.accept_invitation(
        db=mock_session,
        token=mock_invitation.invitation_token,
        user_id=mock_tenant_user.id,
    )
    
    assert result.success is False
    assert "already linked" in result.message.lower()


@pytest.mark.asyncio
async def test_accept_invitation_invalid_token(mock_session, mock_tenant_user):
    """Test acceptance fails with invalid token."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.accept_invitation(
        db=mock_session,
        token="invalid_token",
        user_id=mock_tenant_user.id,
    )
    
    assert result.success is False
    assert "invalid" in result.message.lower()


# =============================================================================
# get_invitation_for_tenant Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_invitation_for_tenant_success(mock_session, mock_landlord, mock_invitation):
    """Test getting invitation for specific tenant."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.get_invitation_for_tenant(
        db=mock_session,
        landlord_id=mock_landlord.id,
        tenant_id=mock_invitation.tenant_id,
    )
    
    assert result is not None
    assert result.tenant_id == mock_invitation.tenant_id


@pytest.mark.asyncio
async def test_get_invitation_for_tenant_not_found(mock_session, mock_landlord):
    """Test when no invitation exists for tenant."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.get_invitation_for_tenant(
        db=mock_session,
        landlord_id=mock_landlord.id,
        tenant_id=999,
    )
    
    assert result is None


# =============================================================================
# list_invitations Tests
# =============================================================================

@pytest.mark.asyncio
async def test_list_invitations_success(mock_session, mock_landlord, mock_invitation):
    """Test listing invitations for landlord."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_invitation]
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.list_invitations(
        db=mock_session,
        landlord_id=mock_landlord.id,
    )
    
    assert result.total == 1
    assert len(result.invitations) == 1


@pytest.mark.asyncio
async def test_list_invitations_with_status_filter(mock_session, mock_landlord, mock_invitation):
    """Test listing invitations with status filter."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_invitation]
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.list_invitations(
        db=mock_session,
        landlord_id=mock_landlord.id,
        status_filter=InvitationStatus.PENDING,
    )
    
    assert result.total == 1


@pytest.mark.asyncio
async def test_list_invitations_empty(mock_session, mock_landlord):
    """Test listing invitations when none exist."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.list_invitations(
        db=mock_session,
        landlord_id=mock_landlord.id,
    )
    
    assert result.total == 0
    assert len(result.invitations) == 0


# =============================================================================
# resend_invitation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_resend_invitation_success(mock_session, mock_landlord, mock_invitation):
    """Test successful invitation resend."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    with patch.object(
        TenantInvitationService, '_send_invitation_email', new_callable=AsyncMock
    ) as mock_send:
        mock_send.return_value = True
        
        result = await TenantInvitationService.resend_invitation(
            db=mock_session,
            landlord_id=mock_landlord.id,
            invitation_id=mock_invitation.id,
        )
    
    assert result.success is True
    assert result.new_expires_at is not None
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_resend_invitation_not_found(mock_session, mock_landlord):
    """Test resend when invitation not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.resend_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        invitation_id=uuid4(),
    )
    
    assert result.success is False
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_resend_invitation_wrong_status(mock_session, mock_landlord, mock_invitation):
    """Test resend fails for accepted invitation."""
    mock_invitation.status = InvitationStatus.ACCEPTED
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_invitation
    mock_session.execute.return_value = mock_result
    
    result = await TenantInvitationService.resend_invitation(
        db=mock_session,
        landlord_id=mock_landlord.id,
        invitation_id=mock_invitation.id,
    )
    
    assert result.success is False
    assert "ACCEPTED" in result.message


# =============================================================================
# _build_invitation_response Tests
# =============================================================================

@pytest.mark.asyncio
async def test_build_invitation_response_individual_tenant(mock_invitation, mock_tenant):
    """Test building response for individual tenant."""
    mock_tenant.tenant_type = TenantType.INDIVIDUAL
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"
    
    result = await TenantInvitationService._build_invitation_response(
        mock_invitation, mock_tenant
    )
    
    assert result.tenant_name == "John Doe"
    assert result.tenant_email == mock_tenant.email


@pytest.mark.asyncio
async def test_build_invitation_response_company_tenant(mock_invitation, mock_tenant):
    """Test building response for company tenant."""
    mock_tenant.tenant_type = TenantType.COMPANY
    mock_tenant.company_name = "Tech Corp"
    
    result = await TenantInvitationService._build_invitation_response(
        mock_invitation, mock_tenant
    )
    
    assert result.tenant_name == "Tech Corp"


@pytest.mark.asyncio
async def test_build_invitation_response_no_tenant(mock_invitation):
    """Test building response when tenant is None."""
    result = await TenantInvitationService._build_invitation_response(
        mock_invitation, None
    )
    
    assert result.tenant_name is None
    assert result.tenant_email is None

