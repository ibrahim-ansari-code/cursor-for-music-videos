"""
Autopay Service for Rent Payments

Handles automated recurring rent payments including:
- Finding and processing due enrollments
- Creating Stripe PaymentIntents
- Retry logic for failed payments
- Email notifications
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

import stripe
import sentry_sdk
from dateutil.relativedelta import relativedelta
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from Backend.api.stripe.client import get_stripe_client
from Backend.config import settings
from Backend.models.lease import Lease
from Backend.models.property import Property
from Backend.models.rent_autopay_enrollment import RentAutopayEnrollment
from Backend.models.rent_payment_transaction import RentPaymentTransaction
from Backend.models.stripe_connected_account import StripeConnectedAccount
from Backend.models.tenant_payment_method import TenantPaymentMethod
from Backend.models.tenant import Tenant
from Backend.models.user import User

logger = logging.getLogger(__name__)


class AutopayService:
    """Service for processing automated rent payments"""

    # Retry schedule: 1 day, 3 days, 7 days after initial failure
    RETRY_INTERVALS = [1, 3, 7]
    MAX_RETRIES = len(RETRY_INTERVALS)
    
    # Days before due date to process autopay
    AUTOPAY_DAYS_BEFORE_DUE = 1

    @staticmethod
    async def process_daily_autopay(session: AsyncSession) -> Dict[str, Any]:
        """
        Main entry point for daily autopay processing.
        Called by Supabase cron job via internal API endpoint.

        Returns:
            Dict[str, Any]: Summary of processing results
        """
        logger.info("🔄 Starting daily autopay processing")

        today = datetime.now(timezone.utc).date()
        results: Dict[str, Any] = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        try:
            # Find all enrollments that are due for payment today
            due_enrollments = await AutopayService._find_due_enrollments(
                session, today
            )
            logger.info(f"📋 Found {len(due_enrollments)} enrollments due for processing")

            for enrollment in due_enrollments:
                try:
                    success = await AutopayService._process_single_enrollment(
                        enrollment, session
                    )
                    results["processed"] += 1

                    if success:
                        results["successful"] += 1
                    else:
                        results["failed"] += 1

                except Exception as e:
                    logger.error(
                        f"❌ Error processing enrollment {enrollment.id}: {str(e)}",
                        exc_info=True,
                    )
                    results["errors"].append(
                        {
                            "enrollment_id": str(enrollment.id),
                            "error": str(e),
                        }
                    )
                    results["failed"] += 1

            await session.commit()
            logger.info(
                f"✅ Autopay processing complete: {results['successful']} successful, "
                f"{results['failed']} failed, {results['skipped']} skipped"
            )

        except Exception as e:
            logger.error(f"❌ Fatal error in autopay processing: {str(e)}", exc_info=True)
            results["errors"].append({"fatal": str(e)})
            await session.rollback()

        return results

    @staticmethod
    async def _find_due_enrollments(
        session: AsyncSession, today: date
    ) -> list[RentAutopayEnrollment]:
        """
        Find all active autopay enrollments that are due for payment.

        An enrollment is due if:
        - is_active is True
        - next_scheduled_at is today or earlier
        """
        result = await session.exec(
            select(RentAutopayEnrollment)
            .where(col(RentAutopayEnrollment.is_active) == True)
            .where(col(RentAutopayEnrollment.next_scheduled_at) <= today)
        )
        return list(result.all())

    @staticmethod
    async def _process_single_enrollment(
        enrollment: RentAutopayEnrollment, session: AsyncSession
    ) -> bool:
        """
        Process a single autopay enrollment.

        Returns:
            bool: True if payment successful, False otherwise
        """
        logger.info(f"💳 Processing autopay for enrollment {enrollment.id}")

        try:
            # Load lease with property eagerly loaded
            lease_result = await session.exec(
                select(Lease)
                .options(selectinload(getattr(Lease, "property")))
                .where(col(Lease.id) == enrollment.lease_id)
            )
            lease = lease_result.first()

            if not lease or not lease.property:
                logger.error(f"Lease {enrollment.lease_id} or property not found for enrollment {enrollment.id}")
                await AutopayService._pause_enrollment(
                    enrollment, session, "Lease or property not found"
                )
                return False

            # Load tenant with user relationship
            tenant_result = await session.exec(
                select(Tenant)
                .options(selectinload(getattr(Tenant, "user")))
                .where(col(Tenant.id) == lease.tenant_id)
            )
            tenant = tenant_result.first()

            if not tenant:
                logger.error(f"Tenant {lease.tenant_id} not found for enrollment {enrollment.id}")
                await AutopayService._pause_enrollment(
                    enrollment, session, "Tenant not found"
                )
                return False

            # Load payment method
            pm_result = await session.exec(
                select(TenantPaymentMethod).where(
                    col(TenantPaymentMethod.id) == enrollment.payment_method_id
                )
            )
            payment_method = pm_result.first()

            if not payment_method:
                logger.error(
                    f"Payment method {enrollment.payment_method_id} not found for enrollment {enrollment.id}"
                )
                await AutopayService._pause_enrollment(
                    enrollment, session, "Payment method not found"
                )
                return False

            # Get landlord_id from property
            landlord_user_id = str(lease.property.user_id)

            # Load connected account
            account_result = await session.exec(
                select(StripeConnectedAccount).where(
                    col(StripeConnectedAccount.user_id) == lease.property.user_id
                )
            )
            connected_account = account_result.first()

            if not connected_account:
                logger.error(
                    f"Connected account not found for landlord {landlord_user_id}"
                )
                await AutopayService._pause_enrollment(
                    enrollment, session, "Connected account not found"
                )
                return False

            # Validate connected account is active
            if connected_account.onboarding_status != "complete":
                logger.error(
                    f"Connected account {connected_account.id} is not active (status: {connected_account.onboarding_status})"
                )
                await AutopayService._pause_enrollment(
                    enrollment,
                    session,
                    "Landlord's payment account is not active",
                )
                return False

            # Create and confirm the payment
            payment_intent = await AutopayService._create_autopay_payment(
                lease=lease,
                tenant=tenant,
                payment_method=payment_method,
                connected_account=connected_account,
                enrollment=enrollment,
                landlord_user_id=landlord_user_id,
                session=session,
            )

            if payment_intent:
                # Payment successful - update enrollment
                enrollment.last_success_at = datetime.now(timezone.utc)
                enrollment.last_attempt_at = datetime.now(timezone.utc)
                enrollment.current_retry_count = 0
                enrollment.last_failure_reason = None

                # Schedule next payment with proper month-end handling
                rent_due_day = lease.rent_due_day or 1
                next_autopay_date = AutopayService._calculate_next_autopay_date(
                    rent_due_day=rent_due_day,
                    from_date=datetime.now(timezone.utc).date()
                )
                enrollment.next_scheduled_at = next_autopay_date

                session.add(enrollment)
                await session.flush()

                # Send success notification
                await AutopayService._send_success_notification(
                    tenant, lease, payment_intent
                )

                logger.info(
                    f"✅ Autopay successful for enrollment {enrollment.id}, "
                    f"next payment scheduled for {next_autopay_date.strftime('%Y-%m-%d')}"
                )
                return True
            else:
                # Payment failed - handle retry logic
                await AutopayService._handle_payment_failure(
                    enrollment, tenant, lease, session, "Payment failed"
                )
                return False

        except Exception as e:
            logger.error(
                f"❌ Error processing enrollment {enrollment.id}: {str(e)}",
                exc_info=True,
            )
            # Try to load tenant/lease if not already loaded
            try:
                if 'tenant' not in locals():
                    tenant_result = await session.exec(
                        select(Tenant).where(col(Tenant.id) == enrollment.tenant_id)
                    )
                    tenant = tenant_result.first()
                if 'lease' not in locals():
                    lease_result = await session.exec(
                        select(Lease).where(col(Lease.id) == enrollment.lease_id)
                    )
                    lease = lease_result.first()
            except:
                tenant = None
                lease = None
            
            await AutopayService._handle_payment_failure(
                enrollment, tenant, lease, session, f"Error: {str(e)}"
            )
            return False

    @staticmethod
    async def _create_autopay_payment(
        lease: Lease,
        tenant: Tenant,
        payment_method: TenantPaymentMethod,
        connected_account: StripeConnectedAccount,
        enrollment: RentAutopayEnrollment,
        landlord_user_id: str,
        session: AsyncSession,
    ) -> Optional[stripe.PaymentIntent]:
        """
        Create and confirm a Stripe PaymentIntent for autopay.

        Returns:
            Optional[stripe.PaymentIntent]: PaymentIntent if successful, None if failed
        """
        try:
            # Use the amount from the enrollment, which could be custom
            amount_cents = enrollment.amount_cents

            # Calculate flat platform fee based on payment method
            from Backend.api.rent_payments.constants import calculate_application_fee_cents
            platform_fee_cents = calculate_application_fee_cents(
                amount_cents,
                payment_method.payment_method_type
            )

            # Build payment description
            from Backend.models.enums import TenantType
            
            if tenant.tenant_type == TenantType.COMPANY and tenant.company_name:
                tenant_name = tenant.company_name
            elif tenant.first_name and tenant.last_name:
                tenant_name = f"{tenant.first_name} {tenant.last_name}"
            else:
                tenant_name = f"Tenant #{tenant.id}"

            description = f"Autopay - Monthly rent for {tenant_name}"

            # Get Stripe client
            stripe_client = get_stripe_client()
            
            # Generate idempotency key to prevent duplicate autopay charges
            # Stable for the entire day to allow retries
            scheduled_date = enrollment.next_scheduled_at.strftime("%Y%m%d") if enrollment.next_scheduled_at else datetime.now(timezone.utc).strftime("%Y%m%d")
            idempotency_key = f"autopay-{enrollment.id}-{scheduled_date}"
            
            # Create PaymentIntent
            pi_params = {
                "amount": amount_cents,
                "currency": "cad",
                "payment_method": payment_method.stripe_payment_method_id,
                "description": description,
                "application_fee_amount": platform_fee_cents,
                "confirm": True,
                "off_session": True,  # Important for autopay
                "payment_method_types": ["card", "acss_debit"],
                "metadata": {
                    "lease_id": str(lease.id),
                    "tenant_id": str(tenant.id),
                    "landlord_id": landlord_user_id,
                    "property_id": str(lease.property_id),
                    "enrollment_id": str(enrollment.id),
                    "payment_type": "autopay",
                },
                "stripe_account": connected_account.stripe_account_id,
                "idempotency_key": idempotency_key,
            }
            
            # For PAD, include mandate data
            pi_params["payment_method_options"] = {
                "acss_debit": {
                    "mandate_options": {
                        "payment_schedule": "sporadic",
                        "transaction_type": "personal",
                    },
                    "verification_method": "automatic",
                }
            }
            
            payment_intent = await stripe_client.payment_intents.create(**pi_params)

            logger.info(
                f"💰 Created autopay PaymentIntent {payment_intent.id} "
                f"for ${amount_cents / 100:.2f} CAD"
            )

            # Create transaction record
            from uuid import UUID
            from Backend.models.rent_payment_transaction import RentPaymentTransactionStatus
            
            transaction = RentPaymentTransaction(
                lease_id=lease.id,
                tenant_id=tenant.id,
                landlord_user_id=UUID(landlord_user_id),
                connected_account_id=connected_account.id,
                amount_cents=amount_cents,
                application_fee_cents=platform_fee_cents,
                currency="cad",
                stripe_payment_intent_id=payment_intent.id,
                status=RentPaymentTransactionStatus.SUCCEEDED,
                payment_method_type=payment_method.payment_method_type,
                metadata={
                    "enrollment_id": str(enrollment.id),
                    "payment_type": "autopay",
                },
            )
            session.add(transaction)
            await session.flush()

            return payment_intent

        except stripe.CardError as e:
            # Card was declined
            logger.error(f"💳 Card declined for autopay: {e.user_message}")
            
            # Track in Sentry for monitoring failure rates by decline code
            sentry_sdk.capture_message(
                f"Autopay Card Declined: {e.code or 'unknown'}",
                level="warning",
                tags={
                    "component": "autopay_payment",
                    "failure_type": "card_declined",
                    "decline_code": e.code or "unknown",
                    "enrollment_id": str(enrollment.id),
                    "payment_method_type": payment_method.payment_method_type,
                },
                contexts={
                    "autopay": {
                        "enrollment_id": str(enrollment.id),
                        "lease_id": str(lease.id),
                        "tenant_id": str(tenant.id),
                        "amount": amount_cents / 100,
                        "decline_code": e.code,
                        "user_message": e.user_message,
                    }
                },
            )
            return None
            
        except stripe.StripeError as e:
            # Other Stripe errors
            logger.error(f"❌ Stripe error during autopay: {str(e)}")
            
            # Track in Sentry
            sentry_sdk.capture_exception(
                e,
                tags={
                    "component": "autopay_payment",
                    "failure_type": "stripe_error",
                    "enrollment_id": str(enrollment.id),
                },
                contexts={
                    "autopay": {
                        "enrollment_id": str(enrollment.id),
                        "lease_id": str(lease.id),
                        "tenant_id": str(tenant.id),
                        "amount": amount_cents / 100,
                    }
                },
            )
            return None
            
        except Exception as e:
            logger.error(f"❌ Unexpected error creating autopay payment: {str(e)}")
            
            # Track unexpected errors
            sentry_sdk.capture_exception(
                e,
                tags={
                    "component": "autopay_payment",
                    "failure_type": "unexpected",
                    "enrollment_id": str(enrollment.id),
                },
                contexts={
                    "autopay": {
                        "enrollment_id": str(enrollment.id),
                        "lease_id": str(lease.id),
                        "tenant_id": str(tenant.id),
                        "amount": amount_cents / 100,
                    }
                },
            )
            return None

    @staticmethod
    async def _handle_payment_failure(
        enrollment: RentAutopayEnrollment,
        tenant: Optional[Tenant],
        lease: Optional[Lease],
        session: AsyncSession,
        failure_reason: str,
    ) -> None:
        """
        Handle a failed autopay attempt with retry logic.

        Retry schedule: 1, 3, 7 days after initial failure
        After max retries, pause the enrollment and notify tenant
        """
        enrollment.last_attempt_at = datetime.now(timezone.utc)
        enrollment.last_failure_reason = failure_reason
        enrollment.current_retry_count += 1

        logger.warning(
            f"⚠️ Autopay failed for enrollment {enrollment.id} "
            f"(attempt {enrollment.current_retry_count}/{AutopayService.MAX_RETRIES}): "
            f"{failure_reason}"
        )

        if enrollment.current_retry_count < AutopayService.MAX_RETRIES:
            # Schedule retry
            retry_days = AutopayService.RETRY_INTERVALS[
                enrollment.current_retry_count - 1
            ]
            # Calculate next retry date as datetime
            next_retry_date = datetime.now(timezone.utc) + timedelta(days=retry_days)
            enrollment.next_scheduled_at = next_retry_date
            session.add(enrollment)

            logger.info(
                f"📅 Scheduled retry for enrollment {enrollment.id} in {retry_days} days"
            )

            # Send failure notification with retry info
            if tenant and lease:
                await AutopayService._send_failure_notification(
                    enrollment, tenant, lease, failure_reason, retry_days
                )
        else:
            # Max retries reached - pause enrollment
            await AutopayService._pause_enrollment(
                enrollment,
                session,
                f"Max retries ({AutopayService.MAX_RETRIES}) exceeded",
            )

            # Send final failure notification
            if tenant and lease:
                await AutopayService._send_failure_notification(
                    enrollment, tenant, lease, failure_reason, None
                )

    @staticmethod
    async def _pause_enrollment(
        enrollment: RentAutopayEnrollment,
        session: AsyncSession,
        reason: str,
    ) -> None:
        """Pause an enrollment due to failure or missing data"""
        enrollment.is_active = False
        enrollment.paused_at = datetime.now(timezone.utc)
        enrollment.last_failure_reason = reason
        session.add(enrollment)

        logger.warning(
            f"⏸️ Paused enrollment {enrollment.id}: {reason}"
        )

    @staticmethod
    async def _send_success_notification(
        tenant: Tenant,
        lease: Lease,
        payment_intent: stripe.PaymentIntent,
    ) -> None:
        """
        Send email notification for successful autopay.
        
        Sends a confirmation email to the tenant with payment details
        and receipt information.
        """
        try:
            from Backend.api.notifications.email_templates import (
                BrikliEmailTemplate,
                EmailSection,
                EmailMetadataRow,
                EmailCTA,
            )
            from Backend.api.notifications.sendgrid_service import SendGridService
            from Backend.models.enums import TenantType
            
            # Get tenant email
            tenant_email = tenant.email
            if not tenant_email and tenant.user:
                tenant_email = tenant.user.email
            
            if not tenant_email:
                logger.warning(
                    f"Cannot send autopay success email to tenant {tenant.id}: no email address"
                )
                return
            
            # Build tenant display name
            if tenant.tenant_type == TenantType.COMPANY and tenant.company_name:
                tenant_name = tenant.company_name
            elif tenant.first_name and tenant.last_name:
                tenant_name = f"{tenant.first_name} {tenant.last_name}"
            else:
                tenant_name = "there"
            
            # Format payment amount
            amount_dollars = payment_intent.amount / 100
            amount_formatted = f"${amount_dollars:,.2f}"
            
            # Format payment date
            from datetime import datetime, timezone
            payment_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
            
            # Get property address
            property_address = "your property"
            if lease.property:
                property_address = lease.property.address or property_address
            
            # Build email content
            sections = [
                EmailSection(
                    text=f"Hi {tenant_name},",
                    is_bold=False
                ),
                EmailSection(
                    text=f"Your rent payment of {amount_formatted} CAD has been successfully processed!",
                    is_bold=False
                ),
                EmailSection(
                    text="Your autopay is working smoothly, and your rent has been paid automatically. No action is needed on your part.",
                    is_bold=False
                ),
            ]
            
            # Add payment details
            metadata = [
                EmailMetadataRow(
                    label="Amount Paid",
                    value=f"{amount_formatted} CAD",
                    emoji="💰"
                ),
                EmailMetadataRow(
                    label="Payment Date",
                    value=payment_date,
                    emoji="📅"
                ),
                EmailMetadataRow(
                    label="Property",
                    value=property_address,
                    emoji="🏠"
                ),
                EmailMetadataRow(
                    label="Payment Method",
                    value="Autopay",
                    emoji="🔄"
                ),
                EmailMetadataRow(
                    label="Transaction ID",
                    value=payment_intent.id,
                    emoji="🔖"
                ),
            ]
            
            # Build HTML email
            html_content = BrikliEmailTemplate.create_email(
                title="Rent Payment Successful",
                greeting="",  # Already included in sections
                sections=sections,
                metadata=metadata,
                cta=EmailCTA(
                    text="View Payment History",
                    url=f"{settings.TENANT_FRONTEND_URL}/payments"
                ) if hasattr(settings, 'TENANT_FRONTEND_URL') else None,
                footer_note="Your next autopay payment will be processed automatically on the scheduled date. Thank you for using Brikli!"
            )
            
            # Send email
            await SendGridService.send_raw_email(
                to_email=tenant_email,
                to_name=tenant_name,
                subject=f"✅ Rent Payment Successful - {amount_formatted}",
                html_content=html_content,
            )
            
            logger.info(
                f"📧 Sent autopay success email to {tenant_email} "
                f"for payment {payment_intent.id}"
            )
            
        except Exception as e:
            # Don't fail the autopay if email fails
            logger.error(
                f"Failed to send autopay success email to tenant {tenant.id}: {str(e)}",
                exc_info=True
            )

    @staticmethod
    def _calculate_next_autopay_date(
        rent_due_day: int,
        from_date: date,
    ) -> datetime:
        """
        Calculate the next autopay date with proper month-end handling.
        
        Autopay is processed 1 day before the rent due date.
        Handles month-end dates correctly (e.g., due on 31st in February becomes 28th/29th).
        
        Args:
            rent_due_day: Day of month rent is due (1-31)
            from_date: Calculate from this date (typically today)
            
        Returns:
            Next autopay datetime (1 day before due date)
            
        Examples:
            - Due on 15th, today is 10th → next autopay is 14th of this month
            - Due on 15th, today is 20th → next autopay is 14th of next month
            - Due on 31st, next month is Feb → next autopay is 27th/28th Feb (29th in leap years)
        """
        # Ensure rent_due_day is valid (1-31)
        rent_due_day = max(1, min(31, rent_due_day))
        
        # Start with current month
        year = from_date.year
        month = from_date.month
        
        # Calculate due date for current month
        # Use min() to handle months with fewer days (e.g., Feb 31 → Feb 28/29)
        from calendar import monthrange
        last_day_of_month = monthrange(year, month)[1]
        actual_due_day = min(rent_due_day, last_day_of_month)
        
        current_month_due_date = date(year, month, actual_due_day)
        
        # Calculate autopay processing date (1 day before due)
        current_month_autopay_date = current_month_due_date - timedelta(days=AutopayService.AUTOPAY_DAYS_BEFORE_DUE)
        
        # If we haven't passed the autopay date yet this month, use it
        if from_date <= current_month_autopay_date:
            next_autopay_date = current_month_autopay_date
        else:
            # Move to next month
            next_month = from_date + relativedelta(months=1)
            
            # Handle month-end properly for next month
            next_month_last_day = monthrange(next_month.year, next_month.month)[1]
            next_month_actual_due_day = min(rent_due_day, next_month_last_day)
            
            next_month_due_date = date(next_month.year, next_month.month, next_month_actual_due_day)
            next_autopay_date = next_month_due_date - timedelta(days=AutopayService.AUTOPAY_DAYS_BEFORE_DUE)
        
        # Convert to datetime with timezone
        return datetime.combine(next_autopay_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
    
    @staticmethod
    async def _send_failure_notification(
        enrollment: RentAutopayEnrollment,
        tenant: Tenant,
        lease: Lease,
        failure_reason: str,
        retry_in_days: Optional[int],
    ) -> None:
        """
        Send email notification for failed autopay.
        
        Args:
            enrollment: The autopay enrollment
            tenant: The tenant
            lease: The lease
            failure_reason: Reason for the failure
            retry_in_days: Days until retry (None if final failure)
        """
        try:
            from Backend.api.notifications.email_templates import (
                BrikliEmailTemplate,
                EmailSection,
                EmailMetadataRow,
                EmailNotice,
                EmailCTA,
            )
            from Backend.api.notifications.sendgrid_service import SendGridService
            from Backend.models.enums import TenantType
            
            # Get tenant email
            tenant_email = tenant.email
            if not tenant_email and tenant.user:
                tenant_email = tenant.user.email
            
            if not tenant_email:
                logger.warning(
                    f"Cannot send autopay failure email to tenant {tenant.id}: no email address"
                )
                return
            
            # Build tenant display name
            if tenant.tenant_type == TenantType.COMPANY and tenant.company_name:
                tenant_name = tenant.company_name
            elif tenant.first_name and tenant.last_name:
                tenant_name = f"{tenant.first_name} {tenant.last_name}"
            else:
                tenant_name = "there"
            
            # Format rent amount
            amount_dollars = int(lease.monthly_rent * 100) / 100
            amount_formatted = f"${amount_dollars:,.2f}"
            
            # Get property address
            property_address = "your property"
            if lease.property:
                property_address = lease.property.address or property_address
            
            # Build email content based on retry status
            if retry_in_days:
                # Retry notification
                title = "Autopay Payment Needs Attention"
                
                sections = [
                    EmailSection(
                        text=f"Hi {tenant_name},",
                        is_bold=False
                    ),
                    EmailSection(
                        text=f"We were unable to process your automatic rent payment of {amount_formatted} CAD.",
                        is_bold=False
                    ),
                    EmailSection(
                        text=f"Don't worry - we'll automatically retry the payment in {retry_in_days} day{'s' if retry_in_days != 1 else ''}.",
                        is_bold=False
                    ),
                    EmailSection(
                        text="If you'd like to update your payment method or make a manual payment, you can do so through your tenant portal.",
                        is_bold=False
                    ),
                ]
                
                notice = EmailNotice(
                    emoji="⚠️",
                    title="Payment Issue",
                    message=f"Reason: {failure_reason}",
                    color="#f59e0b",  # amber
                    bg_color="#fff7ed"
                )
                
                footer_note = f"We'll try again in {retry_in_days} days. If the issue persists, please update your payment method to avoid service interruption."
                
            else:
                # Final failure - autopay paused
                title = "Autopay Paused - Action Required"
                
                sections = [
                    EmailSection(
                        text=f"Hi {tenant_name},",
                        is_bold=False
                    ),
                    EmailSection(
                        text=f"After multiple attempts, we were unable to process your automatic rent payment of {amount_formatted} CAD.",
                        is_bold=True
                    ),
                    EmailSection(
                        text="Your autopay has been paused to prevent further failed attempts.",
                        is_bold=False
                    ),
                    EmailSection(
                        text="Please log in to your tenant portal to update your payment method and make a manual payment for your outstanding rent.",
                        is_bold=False
                    ),
                ]
                
                notice = EmailNotice(
                    emoji="🛑",
                    title="Autopay Paused",
                    message="Your automatic payments have been paused. Please update your payment method and make a manual payment.",
                    color="#dc2626",  # red
                    bg_color="#fee2e2"
                )
                
                footer_note = "You can reactivate autopay anytime after updating your payment method."
            
            # Add payment details
            metadata = [
                EmailMetadataRow(
                    label="Amount Due",
                    value=f"{amount_formatted} CAD",
                    emoji="💰"
                ),
                EmailMetadataRow(
                    label="Property",
                    value=property_address,
                    emoji="🏠"
                ),
                EmailMetadataRow(
                    label="Issue",
                    value=failure_reason,
                    emoji="❌"
                ),
            ]
            
            if retry_in_days:
                metadata.append(
                    EmailMetadataRow(
                        label="Next Retry",
                        value=f"In {retry_in_days} day{'s' if retry_in_days != 1 else ''}",
                        emoji="🔄"
                    )
                )
            
            # Build HTML email
            html_content = BrikliEmailTemplate.create_email(
                title=title,
                greeting="",  # Already included in sections
                sections=sections,
                metadata=metadata,
                notice=notice,
                cta=EmailCTA(
                    text="Go to Tenant Portal" if not retry_in_days else "Update Payment Method",
                    url=f"{settings.TENANT_FRONTEND_URL}/payments"
                ) if hasattr(settings, 'TENANT_FRONTEND_URL') else None,
                footer_note=footer_note
            )
            
            # Send email
            subject_prefix = "⚠️" if retry_in_days else "🛑"
            await SendGridService.send_raw_email(
                to_email=tenant_email,
                to_name=tenant_name,
                subject=f"{subject_prefix} Autopay Payment {'Issue' if retry_in_days else 'Paused'} - {amount_formatted}",
                html_content=html_content,
            )
            
            if retry_in_days:
                logger.info(
                    f"📧 Sent autopay retry notification to {tenant_email} "
                    f"for enrollment {enrollment.id} (retry in {retry_in_days} days)"
                )
            else:
                logger.info(
                    f"📧 Sent autopay final failure notification to {tenant_email} "
                    f"for enrollment {enrollment.id}"
                )
            
        except Exception as e:
            # Don't fail the autopay if email fails
            logger.error(
                f"Failed to send autopay failure email for enrollment {enrollment.id}: {str(e)}",
                exc_info=True
            )

