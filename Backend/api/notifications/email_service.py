"""
Email Notification Service

Handles sending email notifications using Azure SendGrid.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID

import sentry_sdk

from Backend.models.user import User
from Backend.api.notifications.sendgrid_service import SendGridService

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications via SendGrid"""
    
    
    @staticmethod
    async def send_notification_email(
        user: User,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification email to a user via SendGrid.
        
        Args:
            user: User to send email to
            notification_type: Type of notification
            title: Email subject / notification title
            message: Email body / notification message
            link: Optional action link
            metadata: Optional additional data
            
        Returns:
            True if email sent successfully, False otherwise
        """
        # Eagerly capture user attributes to prevent lazy loading in exception handlers
        user_id = user.id
        user_email = user.email
        user_first_name = user.first_name
        user_last_name = user.last_name
        
        try:
            # Get user's full name
            user_name = f"{user_first_name} {user_last_name}".strip() or "Brikli User"
            
            # Send email via SendGrid
            success = await SendGridService.send_email(
                to_email=user_email,
                to_name=user_name,
                subject=title,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                metadata=metadata
            )
            
            if success:
                logger.info(
                    f"Notification email sent successfully to {user_email}",
                    extra={
                        'user_id': str(user_id),
                        'notification_type': notification_type,
                    }
                )
            
            return success
            
        except Exception as e:
            logger.exception(f"Failed to send notification email to {user_email}")
            sentry_sdk.capture_exception(e, extra={
                'user_id': str(user_id),
                'notification_type': notification_type,
            })
            return False
    
    @staticmethod
    async def send_test_email(user: User) -> bool:
        """
        Send a test email to verify email configuration.
        
        Args:
            user: User to send test email to
            
        Returns:
            True if test email sent successfully
        """
        return await EmailService.send_notification_email(
            user=user,
            notification_type='system_update',
            title='Test Notification from Brikli',
            message='This is a test email to verify your notification settings are working correctly. If you received this email, your notifications are properly configured!',
            link='/settings?tab=notifications',
            metadata={'test': True}
        )

