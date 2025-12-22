"""
Notification Service

Business logic for the notification system including:
- Creating and managing notifications
- Managing user preferences
- Querying notifications with filters
- Batch operations (mark all read, cleanup)
"""
import logging
from datetime import datetime, UTC
from typing import List, Optional, Dict, Any
from uuid import UUID

import sentry_sdk
from sqlalchemy import select, func, update, delete, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from Backend.models.notification import Notification, NotificationPreference, NotificationDeliveryLog
from Backend.models.user import User
from Backend.utils.datetime_utils import create_audit_datetime
from Backend.api.notifications.email_service import EmailService

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for notification management"""
    
    # ========================================================================
    # NOTIFICATION CRUD OPERATIONS
    # ========================================================================
    
    @staticmethod
    async def create_notification(
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        session: AsyncSession,
        link: Optional[str] = None,
        actor_id: Optional[UUID] = None,
        actor_name: Optional[str] = None,
        actor_avatar_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
        group_key: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Notification:
        """
        Create a new notification for a user.
        
        This is the central function for creating notifications. It:
        1. Checks user preferences to see if notification should be created
        2. Creates the notification in the database
        3. Logs the delivery (to be extended with email/SMS sending)
        
        Args:
            user_id: UUID of the user to notify
            type: Notification type (rent_reminder, payment_received, etc.)
            title: Notification title
            message: Notification message
            session: Database session
            link: Optional deep link to relevant page
            actor_id: Optional UUID of user who triggered this notification
            actor_name: Optional name of actor
            actor_avatar_url: Optional avatar URL of actor
            metadata: Optional metadata dict (property_id, tenant_id, amount, etc.)
            priority: Priority level (urgent, high, normal, low)
            group_key: Optional key for grouping related notifications
            expires_at: Optional expiration timestamp
            
        Returns:
            Created Notification object
            
        Raises:
            Exception: If notification creation fails
        """
        try:
            # Check user preferences
            preferences = await NotificationService.get_user_preferences(user_id, session)
            
            #  If preferences don't exist (shouldn't happen), create them
            if not preferences:
                preferences = await NotificationService.create_default_preferences(user_id, session)
            
            # Determine delivery channels based on preferences
            delivery_channels = await NotificationService._get_delivery_channels(
                user_id, type, preferences, session
            )
            
            # If no delivery channels enabled, skip notification creation
            if not delivery_channels:
                logger.info(f"Skipping notification creation for user {user_id} - all channels disabled for type {type}")
                # Return None but with proper type annotation handling in the router
                return None  # type: ignore
            
            # Create notification
            notification = Notification(
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                link=link,
                actor_id=actor_id,
                actor_name=actor_name,
                actor_avatar_url=actor_avatar_url,
                metadata_=metadata or {},
                priority=priority,
                delivery_channels=delivery_channels,
                group_key=group_key,
                expires_at=expires_at,
                created_at=create_audit_datetime()
            )
            
            session.add(notification)
            await session.flush()  # Get the notification ID
            
            # Log delivery attempt for in-app notification (always created)
            if "in_app" in delivery_channels and notification.id:
                await NotificationService._log_delivery(
                    notification.id,
                    user_id,
                    "in_app",
                    "delivered",
                    session
                )

            # Trigger email sending if "email" in delivery_channels
            if "email" in delivery_channels and notification.id:
                try:
                    # Fetch user to get email and name
                    user_query = select(User).where(col(User.id) == user_id)
                    user_result = await session.execute(user_query)
                    user = user_result.scalar_one_or_none()

                    if user and user.email:
                        email_success = await EmailService.send_notification_email(
                            user_id=user_id,
                            user_email=user.email,
                            user_first_name=user.first_name,
                            user_last_name=user.last_name,
                            notification_type=type,
                            title=title,
                            message=message,
                            link=link,
                            metadata=metadata
                        )

                        await NotificationService._log_delivery(
                            notification.id,
                            user_id,
                            "email",
                            "delivered" if email_success else "failed",
                            session
                        )

                        if email_success:
                            logger.info(f"Email notification sent to {user.email} for notification {notification.id}")
                        else:
                            logger.warning(f"Failed to send email notification to {user.email} for notification {notification.id}")
                    else:
                        logger.warning(f"Cannot send email notification - user {user_id} has no email address")

                except Exception as email_error:
                    logger.exception(f"Error sending email notification for {notification.id}: {email_error}")
                    # Don't fail the entire notification creation if email fails
                    sentry_sdk.capture_exception(email_error)

            # TODO: Trigger SMS sending if "sms" in delivery_channels (not implemented)

            await session.commit()
            await session.refresh(notification)
            
            logger.info(f"Created notification {notification.id} for user {user_id} (type: {type})")
            
            # Report to Sentry for monitoring
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("notification_type", type)
                scope.set_tag("priority", priority)
                scope.set_context("notification", {
                    "id": str(notification.id),
                    "user_id": str(user_id),
                    "channels": delivery_channels
                })
                sentry_sdk.capture_message(f"Notification created: {type}", level="info")
            
            return notification
            
        except Exception as e:
            logger.exception(f"Failed to create notification for user {user_id}")
            await session.rollback()
            
            # Report error to Sentry
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("notification_type", type)
                scope.set_context("notification_data", {
                    "user_id": str(user_id),
                    "type": type,
                    "title": title
                })
                sentry_sdk.capture_exception(e)
            
            raise
    
    @staticmethod
    async def get_notifications(
        user_id: UUID,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        is_read: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> tuple[List[Notification], int]:
        """
        Get paginated notifications for a user with optional filters.
        
        Returns:
            Tuple of (notifications list, total count)
        """
        try:
            # Build query with filters
            filters = [col(Notification.user_id) == user_id]
            
            if is_read is not None:
                filters.append(col(Notification.is_read) == is_read)
            
            if is_archived is not None:
                filters.append(col(Notification.is_archived) == is_archived)
            else:
                # By default, don't show archived notifications
                filters.append(col(Notification.is_archived) == False)
            
            if type:
                filters.append(col(Notification.type) == type)
            
            if priority:
                filters.append(col(Notification.priority) == priority)
            
            query = select(Notification).where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar()
            
            # Apply sorting, pagination
            query = query.order_by(col(Notification.created_at).desc())
            query = query.limit(limit).offset(offset)
            
            result = await session.execute(query)
            notifications = result.scalars().all()
            
            return list(notifications), total or 0
            
        except Exception as e:
            logger.exception(f"Failed to get notifications for user {user_id}")
            sentry_sdk.capture_exception(e)
            raise
    
    @staticmethod
    async def get_unread_count(user_id: UUID, session: AsyncSession) -> int:
        """Get count of unread notifications for a user"""
        try:
            filters = [
                col(Notification.user_id) == user_id,
                col(Notification.is_read) == False,
                col(Notification.is_archived) == False
            ]
            query = select(func.count()).where(and_(*filters))
            result = await session.execute(query)
            count = result.scalar()
            return count or 0
            
        except Exception as e:
            logger.exception(f"Failed to get unread count for user {user_id}")
            sentry_sdk.capture_exception(e)
            return 0
    
    @staticmethod
    async def mark_as_read(
        notification_ids: List[UUID],
        user_id: UUID,
        session: AsyncSession
    ) -> int:
        """
        Mark specific notifications as read.
        
        Returns:
            Number of notifications marked as read
        """
        try:
            filters = [
                col(Notification.id).in_(notification_ids),
                col(Notification.user_id) == user_id,
                col(Notification.is_read) == False
            ]
            stmt = (
                update(Notification)
                .where(and_(*filters))
                .values(is_read=True, read_at=create_audit_datetime())
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            marked_count = result.rowcount
            logger.info(f"Marked {marked_count} notifications as read for user {user_id}")
            
            return marked_count
            
        except Exception as e:
            logger.exception(f"Failed to mark notifications as read for user {user_id}")
            await session.rollback()
            sentry_sdk.capture_exception(e)
            raise
    
    @staticmethod
    async def mark_all_as_read(user_id: UUID, session: AsyncSession) -> int:
        """
        Mark all unread notifications as read for a user.
        
        Returns:
            Number of notifications marked as read
        """
        try:
            filters = [
                col(Notification.user_id) == user_id,
                col(Notification.is_read) == False
            ]
            stmt = (
                update(Notification)
                .where(and_(*filters))
                .values(is_read=True, read_at=create_audit_datetime())
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            marked_count = result.rowcount
            logger.info(f"Marked all {marked_count} notifications as read for user {user_id}")
            
            return marked_count
            
        except Exception as e:
            logger.exception(f"Failed to mark all notifications as read for user {user_id}")
            await session.rollback()
            sentry_sdk.capture_exception(e)
            raise
    
    @staticmethod
    async def delete_notification(
        notification_id: UUID,
        user_id: UUID,
        session: AsyncSession
    ) -> bool:
        """
        Delete (archive) a notification.
        
        Returns:
            True if notification was deleted, False otherwise
        """
        try:
            filters = [
                col(Notification.id) == notification_id,
                col(Notification.user_id) == user_id
            ]
            stmt = (
                update(Notification)
                .where(and_(*filters))
                .values(is_archived=True)
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            if result.rowcount > 0:
                logger.info(f"Archived notification {notification_id} for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.exception(f"Failed to delete notification {notification_id}")
            await session.rollback()
            sentry_sdk.capture_exception(e)
            raise
    
    # ========================================================================
    # NOTIFICATION PREFERENCE OPERATIONS
    # ========================================================================
    
    @staticmethod
    async def get_user_preferences(
        user_id: UUID,
        session: AsyncSession
    ) -> NotificationPreference:
        """
        Get notification preferences for a user.
        
        Creates default preferences if they don't exist.
        """
        try:
            query = select(NotificationPreference).where(
                col(NotificationPreference.user_id) == user_id
            )
            result = await session.execute(query)
            preferences = result.scalar_one_or_none()
            
            # If no preferences exist, create defaults
            if not preferences:
                preferences = await NotificationService.create_default_preferences(
                    user_id, session
                )
            
            return preferences
            
        except Exception as e:
            logger.exception(f"Failed to get preferences for user {user_id}")
            sentry_sdk.capture_exception(e)
            raise
    
    @staticmethod
    async def create_default_preferences(
        user_id: UUID,
        session: AsyncSession
    ) -> NotificationPreference:
        """Create default notification preferences for a user"""
        try:
            preferences = NotificationPreference(
                user_id=user_id,
                enabled=True,
                created_at=create_audit_datetime(),
                updated_at=create_audit_datetime()
            )
            
            session.add(preferences)
            await session.commit()
            await session.refresh(preferences)
            
            logger.info(f"Created default notification preferences for user {user_id}")
            return preferences
            
        except Exception as e:
            logger.exception(f"Failed to create default preferences for user {user_id}")
            await session.rollback()
            sentry_sdk.capture_exception(e)
            raise
    
    @staticmethod
    async def update_preferences(
        user_id: UUID,
        session: AsyncSession,
        enabled: Optional[bool] = None,
        preferences: Optional[Dict[str, Any]] = None,
        email_digest_frequency: Optional[str] = None,
        email_digest_time: Optional[Any] = None,
        timezone: Optional[str] = None,
        quiet_hours_enabled: Optional[bool] = None,
        quiet_hours_start: Optional[Any] = None,
        quiet_hours_end: Optional[Any] = None,
    ) -> NotificationPreference:
        """
        Update notification preferences for a user.
        
        Only updates provided fields (partial update).
        """
        try:
            # Get existing preferences
            user_prefs = await NotificationService.get_user_preferences(user_id, session)
            
            # Update fields if provided
            if enabled is not None:
                user_prefs.enabled = enabled

            if preferences is not None:
                # Deep merge each updated type to preserve nested settings like 'channels'
                # This allows partial updates like {"payment_received": {"email": false}} without
                # losing other nested keys within that notification type
                # IMPORTANT: Create a new dict to trigger SQLAlchemy change detection for JSONB
                updated_prefs = dict(user_prefs.preferences) if user_prefs.preferences else {}
                for notif_type, new_pref in preferences.items():
                    existing = updated_prefs.get(notif_type, {})
                    updated_prefs[notif_type] = {**existing, **new_pref}
                user_prefs.preferences = updated_prefs
            
            if email_digest_frequency is not None:
                user_prefs.email_digest_frequency = email_digest_frequency
            
            if email_digest_time is not None:
                user_prefs.email_digest_time = email_digest_time
            
            if timezone is not None:
                user_prefs.timezone = timezone
            
            if quiet_hours_enabled is not None:
                user_prefs.quiet_hours_enabled = quiet_hours_enabled
            
            if quiet_hours_start is not None:
                user_prefs.quiet_hours_start = quiet_hours_start
            
            if quiet_hours_end is not None:
                user_prefs.quiet_hours_end = quiet_hours_end
            
            user_prefs.updated_at = create_audit_datetime()
            
            await session.commit()
            await session.refresh(user_prefs)
            
            logger.info(f"Updated notification preferences for user {user_id}")
            return user_prefs
            
        except Exception as e:
            logger.exception(f"Failed to update preferences for user {user_id}")
            await session.rollback()
            sentry_sdk.capture_exception(e)
            raise
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    @staticmethod
    async def _get_delivery_channels(
        user_id: UUID,
        notification_type: str,
        preferences: NotificationPreference,
        session: AsyncSession
    ) -> List[str]:
        """
        Determine which delivery channels to use based on user preferences.
        
        Returns:
            List of enabled channels (e.g., ['in_app', 'email'])
        """
        # If notifications globally disabled, return empty list
        if not preferences.enabled:
            return []
        
        # Get preferences for this notification type
        type_prefs = preferences.preferences.get(notification_type, {})

        # If this type is disabled, return empty list
        if not type_prefs.get('enabled', True):
            return []

        # Default channels when preference type is not configured
        # These match the frontend defaults and NotificationPreference model defaults
        default_channels_by_type = {
            'rent_reminder': ['in_app', 'email'],
            'payment_received': ['in_app', 'email'],
            'lease_expiring': ['in_app', 'email'],
            'maintenance_update': ['in_app', 'email'],
            'maintenance_request_new': ['in_app', 'email'],  # Falls under maintenance_update in UI
            'new_application': ['in_app'],  # Disabled by default
            'system_update': ['in_app'],     # Disabled by default
        }

        # Map sub-types to their parent preference category for lookup
        # This allows maintenance_request_new to use maintenance_update preferences
        preference_type_mapping = {
            'maintenance_request_new': 'maintenance_update',
        }
        lookup_type = preference_type_mapping.get(notification_type, notification_type)

        # Re-check type_prefs using mapped type if different
        if lookup_type != notification_type and not type_prefs:
            type_prefs = preferences.preferences.get(lookup_type, {})
            if not type_prefs.get('enabled', True):
                return []

        # Use lookup_type to get defaults so sub-types inherit parent category defaults
        default_channels = default_channels_by_type.get(
            lookup_type,
            default_channels_by_type.get(notification_type, ['in_app', 'email'])
        )

        # Return configured channels for this type, falling back to type-specific defaults
        channels = type_prefs.get('channels', default_channels)
        
        # Always include in_app if any channels are enabled
        if channels and 'in_app' not in channels:
            channels.append('in_app')
        
        return channels
    
    @staticmethod
    async def _log_delivery(
        notification_id: UUID,
        user_id: UUID,
        channel: str,
        status: str,
        session: AsyncSession,
        error_message: Optional[str] = None
    ) -> None:
        """Log a notification delivery attempt"""
        try:
            log_entry = NotificationDeliveryLog(
                notification_id=notification_id,
                user_id=user_id,
                channel=channel,
                status=status,
                error_message=error_message,
                created_at=create_audit_datetime(),
                sent_at=create_audit_datetime() if status in ['sent', 'delivered'] else None,
                delivered_at=create_audit_datetime() if status == 'delivered' else None
            )
            
            session.add(log_entry)
            # Don't commit here - let the caller commit
            
        except Exception as e:
            logger.exception(f"Failed to log delivery for notification {notification_id}")
            # Don't raise - delivery logging failure shouldn't break notification creation
    
    # ========================================================================
    # CLEANUP & MAINTENANCE
    # ========================================================================
    
    @staticmethod
    async def cleanup_expired_notifications(session: AsyncSession) -> int:
        """
        Delete expired notifications.
        
        Returns:
            Number of notifications deleted
        """
        try:
            filters = [
                col(Notification.expires_at).isnot(None),
                col(Notification.expires_at) < datetime.now(UTC)
            ]
            stmt = delete(Notification).where(and_(*filters))
            
            result = await session.execute(stmt)
            await session.commit()
            
            deleted_count = result.rowcount
            logger.info(f"Cleaned up {deleted_count} expired notifications")
            
            return deleted_count
            
        except Exception as e:
            logger.exception("Failed to cleanup expired notifications")
            await session.rollback()
            sentry_sdk.capture_exception(e)
            return 0

