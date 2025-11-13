"""
SendGrid Email Service

Handles sending email notifications using Azure SendGrid.
"""
import logging
from typing import Optional, Dict, Any

import sentry_sdk
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To

from Backend.config import settings

logger = logging.getLogger(__name__)


class SendGridService:
    """Service for sending emails via SendGrid"""
    
    @staticmethod
    def _get_sendgrid_client() -> Optional[SendGridAPIClient]:
        """
        Get SendGrid client instance.
        
        Returns:
            SendGridAPIClient if configured, None otherwise
        """
        if not settings.SENDGRID_API_KEY:
            logger.warning("SendGrid API key not configured")
            return None
        
        return SendGridAPIClient(settings.SENDGRID_API_KEY)
    
    @staticmethod
    def _create_html_template(
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        icon: str = "🔔"
    ) -> str:
        """
        Generate responsive HTML email template.
        
        Args:
            notification_type: Type of notification
            title: Email title
            message: Email message
            link: Optional action link
            icon: Emoji icon for the notification
            
        Returns:
            HTML string for email body
        """
        # Action button HTML
        action_button = ''
        if link:
            # Ensure link is absolute
            if not link.startswith('http'):
                base_url = settings.FRONTEND_URL or 'https://app.brikli.com'
                link = f"{base_url}{link}"
            
            action_button = f'''
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin: 32px auto;">
                <tr>
                    <td style="border-radius: 8px; background: #14b8a6;">
                        <a href="{link}" target="_blank" style="background: #14b8a6; border: none; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 24px; text-decoration: none; padding: 12px 24px; color: #ffffff; display: inline-block; border-radius: 8px; font-weight: 500;">
                            View Details
                        </a>
                    </td>
                </tr>
            </table>
            '''
        
        # Full HTML template
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="X-UA-Compatible" content="IE=edge">
            <title>{title}</title>
            <!--[if mso]>
            <style type="text/css">
                body, table, td {{font-family: Arial, Helvetica, sans-serif !important;}}
            </style>
            <![endif]-->
        </head>
        <body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f3f4f6;">
                <tr>
                    <td style="padding: 40px 20px;">
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #14b8a6 0%, #0891b2 100%); padding: 32px 24px; text-align: center; border-radius: 12px 12px 0 0;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600; letter-spacing: -0.5px;">
                                        🏠 Brikli Property Management
                                    </h1>
                                </td>
                            </tr>
                            
                            <!-- Icon -->
                            <tr>
                                <td style="padding: 32px 24px 0; text-align: center;">
                                    <div style="font-size: 48px; line-height: 1; margin-bottom: 16px;">
                                        {icon}
                                    </div>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td style="padding: 0 24px 32px;">
                                    <h2 style="color: #111827; font-size: 20px; font-weight: 600; margin: 0 0 16px 0; text-align: center;">
                                        {title}
                                    </h2>
                                    <p style="color: #4b5563; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0; text-align: center;">
                                        {message}
                                    </p>
                                    {action_button}
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="padding: 24px; text-align: center; border-top: 1px solid #e5e7eb;">
                                    <p style="color: #6b7280; font-size: 14px; line-height: 1.5; margin: 0 0 8px 0;">
                                        This is an automated notification from Brikli Property Management.
                                    </p>
                                    <p style="margin: 0;">
                                        <a href="{settings.FRONTEND_URL or 'https://app.brikli.com'}/settings?tab=notifications" style="color: #14b8a6; text-decoration: none; font-size: 14px;">
                                            Manage notification preferences
                                        </a>
                                    </p>
                                </td>
                            </tr>
                        </table>
                        
                        <!-- Footer copyright -->
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="margin: 20px auto 0;">
                            <tr>
                                <td style="text-align: center; color: #9ca3af; font-size: 12px;">
                                    <p style="margin: 0;">
                                        © 2025 Brikli Property Management. All rights reserved.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        return html
    
    @staticmethod
    def _get_notification_icon(notification_type: str) -> str:
        """Get emoji icon for notification type"""
        icon_map = {
            'rent_reminder': '💰',
            'lease_expiring': '📅',
            'system_update': 'ℹ️',
        }
        return icon_map.get(notification_type, '🔔')
    
    @staticmethod
    async def send_email(
        to_email: str,
        to_name: str,
        subject: str,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an email via SendGrid.
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject line
            notification_type: Type of notification
            title: Email title (displayed in body)
            message: Email message content
            link: Optional action link
            metadata: Optional additional metadata
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            client = SendGridService._get_sendgrid_client()
            if not client:
                logger.error("SendGrid client not configured")
                return False
            
            # Get notification icon
            icon = SendGridService._get_notification_icon(notification_type)
            
            # Generate HTML content
            html_content = SendGridService._create_html_template(
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
                icon=icon
            )
            
            # Create email message
            from_email = Email(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME)
            to_email_obj = To(to_email, to_name)
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email_obj,
                subject=subject,
                html_content=html_content
            )
            
            # Add metadata as custom args for tracking
            if metadata:
                mail.custom_arg = [
                    {"notification_type": notification_type},
                    {"test": str(metadata.get('test', False))}
                ]
            
            # Send email
            response = client.send(mail)
            
            if response.status_code in [200, 201, 202]:
                logger.info(
                    f"Email sent successfully to {to_email}",
                    extra={
                        'to_email': to_email,
                        'notification_type': notification_type,
                        'status_code': response.status_code
                    }
                )
                return True
            else:
                logger.error(
                    f"SendGrid API returned non-success status: {response.status_code}",
                    extra={
                        'status_code': response.status_code,
                        'body': response.body,
                        'headers': dict(response.headers)
                    }
                )
                return False
                
        except Exception as e:
            logger.exception(f"Failed to send email to {to_email}")
            sentry_sdk.capture_exception(e, extra={
                'to_email': to_email,
                'notification_type': notification_type,
            })
            return False
    
    @staticmethod
    async def send_raw_email(
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send an email with raw HTML content via SendGrid.
        
        Use this for custom-generated HTML emails (e.g., vendor notifications).
        
        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject line
            html_content: Complete HTML email content
            metadata: Optional additional metadata for tracking
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            client = SendGridService._get_sendgrid_client()
            if not client:
                logger.error("SendGrid client not configured")
                return False
            
            # Create email message
            from_email = Email(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME)
            to_email_obj = To(to_email, to_name)
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email_obj,
                subject=subject,
                html_content=html_content
            )
            
            # Add metadata as custom args for tracking
            if metadata:
                mail.custom_args = {
                    "email_type": metadata.get('email_type', 'custom'),
                    "request_id": str(metadata.get('request_id', ''))
                }
            
            # Send email in thread executor to avoid blocking event loop
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, client.send, mail)
            
            if response.status_code in [200, 201, 202]:
                logger.info(
                    f"Raw HTML email sent successfully to {to_email}",
                    extra={
                        'to_email': to_email,
                        'status_code': response.status_code,
                        'metadata': metadata
                    }
                )
                return True
            else:
                logger.error(
                    f"SendGrid API returned non-success status: {response.status_code}",
                    extra={
                        'status_code': response.status_code,
                        'body': response.body,
                        'headers': dict(response.headers)
                    }
                )
                return False
                
        except Exception as e:
            logger.exception(f"Failed to send raw HTML email to {to_email}")
            sentry_sdk.capture_exception(e, extra={
                'to_email': to_email,
                'metadata': metadata
            })
            return False

