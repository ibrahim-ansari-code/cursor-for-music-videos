"""Stripe Webhook Background Tasks"""
import logging
from datetime import datetime

from Backend.api.billing.webhook_utils import log_billing_audit

logger = logging.getLogger(__name__)


async def send_subscription_created_email(
    user_email: str,
    user_first_name: str | None,
    user_last_name: str | None,
    plan_name: str,
    plan_amount: float,
    plan_currency: str,
    subscription_id: str,
    trial_start: datetime | None,
    trial_end: datetime | None,
    event_id: str
):
    """Background task: Send subscription created welcome email"""
    from Backend.api.billing.email_templates import BillingEmailTemplates
    from Backend.api.notifications.sendgrid_service import SendGridService
    from Backend.config import settings
    
    try:
        # Calculate trial days and end date if applicable
        trial_days = None
        trial_end_date = None
        if trial_end:
            trial_end_date = trial_end.date()
            if trial_start:
                trial_days = (trial_end - trial_start).days
        
        subject, html_body = BillingEmailTemplates.create_subscription_created_email(
            user_name=user_first_name or user_email.split('@')[0],
            plan_name=plan_name,
            amount=plan_amount,
            currency=plan_currency,
            trial_days=trial_days,
            trial_end_date=trial_end_date,
            frontend_url=settings.FRONTEND_URL or "https://app.brikli.com"
        )
        
        email_sent = await SendGridService.send_raw_email(
            to_email=user_email,
            to_name=f"{user_first_name or ''} {user_last_name or ''}".strip() or user_email,
            subject=subject,
            html_content=html_body,
            metadata={
                'email_type': 'subscription_created',
                'subscription_id': subscription_id,
                'event_id': event_id
            }
        )
        
        if email_sent:
            logger.info(f"[BG] Welcome email sent to {user_email}")
        else:
            logger.warning(f"[BG] Failed to send welcome email to {user_email}")
            
    except Exception as e:
        logger.error(f"[BG] Error sending welcome email: {e}", exc_info=True)


async def send_payment_succeeded_email(
    user_email: str,
    user_first_name: str | None,
    user_last_name: str | None,
    plan_name: str,
    amount_paid: float,
    currency: str,
    invoice_id: str,
    invoice_pdf_url: str,
    next_payment_date: datetime | None,
    subscription_id: str,
    stripe_invoice_id: str,
    event_id: str
):
    """Background task: Send payment succeeded email"""
    from Backend.api.billing.email_templates import BillingEmailTemplates
    from Backend.api.notifications.sendgrid_service import SendGridService
    from Backend.config import settings
    
    try:
        subject, html_body = BillingEmailTemplates.create_payment_succeeded_email(
            user_name=user_first_name or user_email.split('@')[0],
            amount=amount_paid,
            currency=currency,
            invoice_id=invoice_id,
            invoice_pdf_url=invoice_pdf_url,
            plan_name=plan_name,
            next_payment_date=next_payment_date.date() if next_payment_date else None,
            frontend_url=settings.FRONTEND_URL or "https://app.brikli.com"
        )
        
        email_sent = await SendGridService.send_raw_email(
            to_email=user_email,
            to_name=f"{user_first_name or ''} {user_last_name or ''}".strip() or user_email,
            subject=subject,
            html_content=html_body,
            metadata={
                'email_type': 'payment_succeeded',
                'subscription_id': subscription_id,
                'invoice_id': stripe_invoice_id,
                'event_id': event_id
            }
        )
        
        if email_sent:
            logger.info(f"[BG] Payment success email sent to {user_email}")
        else:
            logger.warning(f"[BG] Failed to send payment success email to {user_email}")
            
    except Exception as e:
        logger.error(f"[BG] Error sending payment success email: {e}", exc_info=True)


