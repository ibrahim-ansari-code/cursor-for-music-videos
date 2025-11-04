"""
Notification API Router

RESTful API endpoints for notification management:
- GET /notifications - List notifications with filters
- GET /notifications/unread-count - Get unread count
- PATCH /notifications/{id}/read - Mark single notification as read
- PATCH /notifications/mark-all-read - Mark all as read
- DELETE /notifications/{id} - Delete notification
- GET /notifications/preferences - Get user preferences
- PUT /notifications/preferences - Update preferences
- POST /notifications/test-notification - Send test in-app notification
- POST /notifications/test-email - Send test email notification

Internal scheduled job endpoints:
- POST /notifications/scheduled/rent-reminders - Trigger rent reminders (pg_cron)
- POST /notifications/scheduled/lease-expiring - Trigger lease expiring alerts (pg_cron)
"""
import logging
import secrets
from typing import Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from Backend.api.auth import get_current_user, get_user_id
from Backend.database import get_session
from Backend.models.user import User
from Backend.config import settings

from .schemas import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    MarkAsReadRequest,
    MarkAsReadResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    NotificationPreferenceUpdateResponse,
    TestNotificationRequest,
    TestNotificationResponse,
    TestEmailRequest,
    TestEmailResponse,
)
from .service import NotificationService
from .scheduled_service import ScheduledNotificationService
from .email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ========================================================================
# RATE LIMITING FOR TEST ENDPOINTS
# ========================================================================

# Database-backed rate limiter for test endpoints (works with multiple workers)
# Limit: 5 requests per hour per user
_rate_limit_max = 5
_rate_limit_window_seconds = 3600  # 1 hour


async def check_test_rate_limit(user_id: UUID, session: AsyncSession) -> bool:
    """
    Check if user is within rate limit for test endpoints using database.
    
    Uses PostgreSQL advisory locks to prevent race conditions between
    concurrent requests. This ensures the check-and-insert is atomic.
    
    Args:
        user_id: User ID to check
        session: Database session
        
    Returns:
        True if request is allowed, False if rate limited
    """
    from sqlalchemy import text
    from datetime import datetime, timedelta, timezone
    
    # Use PostgreSQL advisory lock to make check-and-insert atomic
    # Lock ID is derived from user_id hash to ensure per-user locking
    lock_id = hash(str(user_id)) % 2147483647  # PostgreSQL max int
    
    try:
        # Acquire advisory lock (automatically released at transaction end)
        lock_query = text("SELECT pg_advisory_xact_lock(:lock_id)")
        await session.execute(lock_query, {"lock_id": lock_id})
        
        # Calculate window start time
        window_start = datetime.now(timezone.utc) - timedelta(seconds=_rate_limit_window_seconds)
        
        # Count requests in the current window
        count_query = text("""
            SELECT COUNT(*) 
            FROM notification_delivery_log 
            WHERE user_id = :user_id 
            AND channel = 'test_endpoint'
            AND created_at > :window_start
        """)
        
        result = await session.execute(count_query, {
            "user_id": str(user_id),
            "window_start": window_start
        })
        count: int = result.scalar() or 0
        
        if count >= _rate_limit_max:
            return False
        
        # Record this request
        insert_query = text("""
            INSERT INTO notification_delivery_log (user_id, notification_id, channel, status, created_at)
            VALUES (:user_id, :notification_id, 'test_endpoint', 'sent', NOW())
        """)
        
        await session.execute(insert_query, {
            "user_id": str(user_id),
            "notification_id": "00000000-0000-0000-0000-000000000000"
        })
        await session.commit()
        
        return True
        
    except Exception as e:
        await session.rollback()
        logger.error(f"Rate limit check failed for user {user_id}: {e}")
        # Fail open: allow request if rate limiting system has errors
        return True


