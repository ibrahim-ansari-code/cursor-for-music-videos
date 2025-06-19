from datetime import datetime
import pytest
from fastapi import status, HTTPException, Response
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi import BackgroundTasks

from Backend.api.tenants.router import get_tenant, get_tenants, create_tenant, update_tenant, delete_tenant
from Backend.models.user import User
from Backend.models.enums import UserType
from Backend.api.tenants.schemas import TenantResponse, TenantCreate, TenantUpdate
from Backend.models.tenant import TenantStatus, Tenant


# =============================================================================
# GET TESTS - get_tenant and get_tenants
# =============================================================================

@pytest.mark.asyncio
async def test_get_tenant_success(mocker):
    # Arrange
    tenant_id = 123
    user_id = uuid4()
    mock_user = User(
        id=user_id, 
        email="test@example.com", 
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    
    # Create a proper mock tenant with landlord_id matching the user
    mock_tenant_orm = Tenant(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone=None,
        status=TenantStatus.ACTIVE,
        landlord_id=user_id,  # This is crucial - must match current_user.id
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    mock_tenant_response = TenantResponse(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        phone=None,
        email="john.doe@example.com",
        status=TenantStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        current_property_id=None,
        unit=None,
        property=None,
    )

    # Mock the service functions
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant_orm),
    )
    mocker.patch(
        "Backend.api.tenants.router.enrich_tenants_with_details",
        new=AsyncMock(return_value=[mock_tenant_response]),
    )

    # Act
    result = await get_tenant(
        tenant_id=tenant_id,
        current_user=mock_user,
        session=mock_session,
    )

    # Assert
    assert isinstance(result, TenantResponse)
    assert result.id == tenant_id
    assert result.first_name == "John"
    assert result.last_name == "Doe"
    assert result.email == "john.doe@example.com"


@pytest.mark.asyncio
async def test_get_tenant_by_id_success(mocker):
    # Arrange
    tenant_id = 202
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord2@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()

    # Mock tenant ORM and response
    mock_tenant_orm = Tenant(
        id=tenant_id,
        first_name="Sam",
        last_name="Smith",
        email="sam.smith@example.com",
        phone="555-2222",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mock_tenant_response = TenantResponse(
        id=tenant_id,
        first_name="Sam",
        last_name="Smith",
        phone="555-2222",
        email="sam.smith@example.com",
        status=TenantStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        current_property_id=10,
        unit=None,
        property=None,
    )

    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant_orm)
    )
    mocker.patch(
        "Backend.api.tenants.router.enrich_tenants_with_details",
        new=AsyncMock(return_value=[mock_tenant_response])
    )

    # Act
    result = await get_tenant(
        tenant_id=tenant_id,
        current_user=mock_user,
        session=mock_session
    )

    # Assert
    assert isinstance(result, TenantResponse)
    assert result.id == tenant_id
    assert result.first_name == "Sam"
    assert result.last_name == "Smith"
    assert result.email == "sam.smith@example.com"
    assert result.current_property_id == 10


