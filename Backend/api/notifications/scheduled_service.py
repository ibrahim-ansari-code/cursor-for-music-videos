"""
Scheduled Notification Service

Business logic for scheduled background jobs that create notifications.
These are called by pg_cron on a schedule (daily at 14:00 UTC / 9 AM EST).
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Any, cast
from sqlalchemy import select, and_, func, inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, QueryableAttribute
from sqlmodel import col

from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.user import User
from Backend.models.accounting.payment import Payment
from Backend.models.accounting.common import PaymentStatus
from Backend.api.notifications.service import NotificationService
from Backend.api.accounting.rent_tracker.schemas import RentStatus
from Backend.api.accounting.rent_tracker.helpers import determine_rent_status, calculate_month_bounds

logger = logging.getLogger(__name__)


class ScheduledNotificationService:
    """Service for scheduled notification jobs"""
    
    @staticmethod
    async def _calculate_lease_payments_for_month(
        session: AsyncSession,
        lease_id: int,
        target_month: int,
        target_year: int
    ) -> Decimal:
        """
        Calculate total payments for a lease in a specific month.
        
        Args:
            session: Database session
            lease_id: ID of the lease
            target_month: Month number (1-12)
            target_year: Year
            
        Returns:
            Total payment amount for the month
        """
        month_start, month_end = calculate_month_bounds(target_month, target_year)
        
        query = select(func.coalesce(func.sum(Payment.amount), Decimal("0.0"))).where(
            and_(
                col(Payment.lease_id) == lease_id,
                col(Payment.payment_date) >= month_start,
                col(Payment.payment_date) <= month_end,
                col(Payment.status).in_([PaymentStatus.PAID, PaymentStatus.PARTIAL])
            )
        )
        
        result = await session.execute(query)
        return result.scalar() or Decimal("0.0")
    
    @staticmethod
    async def send_rent_reminders(session: AsyncSession) -> Dict[str, Any]:
        """
        Find all active leases with rent due in 3 days and notify landlords.
        
        Logic:
        1. Get today's date
        2. Calculate target rent due day (3 days from now)
        3. Find all ACTIVE leases where rent_due_day matches target
        4. For each lease, create notification for property owner
        5. Send email via NotificationService
        
        Returns:
            Dict with success status, notifications_created count, and leases_processed count
        """
        today = date.today()
        target_date = today + timedelta(days=3)
        target_day = target_date.day
        
        logger.info(f"Starting rent reminder job for target date: {target_date} (day {target_day})")
        
        # Find active leases with rent due on target day (eager load property and owner)
        # Use getattr to access relationship attributes with proper typing
        property_rel = cast(QueryableAttribute[Any], getattr(Lease, 'property'))
        owner_rel = cast(QueryableAttribute[Any], getattr(Property, 'owner'))
        
        query = (
            select(Lease)
            .join(Property, col(Lease.property_id) == col(Property.id))
            .options(selectinload(property_rel).selectinload(owner_rel))
            .where(
                and_(
                    col(Lease.status) == LeaseStatus.ACTIVE,
                    col(Lease.rent_due_day) == target_day
                )
            )
        )
        
        result = await session.execute(query)
        leases = result.scalars().all()
        
        logger.info(f"Found {len(leases)} leases with rent due on day {target_day}")
        
        notifications_created = 0
        leases_skipped_paid = 0
        
        for lease in leases:
            try:
                # Property and owner are already loaded via selectinload
                property_obj = lease.property
                
                if not property_obj:
                    logger.warning(f"Property not found for lease {lease.id}")
                    continue
                
                landlord = property_obj.owner
                
                if not landlord:
                    logger.warning(f"Landlord not found for property {property_obj.id}")
                    continue
                
                # Ensure lease has an ID (should always be present for queried leases)
                if lease.id is None:
                    logger.warning("Lease missing ID, skipping")
                    continue
                
                # Assert for type checking - lease.id is guaranteed to be int after None check
                assert lease.id is not None, "Lease ID should not be None after check"
                lease_id: int = lease.id
                
                # Check if rent has already been paid for the target month
                amount_paid = await ScheduledNotificationService._calculate_lease_payments_for_month(
                    session=session,
                    lease_id=lease_id,
                    target_month=target_date.month,
                    target_year=target_date.year
                )
                
                # Determine rent payment status
                rent_status, _ = determine_rent_status(
                    monthly_rent=lease.monthly_rent,
                    amount_paid=amount_paid,
                    due_date=target_date,
                    current_date=today
                )
                
                # Skip notification if rent is already fully paid
                if rent_status == RentStatus.PAID:
                    leases_skipped_paid += 1
                    logger.info(
                        f"Skipping rent reminder for lease {lease.id} - "
                        f"rent for {target_date.strftime('%B %Y')} already paid "
                        f"(${amount_paid} of ${lease.monthly_rent})"
                    )
                    continue
                
                # Log payment status for partial payments
                if rent_status == RentStatus.PARTIAL:
                    logger.info(
                        f"Sending rent reminder for lease {lease.id} - "
                        f"partial payment received (${amount_paid} of ${lease.monthly_rent})"
                    )
                
                # Calculate remaining amount for message
                remaining_amount = lease.monthly_rent - amount_paid
                
                # Customize message based on payment status
                if rent_status == RentStatus.PARTIAL:
                    message = (
                        f'Rent payment for {property_obj.name} is due on {target_date.strftime("%B %d, %Y")}. '
                        f'${amount_paid} received, ${remaining_amount} remaining of ${lease.monthly_rent} total.'
                    )
                else:
                    message = f'Rent payment of ${lease.monthly_rent} is due on {target_date.strftime("%B %d, %Y")}.'
                
                # Create notification
                notification = await NotificationService.create_notification(
                    user_id=landlord.id,
                    type='rent_reminder',
                    title=f'Rent Due in 3 Days - {property_obj.name}',
                    message=message,
                    session=session,
                    link=f'/properties/{property_obj.id}',
                    priority='high',
                    metadata={
                        'lease_id': str(lease.id),
                        'property_id': str(property_obj.id),
                        'tenant_id': str(lease.tenant_id),
                        'amount': str(lease.monthly_rent),
                        'amount_paid': str(amount_paid),
                        'remaining_amount': str(remaining_amount),
                        'rent_status': rent_status.value,
                        'due_date': target_date.isoformat()
                    }
                )
                
                if notification:
                    notifications_created += 1
                    logger.info(f"Created rent reminder notification for lease {lease.id}")
                
            except Exception as e:
                logger.error(f"Failed to create rent reminder for lease {lease.id}: {e}", exc_info=True)
                continue
        
        await session.commit()
        
        result_data = {
            'success': True,
            'notifications_created': notifications_created,
            'leases_processed': len(leases),
            'leases_skipped_already_paid': leases_skipped_paid,
            'target_date': target_date.isoformat()
        }
        
        logger.info(f"Rent reminder job completed: {result_data}")
        return result_data
    
    @staticmethod
    async def send_lease_expiring_notifications(session: AsyncSession) -> Dict[str, Any]:
        """
        Find leases expiring in 30 or 60 days and notify landlords.
        
        Logic:
        1. Get today's date
        2. Calculate 30 days and 60 days from now
        3. Find ACTIVE leases expiring on those exact dates
        4. Create notifications for property owners
        
        Returns:
            Dict with success status, notifications_created count, and leases_processed count
        """
        today = date.today()
        date_30_days = today + timedelta(days=30)
        date_60_days = today + timedelta(days=60)
        
        logger.info(f"Starting lease expiring job for dates: {date_30_days} and {date_60_days}")
        
        # Find leases expiring in 30 or 60 days (eager load property and owner)
        # Use getattr to access relationship attributes with proper typing
        property_rel = cast(QueryableAttribute[Any], getattr(Lease, 'property'))
        owner_rel = cast(QueryableAttribute[Any], getattr(Property, 'owner'))
        
        query = (
            select(Lease)
            .options(selectinload(property_rel).selectinload(owner_rel))
            .where(
                and_(
                    col(Lease.status) == LeaseStatus.ACTIVE,
                    col(Lease.end_date).in_([date_30_days, date_60_days])
                )
            )
        )
        
        result = await session.execute(query)
        leases = result.scalars().all()
        
        logger.info(f"Found {len(leases)} leases expiring in 30 or 60 days")
        
        notifications_created = 0
        
        for lease in leases:
            try:
                # Property and owner are already loaded via selectinload
                property_obj = lease.property
                
                if not property_obj:
                    logger.warning(f"Property not found for lease {lease.id}")
                    continue
                
                landlord = property_obj.owner
                
                if not landlord:
                    logger.warning(f"Landlord not found for property {property_obj.id}")
                    continue
                
                # Determine days until expiry
                days_until = (lease.end_date - today).days
                
                # Create notification
                notification = await NotificationService.create_notification(
                    user_id=landlord.id,
                    type='lease_expiring',
                    title=f'Lease Expiring in {days_until} Days - {property_obj.name}',
                    message=f'The lease for {property_obj.name} expires on {lease.end_date.strftime("%B %d, %Y")}. Consider reaching out to the tenant for renewal.',
                    session=session,
                    link=f'/leases/{lease.id}',
                    priority='high' if days_until == 30 else 'normal',
                    metadata={
                        'lease_id': str(lease.id),
                        'property_id': str(property_obj.id),
                        'tenant_id': str(lease.tenant_id),
                        'end_date': lease.end_date.isoformat(),
                        'days_until_expiry': days_until
                    }
                )
                
                if notification:
                    notifications_created += 1
                    logger.info(f"Created lease expiring notification for lease {lease.id} ({days_until} days)")
                
            except Exception as e:
                logger.error(f"Failed to create lease expiring notification for lease {lease.id}: {e}", exc_info=True)
                continue
        
        await session.commit()
        
        result_data = {
            'success': True,
            'notifications_created': notifications_created,
            'leases_processed': len(leases),
            'check_dates': [date_30_days.isoformat(), date_60_days.isoformat()]
        }
        
        logger.info(f"Lease expiring job completed: {result_data}")
        return result_data
    
    @staticmethod
    async def send_reminder_notifications(session: AsyncSession) -> Dict[str, Any]:
        """
        Find custom reminders that need notifications and send them.
        
        Logic:
        1. Calculate notification window (next 15 minutes)
        2. Find reminders where (reminder_date - notify_before_hours) falls in window
        3. Create in-app and email notifications
        4. Mark as notified to prevent duplicates
        
        Returns:
            Dict with success status, notifications_created count, and reminders_processed count
        """
        from datetime import datetime, timezone
        from Backend.models.calendar import CustomReminder
        from Backend.models.property import Property
        
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(minutes=15)
        
        logger.info(f"Starting custom reminder notification job. Window: {now} to {window_end}")
        
        # Build query to find reminders needing notification
        # Formula: reminder_date - (notify_before_hours * 1 hour) should be between now and window_end
        # We need to find reminders where:
        #   - Not yet completed
        #   - Not yet notified
        #   - Notification time is within the next 15 minutes
        
        # Load relationships eagerly to avoid lazy loading issues
        user_rel = cast(QueryableAttribute[Any], getattr(CustomReminder, 'user'))
        property_rel = cast(QueryableAttribute[Any], getattr(CustomReminder, 'property'))
        
        query = (
            select(CustomReminder)
            .options(
                selectinload(user_rel),
                selectinload(property_rel)
            )
            .where(
                and_(
                    col(CustomReminder.is_completed) == False,
                    col(CustomReminder.notified_at).is_(None),
                    # Calculate notification time and check if it's in the window
                    # notification_time = reminder_date - (notify_before_hours * interval '1 hour')
                    func.date_trunc(
                        'minute',
                        col(CustomReminder.reminder_date) - 
                        (col(CustomReminder.notify_before_hours) * timedelta(hours=1))
                    ).between(now, window_end)
                )
            )
        )
        
        result = await session.execute(query)
        reminders = result.scalars().all()
        
        logger.info(f"Found {len(reminders)} reminders needing notification")
        
        notifications_created = 0
        
        for reminder in reminders:
            try:
                user = reminder.user
                
                if not user:
                    logger.warning(f"User not found for reminder {reminder.id}")
                    continue
                
                # Build notification title and message
                title = f"Reminder: {reminder.title}"
                
                # Calculate time until reminder
                time_until = reminder.reminder_date - now
                hours_until = int(time_until.total_seconds() / 3600)
                
                if hours_until < 1:
                    time_str = "now"
                elif hours_until < 24:
                    time_str = f"in {hours_until} hour{'s' if hours_until != 1 else ''}"
                elif hours_until < 168:
                    days_until = hours_until // 24
                    time_str = f"in {days_until} day{'s' if days_until != 1 else ''}"
                else:
                    weeks_until = hours_until // 168
                    time_str = f"in {weeks_until} week{'s' if weeks_until != 1 else ''}"
                
                # Format reminder date
                reminder_date_str = reminder.reminder_date.strftime("%B %d, %Y at %I:%M %p") if not reminder.all_day else reminder.reminder_date.strftime("%B %d, %Y")
                
                message = f"Your reminder for {reminder_date_str} is coming up {time_str}."
                if reminder.description:
                    message += f"\n\n{reminder.description}"
                
                # Add property context if available
                link = '/calendar'
                metadata = {
                    'reminder_id': str(reminder.id),
                    'reminder_date': reminder.reminder_date.isoformat(),
                    'all_day': reminder.all_day,
                }
                
                if reminder.property:
                    message += f"\n\nProperty: {reminder.property.name}"
                    metadata['property_id'] = str(reminder.property_id)
                    link = f'/properties/{reminder.property_id}'
                
                # Create notification
                notification = await NotificationService.create_notification(
                    user_id=user.id,
                    type='custom_reminder',
                    title=title,
                    message=message,
                    session=session,
                    link=link,
                    priority='high' if hours_until < 1 else 'normal',
                    metadata=metadata
                )
                
                if notification:
                    # Mark as notified
                    reminder.notified_at = now
                    reminder.notification_id = notification.id
                    notifications_created += 1
                    logger.info(f"Created notification for reminder {reminder.id} (user {user.id})")
                
            except Exception as e:
                logger.error(f"Failed to create notification for reminder {reminder.id}: {e}", exc_info=True)
                continue
        
        # Commit all changes
        await session.commit()
        
        result_data = {
            'success': True,
            'notifications_created': notifications_created,
            'reminders_processed': len(reminders),
            'window_start': now.isoformat(),
            'window_end': window_end.isoformat()
        }
        
        logger.info(f"Custom reminder notification job completed: {result_data}")
        return result_data

