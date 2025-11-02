"""
Email Notification Service

Handles sending email notifications using Azure SendGrid.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID

import sentry_sdk

from Backend.api.notifications.sendgrid_service import SendGridService

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email notifications via SendGrid"""
    
    
    @staticmethod
    async def send_notification_email(
        user_id: UUID,
        user_email: str,
        user_first_name: Optional[str],
        user_last_name: Optional[str],
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a notification email to a user via SendGrid.
        
        Args:
            user_id: UUID of the user
            user_email: Email address to send to
            user_first_name: User's first name
            user_last_name: User's last name
            notification_type: Type of notification
            title: Email subject / notification title
            message: Email body / notification message
            link: Optional action link
            metadata: Optional additional data
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get user's full name
            user_name = f"{user_first_name or ''} {user_last_name or ''}".strip() or "Brikli User"
            
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

