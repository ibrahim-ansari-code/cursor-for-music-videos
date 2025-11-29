"""
Unit tests for the Tenant Invitations API endpoints using hybrid testing pattern.

Tests HTTP endpoints with mocked service layer dependencies.
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.models.tenant_portal_invitation import InvitationStatus
from Backend.api.tenant_invitations.schemas import (
    InvitationResponse,
    InvitationListResponse,
    InvitationRevokeResponse,
    InvitationResendResponse,
    InvitationValidateResponse,
    InvitationAcceptResponse,
)
from Backend.api.auth import get_current_user
from Backend.api.auth.dependencies import get_current_user_no_subscription_check
from Backend.database import get_session

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Ensure dependency overrides are cleared after each test."""
    yield
    app.dependency_overrides.clear()


class TestClientWithHost(TestClient):
    """Custom TestClient that sets proper host header."""
    
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type="LANDLORD"):
    """Helper function to create a properly initialized test user."""
    now = datetime.now(timezone.utc)
    return User(
        id=user_id or uuid4(),
        email=email,
        first_name="Test",
        last_name="User",
        user_type=user_type,
        is_active=True,
        is_admin=False,
        created_at=now,
        updated_at=now,
        is_email_verified=True
    )


def create_mock_invitation_response(
    tenant_id: int = 1,
    status: InvitationStatus = InvitationStatus.PENDING,
) -> InvitationResponse:
    """Create a mock invitation response."""
    now = datetime.now(timezone.utc)
    return InvitationResponse(
        id=uuid4(),
        tenant_id=tenant_id,
        invited_by=uuid4(),
        email="tenant@example.com",
        status=status,
        created_at=now,
        expires_at=now + timedelta(days=7),
        tenant_name="John Doe",
        tenant_email="tenant@example.com",
    )


# =============================================================================
# CREATE INVITATION TESTS
# =============================================================================

def test_create_invitation_success(mocker):
    """Test successful invitation creation."""
    mock_user = create_test_user(user_type="LANDLORD")
    mock_response = create_mock_invitation_response()
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.create_invitation",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post(
            "/api/tenant-invitations/invitations",
            json={"tenant_id": 1},
        )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["tenant_id"] == 1
    assert data["status"] == "pending"


def test_create_invitation_tenant_forbidden(mocker):
    """Test that tenant users cannot create invitations."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post(
            "/api/tenant-invitations/invitations",
            json={"tenant_id": 1},
        )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "landlords" in response.json()["detail"].lower()


def test_create_invitation_bad_request(mocker):
    """Test invitation creation returns 400 for invalid tenant."""
    mock_user = create_test_user(user_type="LANDLORD")
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.create_invitation",
        new=AsyncMock(return_value=None),  # Service returns None for invalid
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.post(
            "/api/tenant-invitations/invitations",
            json={"tenant_id": 999},
        )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# LIST INVITATIONS TESTS
# =============================================================================

def test_list_invitations_success(mocker):
    """Test listing invitations."""
    mock_user = create_test_user(user_type="LANDLORD")
    mock_response = InvitationListResponse(
        invitations=[create_mock_invitation_response()],
        total=1,
    )
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.list_invitations",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/invitations")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["invitations"]) == 1


def test_list_invitations_with_status_filter(mocker):
    """Test listing invitations with status filter."""
    mock_user = create_test_user(user_type="LANDLORD")
    mock_response = InvitationListResponse(invitations=[], total=0)
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.list_invitations",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get(
            "/api/tenant-invitations/invitations?status_filter=pending"
        )
    
    assert response.status_code == status.HTTP_200_OK


def test_list_invitations_tenant_forbidden(mocker):
    """Test that tenant users cannot list invitations."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/invitations")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# GET INVITATION FOR TENANT TESTS
# =============================================================================

def test_get_invitation_for_tenant_success(mocker):
    """Test getting invitation for specific tenant."""
    mock_user = create_test_user(user_type="LANDLORD")
    mock_response = create_mock_invitation_response(tenant_id=5)
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.get_invitation_for_tenant",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/invitations/tenant/5")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tenant_id"] == 5


def test_get_invitation_for_tenant_not_found(mocker):
    """Test getting invitation when none exists."""
    mock_user = create_test_user(user_type="LANDLORD")
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.get_invitation_for_tenant",
        new=AsyncMock(return_value=None),
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/invitations/tenant/999")
    
    # Returns null body with 200 (nullable response)
    assert response.status_code == status.HTTP_200_OK


def test_get_invitation_for_tenant_forbidden(mocker):
    """Test tenant cannot get invitation info."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/invitations/tenant/5")
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# REVOKE INVITATION TESTS
# =============================================================================

def test_revoke_invitation_success(mocker):
    """Test revoking an invitation."""
    mock_user = create_test_user(user_type="LANDLORD")
    mock_response = InvitationRevokeResponse(
        success=True,
        message="Invitation revoked successfully",
    )
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.revoke_invitation",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    invitation_id = str(uuid4())
    with TestClientWithHost(app) as client:
        response = client.delete(
            f"/api/tenant-invitations/invitations/{invitation_id}"
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True


def test_revoke_invitation_tenant_forbidden(mocker):
    """Test tenant cannot revoke invitations."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    invitation_id = str(uuid4())
    with TestClientWithHost(app) as client:
        response = client.delete(
            f"/api/tenant-invitations/invitations/{invitation_id}"
        )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# RESEND INVITATION TESTS