# ========================================================================
# NOTIFICATION ENDPOINTS
# ========================================================================

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(20, ge=1, le=100, description="Number of notifications to return"),
    offset: int = Query(0, ge=0, description="Number of notifications to skip"),
    is_read: Optional[bool] = Query(None, description="Filter by read status"),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    user_id: UUID = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
) -> NotificationListResponse:
    """
    Get paginated list of notifications for the current user.
    
    Supports filtering by:
    - is_read: Boolean to filter read/unread
    - type: Notification type (rent_reminder, payment_received, etc.)
    - priority: Priority level (urgent, high, normal, low)
    
    Returns notifications in reverse chronological order (newest first).
    """
    try:
        notifications, total = await NotificationService.get_notifications(
            user_id=user_id,
            session=session,
            limit=limit,
            offset=offset,
            is_read=is_read,
            type=type,
            priority=priority
        )
        
        # Get unread count
        unread_count = await NotificationService.get_unread_count(
            user_id=user_id,
            session=session
        )
        
        return NotificationListResponse(
            notifications=[NotificationResponse.model_validate(n) for n in notifications],
            total=total,
            unread_count=unread_count,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.exception(f"Failed to get notifications for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notifications"
        )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    user_id: UUID = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
) -> UnreadCountResponse:
    """
    Get count of unread notifications for the current user.
    
    This endpoint is lightweight and suitable for frequent polling
    to update the notification badge in the UI.
    """
    try:
        unread_count = await NotificationService.get_unread_count(
            user_id=user_id,
            session=session
        )
        
        return UnreadCountResponse(unread_count=unread_count)
        
    except Exception as e:
        logger.exception(f"Failed to get unread count for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve unread count"
        )


@router.patch("/{notification_id}/read", response_model=MarkAsReadResponse)
async def mark_notification_as_read(
    notification_id: UUID,
    user_id: UUID = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
) -> MarkAsReadResponse:
    """
    Mark a single notification as read.
    
    Sets is_read=True and records the read_at timestamp.
    """
    try:
        marked_count = await NotificationService.mark_as_read(
            notification_ids=[notification_id],
            user_id=user_id,
            session=session
        )
        
        if marked_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or already read"
            )
        
        return MarkAsReadResponse(
            success=True,
            marked_count=marked_count,
            message="Notification marked as read"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to mark notification {notification_id} as read")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notification as read"
        )