@pytest.mark.asyncio
async def test_get_tenants_landlord_scope(mocker):
    # Arrange
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()

    # Mock ORM tenants (only those assigned to landlord's properties)
    tenant1 = Tenant(
        id=1,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="1234567890",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    tenant2 = Tenant(
        id=2,
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        phone="0987654321",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=20,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    tenants_orm = [tenant1, tenant2]

    # Mock the query builder to return a query object
    mock_query = MagicMock()
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query

    # Patch build_filtered_tenants_query to return our mock_query
    mocker.patch(
        "Backend.api.tenants.router.build_filtered_tenants_query",
        return_value=mock_query
    )
    # Patch build_unassigned_tenants_query to ensure it's not called
    mocker.patch(
        "Backend.api.tenants.router.build_unassigned_tenants_query"
    )

    # Patch session.execute to return an object with scalars().all()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = tenants_orm
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Patch enrich_tenants_with_details to return TenantResponse objects
    tenant_response1 = TenantResponse(
        id=1,
        first_name="John",
        last_name="Doe",
        phone="1234567890",
        email="john.doe@example.com",
        status=TenantStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        current_property_id=10,
        unit=None,
        property=None,
    )
    tenant_response2 = TenantResponse(
        id=2,
        first_name="Jane",
        last_name="Smith",
        phone="0987654321",
        email="jane.smith@example.com",
        status=TenantStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        current_property_id=20,
        unit=None,
        property=None,
    )
    mocker.patch(
        "Backend.api.tenants.router.enrich_tenants_with_details",
        new=AsyncMock(return_value=[tenant_response1, tenant_response2])
    )

    # Act
    result = await get_tenants(
        status_filter=None,
        search=None,
        property_id=None,
        unassigned_only=False,
        skip=0,
        limit=100,
        current_user=mock_user,
        session=mock_session
    )

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(t, TenantResponse) for t in result)
    assert {t.id for t in result} == {1, 2}
    assert all(t.status == TenantStatus.ACTIVE for t in result)
    assert all(t.current_property_id in [10, 20] for t in result)


@pytest.mark.asyncio
async def test_get_tenant_not_found(mocker):
    # Arrange
    tenant_id = 999
    mock_user = User(id=uuid4(), email="test@example.com", user_type=UserType.LANDLORD.value)
    mock_session = AsyncMock()

    # Mock check_tenant_permission to raise 404 (tenant not found)
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Tenant not found"
        )),
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await get_tenant(
            tenant_id=tenant_id,
            current_user=mock_user,
            session=mock_session,
        )
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "Tenant not found" in str(exc_info.value.detail)


# =============================================================================
# CREATE TESTS - create_tenant
# =============================================================================


@pytest.mark.asyncio
async def test_create_tenant_success(mocker):
    # Arrange
    mock_user = User(id=uuid4(), email="landlord@example.com", user_type=UserType.LANDLORD.value)
    mock_session = AsyncMock()
    mock_background_tasks = BackgroundTasks()
    tenant_data = TenantCreate(
        first_name="Alice",
        last_name="Smith",
        email="alice.smith@example.com",
        phone="1234567890",
        status=TenantStatus.ACTIVE,
        current_property_id=None,
        user_id=None,
        full_name=None,
    )
    mock_tenant = AsyncMock()
    mock_tenant.id = 1
    mock_tenant.first_name = "Alice"
    mock_tenant.last_name = "Smith"
    mock_tenant.email = "alice.smith@example.com"
    mock_tenant.phone = "1234567890"
    mock_tenant.status = TenantStatus.ACTIVE
    mock_tenant.created_at = "2023-01-01T00:00:00Z"
    mock_tenant.updated_at = "2023-01-01T00:00:00Z"
    mock_tenant.current_property_id = None

    # Mock all the service functions that create_tenant calls
    mocker.patch("Backend.api.tenants.router._validate_user_permissions", new=AsyncMock())
    mocker.patch("Backend.api.tenants.router._determine_landlord", new=AsyncMock(return_value=mock_user.id))
    mocker.patch("Backend.api.tenants.router._validate_property_assignment", new=AsyncMock())
    mocker.patch("Backend.api.tenants.router._validate_linked_user_account", new=AsyncMock())
    mocker.patch("Backend.api.tenants.router.create_and_save_tenant", new=AsyncMock(return_value=mock_tenant))
    mocker.patch.object(mock_session, "commit", new=AsyncMock())
    mocker.patch.object(mock_session, "rollback", new=AsyncMock())
    mocker.patch("Backend.api.tenants.schemas.TenantResponse.model_validate", return_value=TenantResponse(
        id=1,
        first_name="Alice",
        last_name="Smith",
        phone="1234567890",
        email="alice.smith@example.com",
        status=TenantStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        current_property_id=None,
        unit=None,
        property=None,
    ))

    # Act
    result = await create_tenant(
        tenant_data=tenant_data,
        background_tasks=mock_background_tasks,
        current_user=mock_user,
        session=mock_session,
    )

    # Assert
    assert isinstance(result, TenantResponse)
    assert result.first_name == "Alice"
    assert result.last_name == "Smith"
    assert result.email == "alice.smith@example.com"
    assert result.status == TenantStatus.ACTIVE