# =============================================================================

def test_resend_invitation_success(mocker):
    """Test resending an invitation."""
    mock_user = create_test_user(user_type="LANDLORD")
    mock_response = InvitationResendResponse(
        success=True,
        message="Invitation resent successfully",
        new_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.resend_invitation",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    invitation_id = str(uuid4())
    with TestClientWithHost(app) as client:
        response = client.post(
            f"/api/tenant-invitations/invitations/{invitation_id}/resend"
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True


def test_resend_invitation_tenant_forbidden(mocker):
    """Test tenant cannot resend invitations."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    invitation_id = str(uuid4())
    with TestClientWithHost(app) as client:
        response = client.post(
            f"/api/tenant-invitations/invitations/{invitation_id}/resend"
        )
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# VALIDATE TOKEN TESTS (PUBLIC ENDPOINT)
# =============================================================================

def test_validate_invitation_success(mocker):
    """Test validating an invitation token."""
    mock_response = InvitationValidateResponse(
        valid=True,
        email="tenant@example.com",
        tenant_name="John Doe",
        landlord_name="Test Landlord",
        property_name="Test Property",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.validate_token",
        new=AsyncMock(return_value=mock_response),
    )
    
    # Public endpoint - no auth required
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    token = "a" * 43  # Valid token length (~43 chars from secrets.token_urlsafe(32))
    with TestClientWithHost(app) as client:
        response = client.get(
            f"/api/tenant-invitations/validate-invite?token={token}"
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is True
    assert data["email"] == "tenant@example.com"


def test_validate_invitation_invalid_token(mocker):
    """Test validating an invalid token."""
    mock_response = InvitationValidateResponse(
        valid=False,
        message="Invalid invitation link",
    )
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.validate_token",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    token = "b" * 43  # Valid token length
    with TestClientWithHost(app) as client:
        response = client.get(
            f"/api/tenant-invitations/validate-invite?token={token}"
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["valid"] is False


def test_validate_invitation_token_too_short(mocker):
    """Test validation rejects tokens that are too short (min 40 chars)."""
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    with TestClientWithHost(app) as client:
        # Token must be at least 40 chars
        response = client.get(
            "/api/tenant-invitations/validate-invite?token=short_token_only_30chars"
        )
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# ACCEPT INVITATION TESTS
# =============================================================================

def test_accept_invitation_success(mocker):
    """Test accepting an invitation."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    mock_response = InvitationAcceptResponse(
        success=True,
        message="Welcome to the Tenant Portal!",
        tenant_id=1,
    )
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.accept_invitation",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user_no_subscription_check] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    token = "c" * 43  # Valid token length
    with TestClientWithHost(app) as client:
        response = client.post(
            "/api/tenant-invitations/accept-invite",
            json={"token": token},
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is True
    assert data["tenant_id"] == 1


def test_accept_invitation_email_mismatch(mocker):
    """Test accepting invitation with mismatched email returns generic error."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    # Generic message to prevent account enumeration
    mock_response = InvitationAcceptResponse(
        success=False,
        message="Unable to accept invitation. Please try again or contact support.",
    )
    
    mocker.patch(
        "Backend.api.tenant_invitations.router.TenantInvitationService.accept_invitation",
        new=AsyncMock(return_value=mock_response),
    )
    
    app.dependency_overrides[get_current_user_no_subscription_check] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    
    token = "d" * 43  # Valid token length
    with TestClientWithHost(app) as client:
        response = client.post(
            "/api/tenant-invitations/accept-invite",
            json={"token": token},
        )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["success"] is False
    # Generic message doesn't reveal specific failure reason
    assert "unable to accept" in data["message"].lower()


# =============================================================================
# PORTAL STATUS TESTS
# =============================================================================

def test_get_portal_status_tenant_with_access(mocker):
    """Test portal status for tenant with linked account."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    
    # Mock tenant query
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    mock_tenant.current_property = None
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_tenant
    mock_session.execute.return_value = mock_result
    
    app.dependency_overrides[get_current_user_no_subscription_check] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/status")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["has_portal_access"] is True
    assert data["tenant_id"] == 1
    # Note: landlord_id is intentionally excluded for security


def test_get_portal_status_tenant_no_access(mocker):
    """Test portal status for tenant without linked account."""
    mock_user = create_test_user(user_type=UserType.TENANT.value)
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    app.dependency_overrides[get_current_user_no_subscription_check] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/status")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["has_portal_access"] is False
    assert data["tenant_id"] is None


def test_get_portal_status_landlord(mocker):
    """Test portal status for landlord."""
    mock_user = create_test_user(user_type="LANDLORD")
    
    # Mock tenant query for landlord (tenants with portal access)
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_tenant]
    mock_session.execute.return_value = mock_result
    
    app.dependency_overrides[get_current_user_no_subscription_check] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: mock_session
    
    with TestClientWithHost(app) as client:
        response = client.get("/api/tenant-invitations/status")
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["user_type"] == "landlord"
    assert data["tenants_with_portal_access"] == 1

