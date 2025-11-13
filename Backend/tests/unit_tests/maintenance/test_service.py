"""
Unit tests for maintenance service layer.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import date, datetime
from decimal import Decimal
from fastapi import HTTPException, status

from Backend.api.maintenance.service import MaintenanceService
from Backend.api.maintenance.schemas import (
    MaintenanceRequestCreate,
    MaintenanceRequestUpdate,
    MaintenanceRequestResponse,
    MaintenanceSummaryResponse
)
from Backend.models.enums import MaintenancePriority, MaintenanceStatus, UserType
from Backend.models.maintenance import MaintenanceRequest
from Backend.models.property import Property
from Backend.models.units import PropertyUnit
from Backend.models.tenant import Tenant
from Backend.models.user import User


# =============================================================================
# _validate_and_load_entities TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_validate_and_load_entities_admin_success():
    """Test entity validation for admin user."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    
    # Mock property
    mock_property = MagicMock()
    mock_property.id = 1
    
    # Mock unit
    mock_unit = MagicMock()
    mock_unit.id = 101
    
    # Mock tenant
    mock_tenant = MagicMock()
    mock_tenant.id = 1
    
    # Mock query results
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    unit_result = MagicMock()
    unit_result.scalar_one_or_none.return_value = mock_unit
    
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = mock_tenant
    
    mock_session.execute.side_effect = [property_result, unit_result, tenant_result]
    
    result = await MaintenanceService._validate_and_load_entities(
        property_id=1,
        unit_id=101,
        tenant_id=1,
        current_user=mock_user,
        session=mock_session
    )
    
    property_entity, unit_entity, tenant_entity = result
    assert property_entity == mock_property
    assert unit_entity == mock_unit
    assert tenant_entity == mock_tenant