@pytest.mark.asyncio
async def test_create_tenant_duplicate_email(mocker):
    # Arrange
    mock_user = User(id=uuid4(), email="landlord@example.com", user_type=UserType.LANDLORD.value)
    mock_session = AsyncMock()
    mock_background_tasks = BackgroundTasks()
    tenant_data = TenantCreate(
        first_name="Bob",
        last_name="Smith",
        email="bob.smith@example.com",
        phone="555-123-4567",
        status=TenantStatus.ACTIVE,
        current_property_id=None,
        user_id=None,
        full_name=None,
    )

    mocker.patch("Backend.api.tenants.router._validate_user_permissions", new=AsyncMock())
    mocker.patch("Backend.api.tenants.router._determine_landlord", new=AsyncMock(return_value=mock_user.id))
    mocker.patch("Backend.api.tenants.router._validate_property_assignment", new=AsyncMock())
    mocker.patch("Backend.api.tenants.router._validate_linked_user_account", new=AsyncMock())
    # Simulate create_and_save_tenant raising HTTPException for duplicate email
    mocker.patch(
        "Backend.api.tenants.router.create_and_save_tenant",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this email address already exists.",
        ))
    )
    mocker.patch.object(mock_session, "commit", new=AsyncMock())
    mocker.patch.object(mock_session, "rollback", new=AsyncMock())

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await create_tenant(
            tenant_data=tenant_data,
            background_tasks=mock_background_tasks,
            current_user=mock_user,
            session=mock_session,
        )
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in str(exc_info.value.detail)


# =============================================================================
# UPDATE TESTS - update_tenant
# =============================================================================


@pytest.mark.asyncio
async def test_update_tenant_success(mocker):
    # Arrange
    tenant_id = 42
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    new_property_id = 100

    # Existing tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="OldFirst",
        last_name="OldLast",
        email="old@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=50,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    # Patch check_tenant_permission to return the mock tenant
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )

    # Patch session.scalar to simulate property ownership check (property exists and is owned by landlord)
    mock_session.scalar = AsyncMock(return_value=True)

    # Patch session.commit and session.refresh
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Patch create_audit_datetime to return a fixed datetime
    mock_update_time = datetime(2024, 1, 1, 12, 0, 0)
    mocker.patch("Backend.api.tenants.router.create_audit_datetime", return_value=mock_update_time)

    # Patch TenantResponse.model_validate to return a valid response
    mock_response = TenantResponse(
        id=tenant_id,
        first_name="NewFirst",
        last_name="NewLast",
        phone="555-123-4567",
        email="new@example.com",
        status=TenantStatus.ACTIVE,
        created_at=mock_tenant.created_at,
        updated_at=mock_update_time,
        current_property_id=new_property_id,
        unit=None,
        property=None,
    )
    mocker.patch(
        "Backend.api.tenants.schemas.TenantResponse.model_validate",
        return_value=mock_response
    )

    # Prepare update data
    tenant_update = TenantUpdate(
        first_name="NewFirst",
        last_name="NewLast",
        phone="555-123-4567",
        email="new@example.com",
        current_property_id=new_property_id
    )

    # Act
    result = await update_tenant(
        tenant_id=tenant_id,
        tenant_data=tenant_update,
        current_user=mock_user,
        session=mock_session
    )

    # Assert
    assert isinstance(result, TenantResponse)
    assert result.id == tenant_id
    assert result.first_name == "NewFirst"
    assert result.last_name == "NewLast"
    assert result.phone == "555-123-4567"
    assert result.email == "new@example.com"
    assert result.current_property_id == new_property_id
    assert result.updated_at == mock_update_time


