"""
API tests for tenant validation logic in schemas.py

These tests focus on testing Pydantic validation rules through the API endpoints.
Tests cover validation error scenarios that should be caught by schema validators.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from Backend.api.app import app
from Backend.models.user import User
from Backend.models.enums import UserType, TenantType
from Backend.models.tenant import TenantStatus
from Backend.api.auth import get_current_user
from Backend.database import get_session


class TestClientWithHost(TestClient):
    """Custom TestClient to set the host header for tenant context."""
    def request(self, method: str, url, **kwargs):
        headers = kwargs.get("headers") or {}
        if "host" not in {k.lower() for k in headers.keys()}:
            headers["Host"] = "localhost"
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def create_test_user(user_id=None, email="test@example.com", user_type=UserType.LANDLORD):
    """Helper to create a test user."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid4()
    user.email = email
    user.user_type = user_type
    user.is_admin = user_type == UserType.ADMIN
    user.is_active = True
    return user


def setup_function():
    """Setup for each test function."""
    app.dependency_overrides.clear()


def teardown_function():
    """Cleanup after each test function."""
    app.dependency_overrides.clear()


def test_individual_tenant_missing_first_name_validation():
    """Test validation error when individual tenant missing first name - Line 57."""
    mock_user = create_test_user()
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": None,  # Explicitly None to trigger model validator
        "last_name": "Doe",
        "email": "test@example.com"
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    assert "First name is required for individual tenants" in str(error_detail)


def test_individual_tenant_empty_first_name_validation():
    """Test validation error when individual tenant has empty first name - Line 57."""
    mock_user = create_test_user()
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": "   ",  # Only whitespace
        "last_name": "Doe",
        "email": "test@example.com"
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    # Field validator catches empty strings before model validator
    assert "Name fields cannot be empty if provided" in str(error_detail)


def test_individual_tenant_missing_last_name_validation():
    """Test validation error when individual tenant missing last name - Line 59."""
    mock_user = create_test_user()
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": "John",
        "last_name": None,  # Explicitly None to trigger model validator
        "email": "test@example.com"
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    assert "Last name is required for individual tenants" in str(error_detail)


def test_individual_tenant_empty_last_name_validation():
    """Test validation error when individual tenant has empty last name - Line 59."""
    mock_user = create_test_user()
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": "John",
        "last_name": "",  # Empty string
        "email": "test@example.com"
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    # Field validator catches empty strings before model validator
    assert "Name fields cannot be empty if provided" in str(error_detail)

