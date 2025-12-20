"""
Maintenance Request Notification Orchestrator

Centralized notification logic for all maintenance request events.
Follows industry-standard pattern used by Stripe, Shopify, GitHub.

Single source of truth for:
- When to send notifications
- What notifications to send
- How to handle failures

Benefits:
- Consistent behavior across create/update/delete
- Easy to extend with new notification types
- Clear audit trail
- Testable in isolation
"""
import logging
from typing import Dict, Tuple, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.models.maintenance import MaintenanceRequest
from Backend.models.enums import MaintenanceStatus
from Backend.api.maintenance.vendor_notification_service import VendorNotificationService

logger = logging.getLogger(__name__)


async def send_maintenance_notifications(
    request: MaintenanceRequest,
    changes: Dict[str, Tuple[Any, Any]],
    session: AsyncSession
) -> None:
    """
    Central orchestrator for ALL maintenance request notifications.
    Determines what notifications to send based on what changed.
    
    Args:
        request: The maintenance request (with updated values)
        changes: Dictionary mapping field names to (old_value, new_value) tuples
                 Example: {'vendor_id': (None, 123), 'status': ('New', 'Pending')}
        session: Database session for loading relationships
        
    Examples:
        # Vendor was just assigned
        await send_maintenance_notifications(
            request,
            changes={'vendor_id': (None, 123)},
            session=session
        )
        
        # Status changed
        await send_maintenance_notifications(
            request,
            changes={'status': (MaintenanceStatus.NEW, MaintenanceStatus.PENDING)},
            session=session
        )
        
        # Multiple changes
        await send_maintenance_notifications(
            request,
            changes={
                'vendor_id': (None, 123),
                'status': (MaintenanceStatus.NEW, MaintenanceStatus.IN_PROGRESS)
            },
            session=session
        )
    """
    notifications_sent = []
    
    # ========================================
    # 1. VENDOR ASSIGNMENT NOTIFICATION
    # ========================================
    if 'vendor_id' in changes:
        old_vendor_id, new_vendor_id = changes['vendor_id']
        
        # Vendor was newly assigned (wasn't set before, now is set)
        if new_vendor_id and new_vendor_id != old_vendor_id:
            try:
                # Send email to vendor with request details
                vendor_success = await VendorNotificationService.notify_vendor_of_assignment(
                    request,
                    session
                )
                
                # Send confirmation to landlord
                landlord_success = await VendorNotificationService.notify_landlord_of_assignment(
                    request,
                    session
                )
                
                if vendor_success and landlord_success:
                    notifications_sent.append('vendor_assignment')
                    logger.info(
                        f"Vendor assignment notifications sent for request {request.id}",
                        extra={
                            'request_id': request.id,
                            'vendor_id': new_vendor_id,
                            'notification_type': 'vendor_assignment'
                        }
                    )
                else:
                    logger.warning(
                        f"Partial failure sending vendor assignment notifications for request {request.id}",
                        extra={
                            'request_id': request.id,
                            'vendor_success': vendor_success,
                            'landlord_success': landlord_success
                        }
                    )
                    
            except Exception as e:
                logger.exception(
                    f"Failed to send vendor assignment notifications for request {request.id}",
                    extra={
                        'request_id': request.id,
                        'vendor_id': new_vendor_id,
                        'error': str(e)
                    }
                )
                # Don't re-raise - notification failures shouldn't block the operation
    
    # ========================================
    # 2. TENANT STATUS UPDATE NOTIFICATION
    # ========================================
    if 'status' in changes and request.notify_tenant:
        old_status, new_status = changes['status']
        
        # Status actually changed (not just a no-op update)
        if old_status != new_status:
            try:
                success = await VendorNotificationService.notify_tenant_of_status_change(
                    request,
                    old_status,
                    new_status,
                    session
                )
                
                if success:
                    notifications_sent.append('tenant_status_update')
                    logger.info(
                        f"Tenant status update notification sent for request {request.id}: {old_status} → {new_status}",
                        extra={
                            'request_id': request.id,
                            'old_status': old_status.value if isinstance(old_status, MaintenanceStatus) else old_status,
                            'new_status': new_status.value if isinstance(new_status, MaintenanceStatus) else new_status,
                            'notification_type': 'tenant_status_update'
                        }
                    )
                    
            except Exception as e:
                logger.exception(
                    f"Failed to send tenant status update notification for request {request.id}",
                    extra={
                        'request_id': request.id,
                        'old_status': old_status,
                        'new_status': new_status,
                        'error': str(e)
                    }
                )
                # Don't re-raise - notification failures shouldn't block the operation
    
    # ========================================
    # 3. FUTURE: Additional notification triggers can be added here
    # ========================================
    # Examples:
    # - Priority escalated to HIGH → notify landlord immediately
    # - Scheduled date approaching → reminder to vendor
    # - Request overdue → escalation notification
    # - Photos added → notify vendor of new information
    # - Completion date set → notify tenant
    
    # ========================================
    # AUDIT LOG
    # ========================================
    if notifications_sent:
        logger.info(
            f"Maintenance notification orchestrator completed for request {request.id}",
            extra={
                'request_id': request.id,
                'notifications_sent': notifications_sent,
                'changes': {k: f"{v[0]} → {v[1]}" for k, v in changes.items()}
            }
        )
    else:
        logger.debug(
            f"No notifications triggered for request {request.id}",
            extra={
                'request_id': request.id,
                'changes': list(changes.keys())
            }
        )