@pytest.mark.asyncio
async def test_partial_update_tenant(mocker):
    # Arrange
    tenant_id = 2
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    # Existing tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="OldFirst",
        last_name="OldLast",
        email="old@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    # Patch check_tenant_permission to return the mock tenant
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    # Patch session methods
    mock_session.add = MagicMock()  # session.add() is synchronous, not async
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    # Patch create_audit_datetime to return a fixed datetime
    mock_update_time = datetime(2024, 6, 2, 15, 0, 0)
    mocker.patch(
        "Backend.api.tenants.router.create_audit_datetime",
        return_value=mock_update_time
    )
    # Patch TenantResponse.model_validate to return a valid response
    mock_response = TenantResponse(
        id=tenant_id,
        first_name="OldFirst",
        last_name="NewLast",
        phone="555-000-0000",
        email="old@example.com",
        status=TenantStatus.ACTIVE,
        created_at=mock_tenant.created_at,
        updated_at=mock_update_time,
        current_property_id=10,
        unit=None,
        property=None,
    )
    mocker.patch(
        "Backend.api.tenants.schemas.TenantResponse.model_validate",
        return_value=mock_response
    )
    # Prepare update data (only last_name is updated)
    tenant_update = TenantUpdate(
        last_name="NewLast"
    )
    # Act
    result = await update_tenant(
        tenant_id=tenant_id,
        tenant_data=tenant_update,
        current_user=mock_user,
        session=mock_session
    )
    # Assert
    assert isinstance(result, TenantResponse)
    assert result.id == tenant_id
    assert result.first_name == "OldFirst"
    assert result.last_name == "NewLast"
    assert result.phone == "555-000-0000"
    assert result.email == "old@example.com"
    assert result.updated_at == mock_update_time
    mock_session.add.assert_called_once_with(mock_tenant)  # session.add() is synchronous
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(mock_tenant)


