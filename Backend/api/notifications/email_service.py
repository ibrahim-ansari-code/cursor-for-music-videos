"""
Email Notification Service

Handles sending email notifications using Azure SendGrid.
"""
import logging
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

import sentry_sdk

from Backend.api.notifications.sendgrid_service import SendGridService
from Backend.config import settings

logger = logging.getLogger(__name__)


def _format_event_date(event_date: datetime) -> str:
    """
    Format event date with capitalized month.

    Helper function to eliminate code duplication in email generation.

    Args:
        event_date: The datetime to format

    Returns:
        Formatted date string in format "Month DD, YYYY" (e.g., "December 25, 2025")
    """
    formatted_date = event_date.strftime("%B %d, %Y")
    # Ensure month is capitalized
    parts = formatted_date.split(" ", 1)
    if parts:
        formatted_date = parts[0].capitalize() + " " + parts[1] if len(parts) > 1 else parts[0].capitalize()
    return formatted_date


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

    @staticmethod
    async def send_tenant_reminder_email(
        tenant_email: str,
        tenant_name: str,
        event_type: str,
        event_title: str,
        event_subtitle: str,
        event_date: Optional[datetime] = None,
        event_amount: Optional[float] = None,
        days_remaining: Optional[int] = None,
        property_name: Optional[str] = None,
        unit_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        custom_subject: Optional[str] = None,
        custom_message: Optional[str] = None
    ) -> bool:
        """
        Send a reminder email to a tenant about an upcoming event.
        
        Uses the reusable BrikliEmailTemplate system for consistent branding.
        
        Args:
            tenant_email: Tenant's email address
            tenant_name: Tenant's name (first + last or company name)
            event_type: Type of event ('rent', 'lease_expiry', 'invoice', 'maintenance', 'insurance')
            event_title: Title of the event (e.g., "Rent Due", "Lease Expires")
            event_subtitle: Subtitle with additional details
            event_date: Date of the event
            event_amount: Amount if applicable (for rent, invoices)
            days_remaining: Days until event (negative if overdue)
            property_name: Name of the property
            unit_name: Name of the unit
            metadata: Optional additional data
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            from Backend.api.notifications.email_templates import (
                BrikliEmailTemplate,
                EmailSection,
                EmailNotice,
                EmailCTA,
                EmailMetadataRow
            )
            from Backend.api.notifications.sendgrid_service import SendGridService
            from Backend.config import settings
            
            # Build content sections based on event type
            sections = []
            metadata_rows = []
            notice = None
            cta = None
            
            # Add main message (custom or default)
            # Treat empty strings as None (use default)
            if custom_message and custom_message.strip():
                # When custom message is provided, skip greeting and use message exactly as typed
                sections.append(EmailSection(text=custom_message))
                greeting = ""  # No greeting for custom messages
            else:
                # Build greeting for default messages
                greeting = f"Hi {tenant_name},"
                # Generate default message based on event type
                if event_type == 'rent':
                    sections.append(
                        EmailSection(text=f"This is a friendly reminder that your rent payment is {event_subtitle.lower()}.")
                    )
                elif event_type == 'lease_expiry':
                    sections.append(
                        EmailSection(text=f"Your lease is expiring {event_subtitle.lower()}.")
                    )
                elif event_type == 'invoice':
                    sections.append(
                        EmailSection(text=f"You have an invoice that is {event_subtitle.lower()}.")
                    )
                elif event_type == 'maintenance':
                    sections.append(
                        EmailSection(text=f"Maintenance is scheduled: {event_subtitle}")
                    )
                elif event_type == 'insurance':
                    sections.append(
                        EmailSection(text=f"Insurance reminder: {event_subtitle}")
                    )
                else:
                    # Generic reminder
                    sections.append(
                        EmailSection(text=f"Reminder: {event_title}")
                    )
                    sections.append(
                        EmailSection(text=event_subtitle)
                    )
            
            # Always add metadata rows and notices based on event type (regardless of custom message)
            if event_type == 'rent':
                if event_amount:
                    metadata_rows.append(
                        EmailMetadataRow(label="Amount Due", value=f"${event_amount:,.2f}", emoji="💰")
                    )

                if event_date:
                    metadata_rows.append(
                        EmailMetadataRow(label="Due Date", value=_format_event_date(event_date), emoji="📅")
                    )
                
                if days_remaining is not None:
                    if days_remaining < 0:
                        notice = EmailNotice(
                            emoji="⚠️",
                            title="Payment Overdue",
                            message=f"This payment is {abs(days_remaining)} day(s) overdue. Please submit payment as soon as possible.",
                            color="#dc2626",  # red
                            bg_color="#fef2f2"
                        )
                    elif days_remaining == 0:
                        notice = EmailNotice(
                            emoji="⏰",
                            title="Due Today",
                            message="This payment is due today. Please submit payment to avoid late fees.",
                            color="#f59e0b",  # amber
                            bg_color="#fff7ed"
                        )
                    elif days_remaining <= 3:
                        notice = EmailNotice(
                            emoji="⏰",
                            title="Upcoming Payment",
                            message=f"This payment is due in {days_remaining} day(s). Please ensure payment is submitted on time.",
                            color="#3b82f6",  # blue
                            bg_color="#eff6ff"
                        )
            
            elif event_type == 'lease_expiry':
                if event_date:
                    metadata_rows.append(
                        EmailMetadataRow(label="Lease End Date", value=_format_event_date(event_date), emoji="📅")
                    )
                
                if days_remaining is not None:
                    if days_remaining <= 30:
                        notice = EmailNotice(
                            emoji="📋",
                            title="Lease Renewal",
                            message="Your lease is expiring soon. Please contact us to discuss renewal options.",
                            color="#3b82f6",
                            bg_color="#eff6ff"
                        )
                    elif not custom_message:
                        # Only add this extra section if using default message
                        sections.append(
                            EmailSection(text="We wanted to give you advance notice so you can plan accordingly.")
                        )
            
            elif event_type == 'invoice':
                if event_amount:
                    metadata_rows.append(
                        EmailMetadataRow(label="Invoice Amount", value=f"${event_amount:,.2f}", emoji="💰")
                    )

                if event_date:
                    metadata_rows.append(
                        EmailMetadataRow(label="Due Date", value=_format_event_date(event_date), emoji="📅")
                    )
                
                if days_remaining is not None and days_remaining < 0:
                    notice = EmailNotice(
                        emoji="⚠️",
                        title="Invoice Overdue",
                        message=f"This invoice is {abs(days_remaining)} day(s) overdue. Please submit payment as soon as possible.",
                        color="#dc2626",
                        bg_color="#fef2f2"
                    )
            
            elif event_type == 'maintenance':
                if event_date:
                    metadata_rows.append(
                        EmailMetadataRow(label="Scheduled Date", value=_format_event_date(event_date), emoji="📅")
                    )
                
                if days_remaining is not None:
                    if days_remaining == 0:
                        notice = EmailNotice(
                            emoji="🔧",
                            title="Maintenance Today",
                            message="Maintenance is scheduled for today. Please ensure access is available.",
                            color="#10b981",  # green
                            bg_color="#ecfdf5"
                        )
                    elif not custom_message:
                        # Only add this extra section if using default message
                        sections.append(
                            EmailSection(text=f"Maintenance is scheduled in {days_remaining} day(s).")
                        )
            
            elif event_type == 'insurance':
                if event_date:
                    metadata_rows.append(
                        EmailMetadataRow(label="Date", value=_format_event_date(event_date), emoji="📅")
                    )
                
                if days_remaining is not None and days_remaining <= 30:
                    notice = EmailNotice(
                        emoji="🛡️",
                        title="Insurance Update Required",
                        message="Please ensure your insurance is up to date.",
                        color="#3b82f6",
                        bg_color="#eff6ff"
                    )
            
            else:
                # Generic reminder - add date if available
                if event_date:
                    metadata_rows.append(
                        EmailMetadataRow(label="Date", value=_format_event_date(event_date), emoji="📅")
                    )
            
            # Add property/unit info to metadata
            if property_name:
                metadata_rows.insert(0, EmailMetadataRow(label="Property", value=property_name, emoji="📍"))
            if unit_name:
                metadata_rows.append(EmailMetadataRow(label="Unit", value=unit_name, emoji="🏠"))
            
            # Generate CTA link to tenant portal (from environment config)
            tenant_portal_url = f"{settings.TENANT_PORTAL_URL}/login"
            cta = EmailCTA(
                text="View Details",
                url=tenant_portal_url
            )
            
            # Generate email subject (use custom if provided)
            subject = custom_subject if custom_subject else f"Reminder: {event_title}"
            
            # Generate HTML email using BrikliEmailTemplate
            html_body = BrikliEmailTemplate.create_email(
                title=event_title,
                greeting=greeting,
                sections=sections,
                metadata=metadata_rows if metadata_rows else None,
                cta=cta,
                notice=notice,
                footer_note="You're receiving this email because you have an upcoming event or payment due."
            )
            
            # Send email via SendGrid using send_raw_email (like maintenance API)
            success = await SendGridService.send_raw_email(
                to_email=tenant_email,
                to_name=tenant_name,
                subject=subject,
                html_content=html_body,
                metadata={
                    **(metadata or {}),
                    'event_type': event_type,
                    'event_date': event_date.isoformat() if event_date else None,
                    'event_amount': event_amount,
                    'days_remaining': days_remaining,
                }
            )
            
            if success:
                logger.info(
                    f"Tenant reminder email sent successfully to {tenant_email}",
                    extra={
                        'tenant_email': tenant_email,
                        'event_type': event_type,
                        'event_title': event_title,
                    }
                )
            
            return success
            
        except Exception as e:
            logger.exception(f"Failed to send tenant reminder email to {tenant_email}")
            sentry_sdk.capture_exception(e, extra={
                'tenant_email': tenant_email,
                'event_type': event_type,
                'event_title': event_title,
            })
            return False