@router.patch("/mark-all-read", response_model=MarkAsReadResponse)
async def mark_all_notifications_as_read(
    user_id: UUID = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
) -> MarkAsReadResponse:
    """
    Mark all unread notifications as read for the current user.
    
    Useful for "mark all as read" functionality in the UI.
    """
    try:
        marked_count = await NotificationService.mark_all_as_read(
            user_id=user_id,
            session=session
        )
        
        return MarkAsReadResponse(
            success=True,
            marked_count=marked_count,
            message=f"Marked {marked_count} notifications as read"
        )
        
    except Exception as e:
        logger.exception(f"Failed to mark all notifications as read for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark all notifications as read"
        )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    user_id: UUID = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete (archive) a notification.
    
    This marks the notification as archived rather than permanently deleting it.
    Archived notifications won't appear in the user's notification list.
    """
    try:
        success = await NotificationService.delete_notification(
            notification_id=notification_id,
            user_id=user_id,
            session=session
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to delete notification {notification_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification"
        )


# ========================================================================
# NOTIFICATION PREFERENCE ENDPOINTS
# ========================================================================

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    user_id: UUID = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
) -> NotificationPreferenceResponse:
    """
    Get notification preferences for the current user.
    
    Returns all preference settings including:
    - Global enabled/disabled toggle
    - Per-type preferences (enabled, channels, frequency)
    - Email digest settings
    - Quiet hours settings
    """
    try:
        preferences = await NotificationService.get_user_preferences(
            user_id=user_id,
            session=session
        )
        
        return NotificationPreferenceResponse.model_validate(preferences)
        
    except Exception as e:
        logger.exception(f"Failed to get preferences for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve notification preferences"
        )


@router.put("/preferences", response_model=NotificationPreferenceUpdateResponse)
async def update_notification_preferences(
    preference_update: NotificationPreferenceUpdateRequest,
    user_id: UUID = Depends(get_user_id),
    session: AsyncSession = Depends(get_session)
) -> NotificationPreferenceUpdateResponse:
    """
    Update notification preferences for the current user.
    
    Supports partial updates - only provided fields will be updated.
    
    Example request body to disable rent reminders:
    {
        "preferences": {
            "rent_reminder": {
                "enabled": false,
                "channels": ["in_app"],
                "frequency": "immediate"
            }
        }
    }
    """
    try:
        updated_preferences = await NotificationService.update_preferences(
            user_id=user_id,
            session=session,
            enabled=preference_update.enabled,
            preferences=preference_update.preferences,
            email_digest_frequency=preference_update.email_digest_frequency,
            email_digest_time=preference_update.email_digest_time,
            timezone=preference_update.timezone,
            quiet_hours_enabled=preference_update.quiet_hours_enabled,
            quiet_hours_start=preference_update.quiet_hours_start,
            quiet_hours_end=preference_update.quiet_hours_end
        )
        
        return NotificationPreferenceUpdateResponse(
            success=True,
            message="Notification preferences updated successfully",
            preferences=NotificationPreferenceResponse.model_validate(updated_preferences)
        )
        
    except Exception as e:
        logger.exception(f"Failed to update preferences for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification preferences"
        )


# ========================================================================
# TESTING & DEBUG ENDPOINTS
# ========================================================================

@router.post("/test-notification", response_model=TestNotificationResponse)
async def send_test_notification(
    test_request: TestNotificationRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> TestNotificationResponse:
    """
    Send a test in-app notification to the current user.
    
    Rate limited to 5 requests per hour per user.
    """
    user_id = None
    try:
        # Capture user attributes early
        user_id = current_user.id
        
        # Check rate limit (database-backed, works with multiple workers)
        if not await check_test_rate_limit(user_id, session):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. You can send up to 5 test notifications per hour."
            )
        
        # Define test messages
        test_messages = {
            'rent_reminder': {
                'title': 'Test: Rent Due Reminder',
                'message': 'This is a test rent reminder notification. Your rent payment is due soon.'
            },
            'payment_received': {
                'title': 'Test: Payment Received',
                'message': 'This is a test payment confirmation. A payment of $1,500.00 has been received.'
            },
            'lease_expiring': {
                'title': 'Test: Lease Expiring',
                'message': 'This is a test lease expiration notice. A lease will expire in 30 days.'
            },
            'maintenance_update': {
                'title': 'Test: Maintenance Update',
                'message': 'This is a test maintenance notification. A work order has been completed.'
            },
            'new_application': {
                'title': 'Test: New Application',
                'message': 'This is a test application notification. A new tenant application has been submitted.'
            },
            'system_update': {
                'title': 'Test: System Update',
                'message': 'This is a test system notification. New features have been added to Brikli.'
            }
        }
        
        test_data = test_messages.get(
            test_request.notification_type,
            {'title': 'Test Notification', 'message': 'This is a test notification.'}
        )
        
        # Create in-app notification only
        notification = await NotificationService.create_notification(
            user_id=user_id,
            type=test_request.notification_type,
            title=test_data['title'],
            message=test_data['message'],
            metadata={'test': True},
            priority='normal',
            session=session
        )
        
        # Handle case where notification creation was skipped due to user preferences
        if notification is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create test notification: '{test_request.notification_type}' notifications are disabled in your preferences. Please enable them first."
            )
        
        return TestNotificationResponse(
            success=True,
            message="Test notification created successfully!",
            notification_id=str(notification.id)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_user_id = user_id or "unknown"
        logger.exception(f"Failed to send test notification for user {log_user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )


@router.post("/test-email", response_model=TestEmailResponse)
async def send_test_email(
    test_request: TestEmailRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> TestEmailResponse:
    """
    Send a test email notification to the current user via SendGrid.
    
    This endpoint ONLY sends an email - it does NOT create an in-app notification.
    Use the separate /test-notification endpoint for in-app notification testing.
    Rate limited to 5 requests per hour per user.
    """
    user_id = None
    try:
        # Capture user attributes early to avoid lazy loading in error handler
        user_id = current_user.id
        user_email = current_user.email
        user_first_name = current_user.first_name
        user_last_name = current_user.last_name
        
        # Check rate limit (database-backed, works with multiple workers)
        if not await check_test_rate_limit(user_id, session):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. You can send up to 5 test emails per hour."
            )
        
        # Define test messages for different notification types
        test_messages = {
            'rent_reminder': {
                'title': 'Test: Rent Due Reminder',
                'message': 'This is a test rent reminder notification. Your rent payment is due soon.'
            },
            'payment_received': {
                'title': 'Test: Payment Received',
                'message': 'This is a test payment confirmation. A payment of $1,500.00 has been received.'
            },
            'lease_expiring': {
                'title': 'Test: Lease Expiring',
                'message': 'This is a test lease expiration notice. A lease will expire in 30 days.'
            },
            'maintenance_update': {
                'title': 'Test: Maintenance Update',
                'message': 'This is a test maintenance notification. A work order has been completed.'
            },
            'new_application': {
                'title': 'Test: New Application',
                'message': 'This is a test application notification. A new tenant application has been submitted.'
            },
            'system_update': {
                'title': 'Test: System Update',
                'message': 'This is a test system notification. New features have been added to Brikli.'
            }
        }
        
        test_data = test_messages.get(
            test_request.notification_type,
            {'title': 'Test Notification', 'message': 'This is a test notification.'}
        )
        
        # Send email via SendGrid (no in-app notification created)
        email_sent = await EmailService.send_notification_email(
            user_id=user_id,
            user_email=user_email,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            notification_type=test_request.notification_type,
            title=test_data['title'],
            message=test_data['message'],
            link='/settings?tab=notifications',
            metadata={'test': True}
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send test email. Please check SendGrid configuration and try again."
            )
        
        return TestEmailResponse(
            success=True,
            message=f"Test email sent successfully to {user_email}!",
            email_sent_to=user_email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_user_id = user_id or "unknown"
        logger.exception(f"Failed to send test email for user {log_user_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test email"
        )


# ========================================================================
# SCHEDULED JOB ENDPOINTS (Internal - Called by pg_cron)
# ========================================================================

@router.post("/scheduled/rent-reminders", include_in_schema=False)
async def trigger_rent_reminders(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    [Internal] Scheduled job endpoint for rent reminders.
    
    Called by pg_cron daily at 14:00 UTC (9 AM EST).
    Finds all active leases with rent due in 3 days and creates notifications.
    
    Authentication: Requires X-Internal-API-Key header.
    """
    # Verify internal API key
    api_key = request.headers.get('X-Internal-API-Key')
    if not api_key or not secrets.compare_digest(api_key, settings.INTERNAL_CRON_API_KEY):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        result = await ScheduledNotificationService.send_rent_reminders(session)
        logger.info(f"Rent reminders sent: {result}")
        return result
    except Exception as e:
        logger.exception("Failed to send rent reminders")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled/lease-expiring", include_in_schema=False)