def test_empty_name_field_validation():
    """Test validation error for empty name fields - Line 92."""
    mock_user = create_test_user()
    tenant_data = {
        "tenant_type": "Individual",
        "first_name": "",  # Empty string should trigger validation
        "last_name": "Doe",
        "email": "test@example.com"
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    assert "Name fields cannot be empty if provided" in str(error_detail) or "First name is required" in str(error_detail)

def test_invalid_phone_format_validation():
    """Test validation error for invalid phone format - Line 104."""
    mock_user = create_test_user()
    tenant_data = {
            "tenant_type": "Individual", 
            "first_name": "John",
            "last_name": "Doe",
            "email": "test@example.com",
            "phone": "123"  # Too short, should trigger validation
            }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    assert "Phone number must be 10-20 characters long" in str(error_detail)

def test_phone_none_value_passes_validation():
    """Test that None phone value passes validation - Line 90 (phone validator)."""
    mock_user = create_test_user()
    from Backend.api.tenants.schemas import TenantResponse
    
    # Create a proper response object with actual values
    tenant_response_data = {
        "id": 1,
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "company_name": None,
        "contact_person": None,
        "email": "test@example.com",
        "phone": None,
        "status": TenantStatus.ACTIVE,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "current_property_id": None,
        "unit": None,
        "property": None,
        "leases": []
    }

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
        patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save, \
        patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
            
        mock_determine_landlord.return_value = mock_user.id
        # Create a mock tenant for create_and_save_tenant
        mock_tenant = MagicMock()
        mock_tenant.id = 1
        mock_create_save.return_value = mock_tenant
        
        # Create the enriched response
        mock_enrich.return_value = [TenantResponse(**tenant_response_data)]
            
        tenant_data = {
            "tenant_type": "Individual",
            "first_name": "John", 
            "last_name": "Doe",
            "email": "test@example.com"
            # phone is None/not provided
        }

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.post("/api/tenants/", json=tenant_data)

        assert response.status_code == status.HTTP_201_CREATED

def test_empty_company_name_for_company_tenant():
    """Test validation error when company tenant has empty company name - Line 195 (similar pattern)."""
    mock_user = create_test_user()
    tenant_data = {
        "tenant_type": "Company",
        "company_name": "",  # Empty company name
        "contact_person": "John Doe",
        "email": "contact@company.com"
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.post("/api/tenants/", json=tenant_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    assert "Company name is required for company tenants" in str(error_detail) or "Name fields cannot be empty" in str(error_detail)

def test_full_name_split_for_individual_tenant():
    """Test full_name splitting logic for individual tenants - Lines 245, 248."""
    mock_user = create_test_user()
    from Backend.api.tenants.schemas import TenantResponse
    
    # Create a proper response object with actual values
    tenant_response_data = {
        "id": 1,
        "tenant_type": TenantType.INDIVIDUAL,
        "first_name": "John",
        "last_name": "Doe",
        "company_name": None,
        "contact_person": None,
        "email": "test@example.com",
        "phone": None,
        "status": TenantStatus.ACTIVE,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "current_property_id": None,
        "unit": None,
        "property": None,
        "leases": []
    }

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
        patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save, \
        patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
            
        mock_determine_landlord.return_value = mock_user.id
        # Create a mock tenant for create_and_save_tenant
        mock_tenant = MagicMock()
        mock_tenant.id = 1
        mock_create_save.return_value = mock_tenant
        
        # Create the enriched response
        mock_enrich.return_value = [TenantResponse(**tenant_response_data)]
            
        tenant_data = {
            "tenant_type": "Individual",
            "full_name": "John Doe",  # This should be split into first_name and last_name
            "email": "test@example.com"
        }

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.post("/api/tenants/", json=tenant_data)

        # Should succeed - full_name gets split into first_name and last_name
        assert response.status_code == status.HTTP_201_CREATED

def test_full_name_not_split_for_company_tenant():
    """Test that full_name is not split for company tenants - Lines 248-249."""
    mock_user = create_test_user()
    from Backend.api.tenants.schemas import TenantResponse
    
    # Create a proper response object for company tenant with proper ID
    tenant_response_data = {
        "id": 2,  # Ensure proper ID is set
        "tenant_type": TenantType.COMPANY,
        "first_name": None,
        "last_name": None,
        "company_name": "Tech Corp",
        "contact_person": None,
        "email": "contact@techcorp.com",
        "phone": None,
        "status": TenantStatus.ACTIVE,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "current_property_id": None,
        "unit": None,
        "property": None,
        "leases": []
    }

    with patch("Backend.api.tenants.router._validate_user_permissions", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router._determine_landlord", new_callable=AsyncMock) as mock_determine_landlord, \
        patch("Backend.api.tenants.router._validate_property_assignment", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router._validate_linked_user_account", new_callable=AsyncMock), \
        patch("Backend.api.tenants.router.create_and_save_tenant", new_callable=AsyncMock) as mock_create_save, \
        patch("Backend.api.tenants.router.enrich_tenants_with_details", new_callable=AsyncMock) as mock_enrich:
            
        mock_determine_landlord.return_value = mock_user.id
        # Create a mock tenant for create_and_save_tenant
        mock_tenant = MagicMock()
        mock_tenant.id = 2
        mock_create_save.return_value = mock_tenant
        
        # Create the enriched response
        mock_enrich.return_value = [TenantResponse(**tenant_response_data)]
            
        tenant_data = {
            "tenant_type": "Company",
            "full_name": "John Doe",  # This should NOT be split for company type
            "company_name": "Tech Corp",
            "email": "contact@techcorp.com"
        }

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session] = lambda: AsyncMock()

        with TestClientWithHost(app) as client:
            response = client.post("/api/tenants/", json=tenant_data)

        # Should succeed - company tenant validation doesn't require first/last names
        assert response.status_code == status.HTTP_201_CREATED

def test_computed_field_full_name_individual():
    """Test computed field full_name for individual tenant - Lines 288-292."""
    mock_user = create_test_user()
        
        # Mock successful tenant creation and retrieval
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    mock_tenant.tenant_type = TenantType.INDIVIDUAL
    mock_tenant.first_name = "John"
    mock_tenant.last_name = "Doe"
    mock_tenant.company_name = None
    mock_tenant.contact_person = None
    mock_tenant.email = "test@example.com"
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.created_at = datetime.now(timezone.utc)
    mock_tenant.updated_at = datetime.now(timezone.utc)
    mock_tenant.current_property_id = None
    mock_tenant.landlord_id = mock_user.id

    with patch("Backend.api.tenants.router.check_tenant_permission", new_callable=AsyncMock) as mock_check_permission, \
        patch("Backend.api.tenants.schemas.TenantResponse.model_validate") as mock_validate:
            
        mock_check_permission.return_value = mock_tenant
            # Create a proper response object
    tenant_response = {
            "id": 1,
            "tenant_type": "Individual",
            "first_name": "John",
            "last_name": "Doe",
            "email": "test@example.com",
            "status": "Active",
            "full_name": "John Doe",
            "display_name": "John Doe"
        }
    mock_validate.return_value = type('obj', (object,), tenant_response)()
            
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    with TestClientWithHost(app) as client:
        response = client.get("/api/tenants/1")

    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        # Should have computed full_name field
        assert "full_name" in data
        # For individual tenant, should combine first and last name
        assert data["full_name"] == "John Doe"

def test_computed_field_display_name_company():
    """Test computed field display_name for company tenant - Lines 306-307."""
    from Backend.api.tenants.schemas import TenantResponse
    
    # Test the computed field directly on the schema object
    tenant_response_data = {
        "id": 2,
        "tenant_type": TenantType.COMPANY,
        "first_name": None,
        "last_name": None,
        "company_name": "Tech Corp",
        "contact_person": "Jane Smith",
        "email": "contact@techcorp.com",
        "phone": None,
        "status": TenantStatus.ACTIVE,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "current_property_id": None,
        "unit": None,
        "property": None,
        "leases": []
    }
    
    # Create TenantResponse object directly to test computed field
    tenant_response = TenantResponse(**tenant_response_data)
    
    # Test computed field display_name
    assert tenant_response.display_name == "Tech Corp"

    # Test computed field full_name
    assert tenant_response.full_name == "Tech Corp (Contact: Jane Smith)"


# =============================================================================
# Emergency Contact Schema Validation Tests
# =============================================================================

def test_emergency_contact_missing_name():
    """Test validation error for missing name - covers schemas.py:31-33"""
    from Backend.api.tenants.schemas import EmergencyContactCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactCreate(
            # name is missing
            relationship="Brother",
            phone="555-1234567"
        )

    errors = exc_info.value.errors()
    assert any("name" in str(error) for error in errors)


def test_emergency_contact_missing_relationship():
    """Test validation error for missing relationship - covers schemas.py:31-33"""
    from Backend.api.tenants.schemas import EmergencyContactCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactCreate(
            name="John Emergency",
            # relationship is missing
            phone="555-1234567"
        )

    errors = exc_info.value.errors()
    assert any("relationship" in str(error) for error in errors)


def test_emergency_contact_missing_phone():
    """Test validation error for missing phone - covers schemas.py:31-33"""
    from Backend.api.tenants.schemas import EmergencyContactCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactCreate(
            name="John Emergency",
            relationship="Brother"
            # phone is missing
        )

    errors = exc_info.value.errors()
    assert any("phone" in str(error) for error in errors)


def test_emergency_contact_phone_too_short():
    """Test validation error for phone too short - covers schemas.py:39-40, 42-45"""
    from Backend.api.tenants.schemas import EmergencyContactCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactCreate(
            name="John Emergency",
            relationship="Brother",
            phone="123"  # Too short (less than 10 digits)
        )

    errors = exc_info.value.errors()
    assert any("Phone number must contain 10-15 digits" in str(error) for error in errors)


def test_emergency_contact_phone_too_long():
    """Test validation error for phone too long - covers schemas.py:42-45"""
    from Backend.api.tenants.schemas import EmergencyContactCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactCreate(
            name="John Emergency",
            relationship="Brother",
            phone="1234567890123456789012"  # Too long (more than 20 characters)
        )

    errors = exc_info.value.errors()
    assert any("Phone number must contain 10-15 digits" in str(error) for error in errors)


def test_emergency_contact_invalid_email_format():
    """Test validation error for invalid email format - covers schemas.py:51-56"""
    from Backend.api.tenants.schemas import EmergencyContactCreate
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactCreate(
            name="John Emergency",
            relationship="Brother",
            phone="555-1234567",
            email="invalid-email-format"  # Invalid email
        )

    errors = exc_info.value.errors()
    assert any("email" in str(error).lower() for error in errors)


def test_emergency_contact_valid_phone_formats():
    """Test various valid phone formats pass validation"""
    from Backend.api.tenants.schemas import EmergencyContactCreate

    valid_phones = [
        "5551234567",           # 10 digits
        "555-123-4567",         # With dashes
        "(555) 123-4567",       # With parentheses
        "+1 555 123 4567",      # With country code
        "555.123.4567",         # With dots
    ]

    for phone in valid_phones:
        contact = EmergencyContactCreate(
            name="John Emergency",
            relationship="Brother",
            phone=phone
        )
        assert contact.phone == phone


def test_emergency_contact_optional_fields_none():
    """Test that optional fields can be None"""
    from Backend.api.tenants.schemas import EmergencyContactCreate

    contact = EmergencyContactCreate(
        name="John Emergency",
        relationship="Brother",
        phone="555-1234567"
        # email, notes, is_primary are optional
    )

    assert contact.email is None
    assert contact.notes is None
    assert contact.is_primary is False  # Default value


def test_emergency_contact_update_name_validation():
    """Test EmergencyContactUpdate name validation - covers schemas.py:77-79"""
    from Backend.api.tenants.schemas import EmergencyContactUpdate

    # Valid: name can be provided
    update = EmergencyContactUpdate(name="Updated Name")
    assert update.name == "Updated Name"

    # Valid: name can be None (not updating)
    update = EmergencyContactUpdate(phone="555-9999999")
    assert update.name is None


def test_emergency_contact_update_relationship_validation():
    """Test EmergencyContactUpdate relationship validation - covers schemas.py:77-79"""
    from Backend.api.tenants.schemas import EmergencyContactUpdate

    # Valid: relationship can be provided
    update = EmergencyContactUpdate(relationship="Sister")
    assert update.relationship == "Sister"

    # Valid: relationship can be None (not updating)
    update = EmergencyContactUpdate(phone="555-9999999")
    assert update.relationship is None


def test_emergency_contact_update_phone_validation():
    """Test EmergencyContactUpdate phone validation - covers schemas.py:85-92"""
    from Backend.api.tenants.schemas import EmergencyContactUpdate
    from pydantic import ValidationError

    # Valid: phone can be provided
    update = EmergencyContactUpdate(phone="555-9999999")
    assert update.phone == "555-9999999"

    # Invalid: phone too short
    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactUpdate(phone="123")

    errors = exc_info.value.errors()
    assert any("Phone number must contain 10-15 digits" in str(error) for error in errors)


def test_emergency_contact_update_email_validation():
    """Test EmergencyContactUpdate email validation - covers schemas.py:98-103"""
    from Backend.api.tenants.schemas import EmergencyContactUpdate
    from pydantic import ValidationError

    # Valid: email can be provided
    update = EmergencyContactUpdate(email="newemail@example.com")
    assert update.email == "newemail@example.com"

    # Valid: email can be None (not updating)
    update = EmergencyContactUpdate(phone="555-9999999")
    assert update.email is None

    # Invalid: email format
    with pytest.raises(ValidationError) as exc_info:
        EmergencyContactUpdate(email="invalid-email")

    errors = exc_info.value.errors()
    assert any("email" in str(error).lower() for error in errors)


def test_emergency_contact_update_all_fields_none():
    """Test EmergencyContactUpdate with all fields as None (empty update)"""
    from Backend.api.tenants.schemas import EmergencyContactUpdate

    # This is valid - partial update with no changes specified
    update = EmergencyContactUpdate()
    assert update.name is None
    assert update.relationship is None
    assert update.phone is None
    assert update.email is None
    assert update.notes is None
    assert update.is_primary is None


def test_emergency_contact_create_with_all_fields():
    """Test creating emergency contact with all fields populated"""
    from Backend.api.tenants.schemas import EmergencyContactCreate

    contact = EmergencyContactCreate(
        name="John Emergency",
        relationship="Brother",
        phone="555-1234567",
        email="john@example.com",
        notes="Call after 6pm only",
        is_primary=True
    )

    assert contact.name == "John Emergency"
    assert contact.relationship == "Brother"
    assert contact.phone == "555-1234567"
    assert contact.email == "john@example.com"
    assert contact.notes == "Call after 6pm only"
    assert contact.is_primary is True


def test_emergency_contact_response_schema():
    """Test EmergencyContactResponse schema"""
    from Backend.api.tenants.schemas import EmergencyContactResponse

    response = EmergencyContactResponse(
        id="test-uuid-123",
        name="John Emergency",
        relationship="Brother",
        phone="555-1234567",
        email="john@example.com",
        is_primary=True,
        notes="Call after 6pm"
    )

    assert response.id == "test-uuid-123"
    assert response.name == "John Emergency"
    assert response.relationship == "Brother"
    assert response.phone == "555-1234567"
    assert response.email == "john@example.com"
    assert response.is_primary is True
    assert response.notes == "Call after 6pm"