@pytest.mark.asyncio
async def test_validate_and_load_entities_landlord_success():
    """Test entity validation for landlord user with ownership."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "user123"
    
    # Mock property owned by user
    mock_property = MagicMock()
    mock_property.id = 1
    mock_property.user_id = "user123"
    
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    mock_session.execute.return_value = property_result
    
    result = await MaintenanceService._validate_and_load_entities(
        property_id=1,
        unit_id=None,
        tenant_id=None,
        current_user=mock_user,
        session=mock_session
    )
    
    property_entity, unit_entity, tenant_entity = result
    assert property_entity == mock_property
    assert unit_entity is None
    assert tenant_entity is None


@pytest.mark.asyncio
async def test_validate_and_load_entities_property_not_found():
    """Test entity validation when property doesn't exist."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = property_result
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService._validate_and_load_entities(
            property_id=999,
            unit_id=None,
            tenant_id=None,
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 404
    assert "Property not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_and_load_entities_unauthorized_property():
    """Test entity validation when user doesn't own property."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "user123"
    
    # First query returns None (filtered by ownership)
    # Second query returns property ID (exists but not owned)
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = None
    
    check_result = MagicMock()
    check_result.scalar_one_or_none.return_value = 1  # Property exists
    
    mock_session.execute.side_effect = [property_result, check_result]
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService._validate_and_load_entities(
            property_id=1,
            unit_id=None,
            tenant_id=None,
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 403
    assert "You do not have permission to access this property" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_and_load_entities_unit_not_found():
    """Test entity validation when unit doesn't exist."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    
    # Mock property exists
    mock_property = MagicMock()
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    # Mock unit doesn't exist
    unit_result = MagicMock()
    unit_result.scalar_one_or_none.return_value = None
    
    # Mock unit check returns None (unit doesn't exist at all)
    unit_check_result = MagicMock()
    unit_check_result.scalar_one_or_none.return_value = None
    
    mock_session.execute.side_effect = [property_result, unit_result, unit_check_result]
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService._validate_and_load_entities(
            property_id=1,
            unit_id=999,
            tenant_id=None,
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 404
    assert "Unit not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_and_load_entities_unit_wrong_property():
    """Test entity validation when unit belongs to different property."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    
    # Mock property exists
    mock_property = MagicMock()
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    # Mock unit doesn't exist for this property
    unit_result = MagicMock()
    unit_result.scalar_one_or_none.return_value = None
    
    # Mock unit exists but belongs to different property
    unit_check_result = MagicMock()
    unit_check_result.scalar_one_or_none.return_value = 2  # Different property ID
    
    mock_session.execute.side_effect = [property_result, unit_result, unit_check_result]
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService._validate_and_load_entities(
            property_id=1,
            unit_id=101,
            tenant_id=None,
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 400
    assert "does not belong to the specified property" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_and_load_entities_tenant_not_found():
    """Test entity validation when tenant doesn't exist."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    
    # Mock property exists
    mock_property = MagicMock()
    property_result = MagicMock()
    property_result.scalar_one_or_none.return_value = mock_property
    
    # Mock tenant doesn't exist
    tenant_result = MagicMock()
    tenant_result.scalar_one_or_none.return_value = None
    
    mock_session.execute.side_effect = [property_result, tenant_result]
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService._validate_and_load_entities(
            property_id=1,
            unit_id=None,
            tenant_id=999,
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 404
    assert "Tenant not found" in exc_info.value.detail


# =============================================================================
# list_maintenance_requests TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_list_maintenance_requests_admin():
    """Test listing maintenance requests for admin user."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    mock_user.id = "admin123"
    
    # Mock request
    mock_request = MagicMock()
    mock_request.id = 1
    
    mock_result = MagicMock()
    mock_result.unique.return_value.scalars.return_value.all.return_value = [mock_request]
    mock_session.execute.return_value = mock_result
    
    with patch.object(MaintenanceRequestResponse, 'model_validate') as mock_validate:
        mock_validate.return_value = MagicMock()
        
        result = await MaintenanceService.list_maintenance_requests(
            current_user=mock_user,
            session=mock_session
        )
        
        assert len(result) == 1
        mock_validate.assert_called_once_with(mock_request)


@pytest.mark.asyncio
async def test_list_maintenance_requests_with_filters():
    """Test listing maintenance requests with filters."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    
    mock_result = MagicMock()
    mock_result.unique.return_value.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    with patch.object(MaintenanceRequestResponse, 'model_validate'):
        result = await MaintenanceService.list_maintenance_requests(
            current_user=mock_user,
            session=mock_session,
            req_status=MaintenanceStatus.PENDING,
            priority=MaintenancePriority.HIGH,
            property_id=1,
            unit_id=101,
            tenant_id=1,
            assigned_to="John Doe",
            limit=10,
            offset=5
        )
        
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_list_maintenance_requests_landlord():
    """Test listing maintenance requests for landlord (filtered by ownership)."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "landlord123"
    
    mock_result = MagicMock()
    mock_result.unique.return_value.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    with patch.object(MaintenanceRequestResponse, 'model_validate'):
        result = await MaintenanceService.list_maintenance_requests(
            current_user=mock_user,
            session=mock_session
        )
        
        assert isinstance(result, list)


# =============================================================================
# create_maintenance_request TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_create_maintenance_request_success():
    """Test successful maintenance request creation."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    data = MaintenanceRequestCreate(
        issue_title="Leaking faucet",
        description="Kitchen faucet is dripping",
        property_id=1,
        priority=MaintenancePriority.MEDIUM
    )
    
    # Mock validation
    mock_property = MagicMock()
    mock_property.id = 1
    
    # Mock re-query after commit (new pattern)
    mock_created_request = MagicMock()
    mock_created_request.id = 1
    mock_requery_result = MagicMock()
    mock_requery_result.scalar_one.return_value = mock_created_request
    
    # session.execute will be called twice: once for re-query
    mock_session.execute.return_value = mock_requery_result
    
    with patch.object(MaintenanceService, '_validate_and_load_entities') as mock_validate:
        mock_validate.return_value = (mock_property, None, None)
        
        with patch.object(MaintenanceRequestResponse, 'model_validate') as mock_response:
            mock_response.return_value = MagicMock()
            
            # Mock the vendor notification service to prevent email queries
            with patch('Backend.api.maintenance.vendor_notification_service.VendorNotificationService') as mock_notif:
                result = await MaintenanceService.create_maintenance_request(
                    data=data,
                    current_user=mock_user,
                    session=mock_session
                )
                
                mock_session.add.assert_called_once()
                mock_session.commit.assert_called_once()
                # We now re-query instead of refresh
                mock_session.execute.assert_called_once()
                assert result is not None


@pytest.mark.asyncio
async def test_create_maintenance_request_validation_error():
    """Test maintenance request creation with validation error."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    
    data = MaintenanceRequestCreate(
        issue_title="Test issue",
        property_id=999,
        priority=MaintenancePriority.LOW
    )
    
    with patch.object(MaintenanceService, '_validate_and_load_entities') as mock_validate:
        mock_validate.side_effect = HTTPException(status_code=404, detail="Property not found")
        
        with pytest.raises(HTTPException) as exc_info:
            await MaintenanceService.create_maintenance_request(
                data=data,
                current_user=mock_user,
                session=mock_session
            )
        
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_maintenance_request_database_error():
    """Test maintenance request creation with database error."""
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("Database error")
    mock_user = MagicMock()
    
    data = MaintenanceRequestCreate(
        issue_title="Test issue",
        property_id=1,
        priority=MaintenancePriority.LOW
    )
    
    with patch.object(MaintenanceService, '_validate_and_load_entities') as mock_validate:
        mock_validate.return_value = (MagicMock(), None, None)
        
        with pytest.raises(HTTPException) as exc_info:
            await MaintenanceService.create_maintenance_request(
                data=data,
                current_user=mock_user,
                session=mock_session
            )
        
        assert exc_info.value.status_code == 500
        mock_session.rollback.assert_called_once()


# =============================================================================
# get_maintenance_request TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_maintenance_request_success():
    """Test successful maintenance request retrieval."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    
    mock_request = MagicMock()
    mock_request.id = 1
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_request
    mock_session.execute.return_value = mock_result
    
    with patch('Backend.api.maintenance.service.check_permission') as mock_check:
        with patch.object(MaintenanceRequestResponse, 'model_validate') as mock_validate:
            mock_validate.return_value = MagicMock()
            
            result = await MaintenanceService.get_maintenance_request(
                request_id=1,
                current_user=mock_user,
                session=mock_session
            )
            
            mock_check.assert_called_once_with(mock_request, mock_user, mock_session)
            assert result is not None


@pytest.mark.asyncio
async def test_get_maintenance_request_not_found():
    """Test maintenance request retrieval when request doesn't exist."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.get_maintenance_request(
            request_id=999,
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 404
    assert "Maintenance request not found" in exc_info.value.detail


# =============================================================================
# update_maintenance_request TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_update_maintenance_request_success():
    """Test successful maintenance request update."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.property_id = 1
    mock_request.unit_id = None
    mock_request.tenant_id = None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_request
    mock_session.execute.return_value = mock_result
    
    update_data = MaintenanceRequestUpdate(
        status=MaintenanceStatus.COMPLETED,
        actual_cost=Decimal("175.00")
    )
    
    with patch('Backend.api.maintenance.service.check_permission'):
        with patch.object(MaintenanceRequestResponse, 'model_validate') as mock_validate:
            mock_validate.return_value = MagicMock()
            
            result = await MaintenanceService.update_maintenance_request(
                request_id=1,
                data=update_data,
                current_user=mock_user,
                session=mock_session
            )
            
            mock_session.add.assert_called_once_with(mock_request)
            mock_session.commit.assert_called_once()
            assert result is not None


@pytest.mark.asyncio
async def test_update_maintenance_request_with_property_change():
    """Test maintenance request update with property change."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    
    mock_request = MagicMock()
    mock_request.id = 1
    mock_request.property_id = 1
    mock_request.unit_id = None
    mock_request.tenant_id = None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_request
    mock_session.execute.return_value = mock_result
    
    update_data = MaintenanceRequestUpdate(property_id=2)
    
    with patch('Backend.api.maintenance.service.check_permission'):
        with patch.object(MaintenanceService, '_validate_and_load_entities') as mock_validate:
            mock_validate.return_value = (MagicMock(), None, None)
            
            with patch.object(MaintenanceRequestResponse, 'model_validate') as mock_response:
                mock_response.return_value = MagicMock()
                
                result = await MaintenanceService.update_maintenance_request(
                    request_id=1,
                    data=update_data,
                    current_user=mock_user,
                    session=mock_session
                )
                
                mock_validate.assert_called_once()
                assert result is not None


# =============================================================================
# delete_maintenance_request TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_delete_maintenance_request_success():
    """Test successful maintenance request deletion."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    mock_request = MagicMock()
    mock_request.id = 1
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_request
    mock_session.execute.return_value = mock_result
    
    with patch('Backend.api.maintenance.service.check_permission'):
        await MaintenanceService.delete_maintenance_request(
            request_id=1,
            current_user=mock_user,
            session=mock_session
        )
        
        mock_session.delete.assert_called_once_with(mock_request)
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_maintenance_request_not_found():
    """Test maintenance request deletion when request doesn't exist."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.delete_maintenance_request(
            request_id=999,
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == 404


# =============================================================================
# get_maintenance_summary TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_get_maintenance_summary_admin():
    """Test maintenance summary for admin user."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    mock_user.id = "admin123"
    
    # Mock query results
    mock_results = [
        (MaintenanceStatus.PENDING, 5),
        (MaintenanceStatus.IN_PROGRESS, 3),
        (MaintenanceStatus.COMPLETED, 10)
    ]
    mock_session.execute.return_value = mock_results
    
    result = await MaintenanceService.get_maintenance_summary(
        current_user=mock_user,
        session=mock_session
    )
    
    assert isinstance(result, MaintenanceSummaryResponse)
    assert result.total_requests == 18
    assert result.pending == 5
    assert result.in_progress == 3
    assert result.completed == 10


@pytest.mark.asyncio
async def test_get_maintenance_summary_landlord():
    """Test maintenance summary for landlord user (filtered by ownership)."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = False
    mock_user.id = "landlord123"
    
    mock_results = [
        (MaintenanceStatus.PENDING, 2),
        (MaintenanceStatus.COMPLETED, 5)
    ]
    mock_session.execute.return_value = mock_results
    
    result = await MaintenanceService.get_maintenance_summary(
        current_user=mock_user,
        session=mock_session
    )
    
    assert result.total_requests == 7
    assert result.pending == 2
    assert result.completed == 5
    assert result.in_progress == 0  # Default value


@pytest.mark.asyncio
async def test_get_maintenance_summary_empty():
    """Test maintenance summary with no requests."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.is_admin = True
    
    mock_session.execute.return_value = []
    
    result = await MaintenanceService.get_maintenance_summary(
        current_user=mock_user,
        session=mock_session
    )
    
    assert result.total_requests == 0
    assert result.pending == 0
    assert result.in_progress == 0
    assert result.completed == 0


# =============================================================================
# upload_maintenance_photo TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_upload_maintenance_photo_success():
    """Test successful maintenance photo upload."""
    mock_file = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.LANDLORD
    mock_user.id = "user123"
    
    with patch('Backend.api.maintenance.service.validate_file_content') as mock_validate_content:
        with patch('Backend.api.maintenance.service.validate_file_size') as mock_validate_size:
            with patch('Backend.api.maintenance.service.upload_maintenance_photo_to_blob') as mock_upload:
                mock_validate_content.return_value = True
                mock_upload.return_value = "https://storage.example.com/photo.jpg"
                
                result = await MaintenanceService.upload_maintenance_photo(
                    upload_file=mock_file,
                    current_user=mock_user
                )
                
                assert result["photo_url"] == "https://storage.example.com/photo.jpg"
                mock_validate_content.assert_called_once_with(mock_file)
                mock_validate_size.assert_called_once_with(mock_file, 10 * 1024 * 1024)


@pytest.mark.asyncio
async def test_upload_maintenance_photo_unauthorized():
    """Test maintenance photo upload with unauthorized user."""
    mock_file = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.TENANT  # Not authorized
    
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.upload_maintenance_photo(
            upload_file=mock_file,
            current_user=mock_user
        )
    
    assert exc_info.value.status_code == 403
    assert "Not authorized" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_maintenance_photo_invalid_file():
    """Test maintenance photo upload with invalid file type."""
    mock_file = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.ADMIN
    
    with patch('Backend.api.maintenance.service.validate_file_content') as mock_validate:
        mock_validate.return_value = False  # Invalid file type
        
        with pytest.raises(HTTPException) as exc_info:
            await MaintenanceService.upload_maintenance_photo(
                upload_file=mock_file,
                current_user=mock_user
            )
        
        assert exc_info.value.status_code == 400
        assert "Unsupported file type" in exc_info.value.detail


@pytest.mark.asyncio
async def test_upload_maintenance_photo_upload_error():
    """Test maintenance photo upload with blob storage error."""
    mock_file = AsyncMock()
    mock_user = MagicMock()
    mock_user.user_type = UserType.LANDLORD
    
    with patch('Backend.api.maintenance.service.validate_file_content') as mock_validate_content:
        with patch('Backend.api.maintenance.service.validate_file_size') as mock_validate_size:
            with patch('Backend.api.maintenance.service.upload_maintenance_photo_to_blob') as mock_upload:
                mock_validate_content.return_value = True
                mock_upload.side_effect = Exception("Blob storage error")
                
                with pytest.raises(HTTPException) as exc_info:
                    await MaintenanceService.upload_maintenance_photo(
                        upload_file=mock_file,
                        current_user=mock_user
                    )
                
                assert exc_info.value.status_code == 500
                assert "Failed to upload maintenance photo" in exc_info.value.detail


# =============================================================================
# bulk_delete_maintenance_requests TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_bulk_delete_maintenance_requests_success_admin():
    """Test successful bulk deletion of maintenance requests by admin."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "admin123"
    mock_user.is_admin = True
    
    # Mock requests to delete
    mock_request1 = MagicMock(spec=MaintenanceRequest)
    mock_request1.id = 1
    
    mock_request2 = MagicMock(spec=MaintenanceRequest)
    mock_request2.id = 2
    
    # Mock query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_request1, mock_request2]
    mock_session.execute.return_value = mock_result
    
    # Act
    await MaintenanceService.bulk_delete_maintenance_requests(
        request_ids=[1, 2],
        current_user=mock_user,
        session=mock_session
    )
    
    # Assert
    # Verify bulk delete was executed via SQL delete statement
    assert mock_session.execute.call_count >= 2  # At least: query to fetch requests, bulk delete statement
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()
    # Should NOT use individual session.delete() calls
    mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_bulk_delete_maintenance_requests_success_landlord():
    """Test successful bulk deletion of maintenance requests by landlord."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "landlord123"
    mock_user.is_admin = False
    
    # Mock requests owned by landlord
    mock_request1 = MagicMock(spec=MaintenanceRequest)
    mock_request1.id = 1
    
    mock_request2 = MagicMock(spec=MaintenanceRequest)
    mock_request2.id = 2
    
    # Mock query result (with join for ownership validation)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_request1, mock_request2]
    mock_session.execute.return_value = mock_result
    
    # Act
    await MaintenanceService.bulk_delete_maintenance_requests(
        request_ids=[1, 2],
        current_user=mock_user,
        session=mock_session
    )
    
    # Assert
    # Verify bulk delete was executed via SQL delete statement
    assert mock_session.execute.call_count >= 2  # At least: query to fetch requests, bulk delete statement
    mock_session.commit.assert_called_once()
    # Should NOT use individual session.delete() calls
    mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_bulk_delete_maintenance_requests_empty_list():
    """Test bulk deletion with empty list - should return early."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "user123"
    
    # Act
    await MaintenanceService.bulk_delete_maintenance_requests(
        request_ids=[],
        current_user=mock_user,
        session=mock_session
    )
    
    # Assert - Should return early without executing queries
    mock_session.execute.assert_not_called()
    mock_session.delete.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_bulk_delete_maintenance_requests_not_found():
    """Test bulk deletion when some requests are not found or unauthorized."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "landlord123"
    mock_user.is_admin = False
    
    # Mock only one request found (missing one)
    mock_request1 = MagicMock(spec=MaintenanceRequest)
    mock_request1.id = 1
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_request1]
    mock_session.execute.return_value = mock_result
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.bulk_delete_maintenance_requests(
            request_ids=[1, 2],
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "One or more maintenance requests not found" in exc_info.value.detail
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_delete_maintenance_requests_single_request():
    """Test bulk deletion with single request."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "admin123"
    mock_user.is_admin = True
    
    # Mock single request
    mock_request = MagicMock(spec=MaintenanceRequest)
    mock_request.id = 1
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_request]
    mock_session.execute.return_value = mock_result
    
    # Act
    await MaintenanceService.bulk_delete_maintenance_requests(
        request_ids=[1],
        current_user=mock_user,
        session=mock_session
    )
    
    # Assert
    # Verify bulk delete was executed via SQL delete statement (even for single request)
    assert mock_session.execute.call_count >= 2  # At least: query to fetch requests, bulk delete statement
    mock_session.commit.assert_called_once()
    # Should NOT use individual session.delete() calls
    mock_session.delete.assert_not_called()


@pytest.mark.asyncio
async def test_bulk_delete_maintenance_requests_general_exception():
    """Test bulk deletion handles general exceptions."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "admin123"
    mock_user.is_admin = True
    
    # Mock request
    mock_request = MagicMock(spec=MaintenanceRequest)
    mock_request.id = 1
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_request]
    mock_session.execute.return_value = mock_result
    
    # Mock commit to raise exception
    mock_session.commit.side_effect = Exception("Database connection lost")
    
    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.bulk_delete_maintenance_requests(
            request_ids=[1],
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "An unexpected error occurred during bulk deletion" in exc_info.value.detail
    mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_bulk_delete_maintenance_requests_duplicate_ids():
    """Test bulk deletion with duplicate IDs - should handle correctly."""
    mock_session = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = "admin123"
    mock_user.is_admin = True
    
    # Mock request (duplicate IDs in list)
    mock_request = MagicMock(spec=MaintenanceRequest)
    mock_request.id = 1
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_request]
    mock_session.execute.return_value = mock_result
    
    # Act & Assert - Should fail because we have duplicate IDs but only one found
    with pytest.raises(HTTPException) as exc_info:
        await MaintenanceService.bulk_delete_maintenance_requests(
            request_ids=[1, 1, 2],  # Duplicate 1, missing 2
            current_user=mock_user,
            session=mock_session
        )
    
    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    mock_session.rollback.assert_called_once()