async def trigger_lease_expiring(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    [Internal] Scheduled job endpoint for lease expiring alerts.
    
    Called by pg_cron daily at 14:00 UTC (9 AM EST).
    Finds leases expiring in 30 or 60 days and creates notifications.
    
    Authentication: Requires X-Internal-API-Key header.
    """
    # Verify internal API key
    api_key = request.headers.get('X-Internal-API-Key')
    if not api_key or api_key != settings.INTERNAL_CRON_API_KEY:
        logger.warning("Unauthorized lease expiring trigger attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        result = await ScheduledNotificationService.send_lease_expiring_notifications(session)
        logger.info(f"Lease expiring notifications sent: {result}")
        return result
    except Exception as e:
        logger.exception("Failed to send lease expiring notifications")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduled/reminders", include_in_schema=False)
async def trigger_reminder_notifications(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    [Internal] Scheduled job endpoint for custom reminder notifications.
    
    Called by pg_cron every 15 minutes.
    Finds reminders that need notifications in the next 15-minute window and sends them.
    
    Authentication: Requires X-Internal-API-Key header.
    """
    # Verify internal API key
    api_key = request.headers.get('X-Internal-API-Key')
    if not api_key or api_key != settings.INTERNAL_CRON_API_KEY:
        logger.warning("Unauthorized reminder notification trigger attempt")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        result = await ScheduledNotificationService.send_reminder_notifications(session)
        logger.info(f"Reminder notifications sent: {result}")
        return result
    except Exception as e:
        logger.exception("Failed to send reminder notifications")
        raise HTTPException(status_code=500, detail=str(e))