@pytest.mark.asyncio
async def test_non_privileged_user_update_forbidden(mocker):
    # Arrange
    tenant_id = 77
    mock_user = User(
        id=uuid4(),
        email="unauthorized@example.com",
        user_type=UserType.TENANT.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    tenant_update = TenantUpdate(
        first_name="Should",
        last_name="Fail",
        email="should.fail@example.com"
    )

    # Patch check_tenant_permission to raise 403 Forbidden
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(side_effect=HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this tenant"
        ))
    )

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_tenant(
            tenant_id=tenant_id,
            tenant_data=tenant_update,
            current_user=mock_user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Not authorized" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_landlord_updates_tenant_info_without_property_change(mocker):
    # Arrange
    tenant_id = 123
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    # Existing tenant ORM object (property assignment unchanged)
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="OldFirst",
        last_name="OldLast",
        email="old@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    # Patch check_tenant_permission to return the mock tenant
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    # Patch session methods
    mock_session.add = MagicMock()  # session.add() is synchronous, not async
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    # Patch create_audit_datetime to return a fixed datetime
    mock_update_time = datetime(2024, 6, 1, 10, 0, 0)
    mocker.patch(
        "Backend.api.tenants.router.create_audit_datetime",
        return_value=mock_update_time
    )
    # Patch TenantResponse.model_validate to return a valid response
    mock_response = TenantResponse(
        id=tenant_id,
        first_name="NewFirst",
        last_name="NewLast",
        phone="555-123-4567",
        email="new@example.com",
        status=TenantStatus.ACTIVE,
        created_at=mock_tenant.created_at,
        updated_at=mock_update_time,
        current_property_id=10,
        unit=None,
        property=None,
    )
    mocker.patch(
        "Backend.api.tenants.schemas.TenantResponse.model_validate",
        return_value=mock_response
    )
    # Prepare update data (no property change)
    tenant_update = TenantUpdate(
        first_name="NewFirst",
        last_name="NewLast",
        phone="555-123-4567",
        email="new@example.com",
        current_property_id=10
    )
    # Act
    result = await update_tenant(
        tenant_id=tenant_id,
        tenant_data=tenant_update,
        current_user=mock_user,
        session=mock_session
    )
    # Assert
    assert isinstance(result, TenantResponse)
    assert result.id == tenant_id
    assert result.first_name == "NewFirst"
    assert result.last_name == "NewLast"
    assert result.phone == "555-123-4567"
    assert result.email == "new@example.com"
    assert result.current_property_id == 10
    assert result.updated_at == mock_update_time
    mock_session.add.assert_called_once_with(mock_tenant)  # session.add() is synchronous
    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(mock_tenant)


@pytest.mark.asyncio
async def test_landlord_assigns_unowned_property_forbidden(mocker):
    # Arrange
    tenant_id = 1
    landlord_id = uuid4()
    unowned_property_id = 999
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    # Existing tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=10,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    # Patch check_tenant_permission to return the mock tenant
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    # Patch session.scalar to simulate property does not exist or is not owned by landlord
    mock_session.scalar = AsyncMock(return_value=False)
    # Prepare update data with a property the landlord does not own
    tenant_update = TenantUpdate(
        current_property_id=unowned_property_id
    )
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await update_tenant(
            tenant_id=tenant_id,
            tenant_data=tenant_update,
            current_user=mock_user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "do not own" in str(exc_info.value.detail)


# =============================================================================
# DELETE TESTS - delete_tenant
# =============================================================================


@pytest.mark.asyncio
async def test_delete_tenant_success(mocker):
    # Arrange
    tenant_id = 101
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()

    # Mock check_tenant_permission to return a tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="555-111-1111",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )

    # Mock session.scalar to simulate no active leases
    mock_session.scalar = AsyncMock(return_value=None)
    # Mock session.delete and session.commit
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    # Act
    response = await delete_tenant(
        tenant_id=tenant_id,
        current_user=mock_user,
        session=mock_session
    )

    # Assert
    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_session.delete.assert_awaited_once_with(mock_tenant)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_tenant_with_active_leases(mocker):
    # Arrange
    tenant_id = 555
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()

    # Mock check_tenant_permission to return a tenant ORM object
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Active",
        last_name="Lease",
        email="active.lease@example.com",
        phone="555-999-9999",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )

    # Mock session.scalar to simulate active lease exists
    mock_session.scalar = AsyncMock(return_value=True)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await delete_tenant(
            tenant_id=tenant_id,
            current_user=mock_user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "active leases" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_commit_called_on_successful_deletion(mocker):
    tenant_id = 123
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()

    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test.tenant@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    response = await delete_tenant(
        tenant_id=tenant_id,
        current_user=mock_user,
        session=mock_session
    )

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_landlord_can_delete_own_tenant_without_active_leases(mocker):
    tenant_id = 10
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Test",
        last_name="Tenant",
        email="test.tenant@example.com",
        phone="555-000-0000",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.delete = AsyncMock()
    mock_session.commit = AsyncMock()

    response = await delete_tenant(
        tenant_id=tenant_id,
        current_user=mock_user,
        session=mock_session
    )

    assert isinstance(response, Response)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    mock_session.delete.assert_awaited_once_with(mock_tenant)
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_error_returns_500_on_deletion(mocker):
    tenant_id = 20
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Error",
        last_name="Tenant",
        email="error.tenant@example.com",
        phone="555-1111",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.delete = AsyncMock(side_effect=Exception("DB error"))
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    with pytest.raises(HTTPException) as exc_info:
        await delete_tenant(
            tenant_id=tenant_id,
            current_user=mock_user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Failed to delete tenant" in str(exc_info.value.detail)
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_rollback_on_deletion_exception(mocker):
    tenant_id = 30
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Rollback",
        last_name="Tenant",
        email="rollback.tenant@example.com",
        phone="555-2222",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    mock_session.scalar = AsyncMock(return_value=None)
    mock_session.delete = AsyncMock(side_effect=Exception("Simulated error"))
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    with pytest.raises(HTTPException):
        await delete_tenant(
            tenant_id=tenant_id,
            current_user=mock_user,
            session=mock_session
        )
    mock_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_tenant_with_active_leases_returns_400(mocker):
    tenant_id = 40
    landlord_id = uuid4()
    mock_user = User(
        id=landlord_id,
        email="landlord@example.com",
        user_type=UserType.LANDLORD.value,
        is_admin=False
    )
    mock_session = AsyncMock()
    mock_tenant = Tenant(
        id=tenant_id,
        first_name="Active",
        last_name="Lease",
        email="active.lease@example.com",
        phone="555-3333",
        status=TenantStatus.ACTIVE,
        landlord_id=landlord_id,
        current_property_id=None,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    mocker.patch(
        "Backend.api.tenants.router.check_tenant_permission",
        new=AsyncMock(return_value=mock_tenant)
    )
    mock_session.scalar = AsyncMock(return_value=True)

    with pytest.raises(HTTPException) as exc_info:
        await delete_tenant(
            tenant_id=tenant_id,
            current_user=mock_user,
            session=mock_session
        )
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "active leases" in str(exc_info.value.detail)