async def send_payment_failed_email(
    user_email: str,
    user_first_name: str | None,
    user_last_name: str | None,
    plan_name: str,
    amount_due: float,
    currency: str,
    attempt_count: int,
    invoice_url: str,
    subscription_id: str,
    stripe_invoice_id: str,
    event_id: str
):
    """Background task: Send payment failed email"""
    from Backend.api.billing.email_templates import BillingEmailTemplates
    from Backend.api.notifications.sendgrid_service import SendGridService
    from Backend.config import settings
    
    try:
        if not invoice_url:
            invoice_url = f"{settings.FRONTEND_URL or 'https://app.brikli.com'}/settings?tab=billing"
        
        subject, html_body = BillingEmailTemplates.create_payment_failed_email(
            user_name=user_first_name or user_email.split('@')[0],
            amount=amount_due,
            currency=currency,
            plan_name=plan_name,
            attempt_count=attempt_count,
            invoice_url=invoice_url,
            frontend_url=settings.FRONTEND_URL or "https://app.brikli.com"
        )
        
        email_sent = await SendGridService.send_raw_email(
            to_email=user_email,
            to_name=f"{user_first_name or ''} {user_last_name or ''}".strip() or user_email,
            subject=subject,
            html_content=html_body,
            metadata={
                'email_type': 'payment_failed',
                'subscription_id': subscription_id,
                'invoice_id': stripe_invoice_id,
                'event_id': event_id
            }
        )
        
        if email_sent:
            logger.info(f"[BG] Payment failed email sent to {user_email}")
        else:
            logger.warning(f"[BG] Failed to send payment failed email to {user_email}")
            
    except Exception as e:
        logger.error(f"[BG] Error sending payment failed email: {e}", exc_info=True)


async def send_trial_ending_email(
    user_email: str,
    user_first_name: str | None,
    user_last_name: str | None,
    plan_name: str,
    plan_amount: float,
    plan_currency: str,
    days_remaining: int,
    subscription_id: str,
    event_id: str
):
    """Background task: Send trial ending email"""
    from Backend.api.billing.email_templates import BillingEmailTemplates
    from Backend.api.notifications.sendgrid_service import SendGridService
    from Backend.config import settings
    
    try:
        subject, html_body = BillingEmailTemplates.create_trial_ending_email(
            user_name=user_first_name or user_email.split('@')[0],
            days_remaining=days_remaining,
            plan_name=plan_name,
            amount=plan_amount,
            currency=plan_currency,
            frontend_url=settings.FRONTEND_URL or "https://app.brikli.com"
        )
        
        email_sent = await SendGridService.send_raw_email(
            to_email=user_email,
            to_name=f"{user_first_name or ''} {user_last_name or ''}".strip() or user_email,
            subject=subject,
            html_content=html_body,
            metadata={
                'email_type': 'trial_ending',
                'subscription_id': subscription_id,
                'event_id': event_id
            }
        )
        
        if email_sent:
            logger.info(f"[BG] Trial ending email sent to {user_email}")
        else:
            logger.warning(f"[BG] Failed to send trial ending email to {user_email}")
            
    except Exception as e:
        logger.error(f"[BG] Error sending trial ending email: {e}", exc_info=True)


async def log_billing_audit_background(
    action: str,
    actor: str,
    user_id: str | None = None,
    subscription_id: str | None = None,
    description: str | None = None,
    audit_metadata: dict | None = None,
    amount: float | None = None,
    currency: str | None = None,
    stripe_event_id: str | None = None
):
    """Background task: Log billing audit event"""
    from Backend.database import get_session
    
    try:
        async for session in get_session():
            await log_billing_audit(
                action=action,
                actor=actor,
                session=session,
                user_id=user_id,
                subscription_id=subscription_id,
                description=description,
                audit_metadata=audit_metadata,
                amount=amount,
                currency=currency,
                stripe_event_id=stripe_event_id
            )
            logger.info(f"[BG] Audit log created: {action}")
            break
    except Exception as e:
        logger.error(f"[BG] Error creating audit log: {e}", exc_info=True)

