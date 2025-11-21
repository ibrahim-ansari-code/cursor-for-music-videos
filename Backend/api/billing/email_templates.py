"""
Billing Email Templates

Professional email templates for billing notifications
using the Brikli brand design system.
"""
from typing import Optional
from datetime import date

from Backend.api.notifications.email_templates import (
    BrikliEmailTemplate,
    EmailSection,
    EmailNotice,
    EmailCTA,
    EmailMetadataRow
)

class BillingEmailTemplates:
    """Email templates for billing notifications"""
    
    @staticmethod
    def create_payment_succeeded_email(
        user_name: str,
        amount: float,
        currency: str,
        invoice_id: str,
        invoice_pdf_url: str,
        plan_name: str,
        next_payment_date: Optional[date],
        frontend_url: str
    ) -> tuple[str, str]:
        """
        Generate email for successful payment.
        
        Returns:
            tuple: (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hi there,"
        formatted_amount = f"${amount:.2f} {currency.upper()}"
        
        sections = [
            EmailSection(
                text=f"Your payment of {formatted_amount} for {plan_name} was successful."
            ),
            EmailSection(
                text="Thank you for your continued business!"
            )
        ]
        
        metadata = [
            EmailMetadataRow(label="Amount Paid", value=formatted_amount, emoji="💰"),
            EmailMetadataRow(label="Invoice #", value=invoice_id, emoji="📄"),
            EmailMetadataRow(label="Plan", value=plan_name, emoji="⭐"),
        ]
        
        if next_payment_date:
            metadata.append(
                EmailMetadataRow(
                    label="Next Payment", 
                    value=next_payment_date.strftime("%B %d, %Y"), 
                    emoji="📅"
                )
            )
            
        cta = EmailCTA(
            text="Download Invoice",
            url=invoice_pdf_url
        )
        
        subject = f"Payment Receipt - {formatted_amount}"
        html_body = BrikliEmailTemplate.create_email(
            title="Payment Successful",
            greeting=greeting,
            sections=sections,
            metadata=metadata,
            cta=cta,
            footer_note="You can manage your subscription and payment methods in your account settings."
        )
        
        return subject, html_body
    
    @staticmethod
    def create_trial_ending_email(
        user_name: str,
        days_remaining: int,
        plan_name: str,
        amount: float,
        currency: str,
        frontend_url: str
    ) -> tuple[str, str]:
        """
        Generate email for trial ending reminder (3 days before).
        
        Returns:
            tuple: (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hi there,"
        formatted_amount = f"${amount:.2f} {currency.upper()}"
        
        sections = [
            EmailSection(
                text=f"Your {plan_name} trial will end in {days_remaining} days."
            ),
            EmailSection(
                text=f"After your trial ends, you'll be charged {formatted_amount}/month to continue using Brikli."
            ),
            EmailSection(
                text="To avoid any interruption, please ensure your payment method is up to date."
            )
        ]
        
        metadata = [
            EmailMetadataRow(label="Trial Ends In", value=f"{days_remaining} days", emoji="⏰"),
            EmailMetadataRow(label="Plan", value=plan_name, emoji="⭐"),
            EmailMetadataRow(label="Price", value=f"{formatted_amount}/month", emoji="💰"),
        ]
        
        notice = EmailNotice(
            emoji="ℹ️",
            title="What happens next?",
            message=f"On your trial end date, we'll automatically charge {formatted_amount} to your payment method. You can cancel anytime before then to avoid being charged.",
            color="#3b82f6",  # blue
            bg_color="#eff6ff"
        )
        
        billing_url = f"{frontend_url}/settings?tab=billing"
        cta = EmailCTA(
            text="Manage Subscription",
            url=billing_url
        )
        
        subject = f"Your Brikli Trial Ends in {days_remaining} Days"
        html_body = BrikliEmailTemplate.create_email(
            title="Trial Ending Soon",
            greeting=greeting,
            sections=sections,
            metadata=metadata,
            notice=notice,
            cta=cta,
            footer_note="Questions? Contact support@brikli.com anytime."
        )
        
        return subject, html_body
    
    @staticmethod
    def create_payment_failed_email(
        user_name: str,
        amount: float,
        currency: str,
        plan_name: str,
        attempt_count: int,
        invoice_url: str,
        frontend_url: str
    ) -> tuple[str, str]:
        """
        Generate email for failed payment notification.
        
        Returns:
            tuple: (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hi there,"
        formatted_amount = f"${amount:.2f} {currency.upper()}"
        
        sections = [
            EmailSection(
                text=f"We were unable to process your payment of {formatted_amount} for {plan_name}.",
                is_bold=True
            ),
            EmailSection(
                text="To avoid service interruption, please update your payment method or retry the payment."
            )
        ]
        
        metadata = [
            EmailMetadataRow(label="Amount Due", value=formatted_amount, emoji="💰"),
            EmailMetadataRow(label="Plan", value=plan_name, emoji="⭐"),
            EmailMetadataRow(label="Attempt", value=f"#{attempt_count}", emoji="🔄"),
        ]
        
        notice = EmailNotice(
            emoji="⚠️",
            title="Action Required",
            message="Your subscription will be canceled if payment cannot be processed. Please update your payment information to maintain access.",
            color="#dc2626",  # red
            bg_color="#fee2e2"
        )
        
        billing_url = f"{frontend_url}/settings?tab=billing"
        cta = EmailCTA(
            text="Update Payment Method",
            url=billing_url
        )
        
        subject = f"Payment Failed - Action Required"
        html_body = BrikliEmailTemplate.create_email(
            title="Payment Failed",
            greeting=greeting,
            sections=sections,
            metadata=metadata,
            notice=notice,
            cta=cta,
            footer_note="If you believe this is an error, please contact support@brikli.com."
        )
        
        return subject, html_body
    
    @staticmethod
    def create_subscription_created_email(
        user_name: str,
        plan_name: str,
        amount: float,
        currency: str,
        trial_days: Optional[int],
        trial_end_date: Optional[date],
        frontend_url: str
    ) -> tuple[str, str]:
        """
        Generate welcome email for new subscription.
        
        Returns:
            tuple: (subject, html_body)
        """
        greeting = f"Hi {user_name}," if user_name else "Hi there,"
        formatted_amount = f"${amount:.2f} {currency.upper()}"
        
        sections = [
            EmailSection(
                text=f"Welcome to {plan_name}! Your subscription is now active."
            ),
        ]
        
        metadata = [
            EmailMetadataRow(label="Plan", value=plan_name, emoji="⭐"),
            EmailMetadataRow(label="Price", value=f"{formatted_amount}/month", emoji="💰"),
        ]
        
        notice = None
        if trial_days and trial_end_date:
            sections.append(
                EmailSection(
                    text=f"You have {trial_days} days of free trial. Your first payment will be on {trial_end_date.strftime('%B %d, %Y')}."
                )
            )
            metadata.append(
                EmailMetadataRow(
                    label="Trial Period", 
                    value=f"{trial_days} days free", 
                    emoji="🎁"
                )
            )
            metadata.append(
                EmailMetadataRow(
                    label="First Payment", 
                    value=trial_end_date.strftime("%B %d, %Y"), 
                    emoji="📅"
                )
            )
            notice = EmailNotice(
                emoji="🎉",
                title="Free Trial Active",
                message=f"Enjoy {trial_days} days of full access to Brikli at no charge. Cancel anytime before {trial_end_date.strftime('%B %d, %Y')} to avoid being charged.",
                color="#10b981",  # green
                bg_color="#ecfdf5"
            )
        else:
            sections.append(
                EmailSection(
                    text="You now have full access to all Brikli features!"
                )
            )
        
        sections.append(
            EmailSection(
                text="Manage your properties, tenants, and finances all in one place."
            )
        )
        
        dashboard_url = f"{frontend_url}/dashboard"
        cta = EmailCTA(
            text="Go to Dashboard",
            url=dashboard_url
        )
        
        subject = f"Welcome to {plan_name}!"
        html_body = BrikliEmailTemplate.create_email(
            title="Subscription Activated",
            greeting=greeting,
            sections=sections,
            metadata=metadata,
            notice=notice,
            cta=cta,
            footer_note="Need help getting started? Visit our help center or contact support@brikli.com."
        )
        
        return subject, html_body

