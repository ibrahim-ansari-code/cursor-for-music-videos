# Notification Scheduler Implementation Plan

## Overview

This document outlines the implementation of scheduled notifications using **Supabase `pg_cron`**, a PostgreSQL extension that enables database-native job scheduling.

## Why pg_cron?

✅ **Native to Supabase/PostgreSQL** - No additional infrastructure needed  
✅ **Zero additional cost** - Included in Supabase  
✅ **Simple architecture** - No external services or message queues  
✅ **Reliable** - Database-native ensures ACID properties  
✅ **Industry standard** - Used by Stripe, GitHub, Airbnb

## Architecture

```text
┌─────────────┐      ┌──────────────┐      ┌─────────────────┐
│  pg_cron    │─────▶│  SQL Function│─────▶│  HTTP Request   │
│  (Supabase) │      │  (Database)  │      │  to FastAPI     │
└─────────────┘      └──────────────┘      └─────────────────┘
   Daily @ 9AM          Find users             Create notifications
                        Check leases           Send emails
```

### Two Scheduled Notifications

1. **Rent Reminders** 💰  
   - **Trigger**: 3 days before rent due date  
   - **Frequency**: Daily at 9:00 AM UTC  
   - **Logic**: Find all active leases where `rent_due_day` is 3 days from now  
   - **Recipients**: Landlords (property owners)

2. **Lease Expiring** 📅  
   - **Trigger**: 60 days and 30 days before lease end date  
   - **Frequency**: Daily at 9:00 AM UTC  
   - **Logic**: Find leases expiring in exactly 60 or 30 days  
   - **Recipients**: Landlords (property owners)

## Implementation Steps

### Step 1: Enable pg_cron Extension

Run this in Supabase SQL Editor:

```sql
-- Enable pg_cron extension (may already be enabled)
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Grant permissions
GRANT USAGE ON SCHEMA cron TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cron TO postgres;
```

### Step 2: Create Backend API Endpoints

**File**: `Backend/api/notifications/router.py`

Add these endpoints for scheduled jobs to call:

```python
@router.post("/scheduled/rent-reminders", include_in_schema=False)
async def trigger_rent_reminders(
    session: AsyncSession = Depends(get_session),
    # Add API key authentication for cron jobs
) -> Dict[str, Any]:
    """
    Scheduled job endpoint: Find tenants with rent due in 3 days
    and create notifications for their landlords.
    
    Called by pg_cron daily at 9 AM UTC.
    """
    pass  # Implementation below

@router.post("/scheduled/lease-expiring", include_in_schema=False)
async def trigger_lease_expiring(
    session: AsyncSession = Depends(get_session),
    # Add API key authentication for cron jobs
) -> Dict[str, Any]:
    """
    Scheduled job endpoint: Find leases expiring in 30 or 60 days
    and create notifications for landlords.
    
    Called by pg_cron daily at 9 AM UTC.
    """
    pass  # Implementation below
```

### Step 3: Create PostgreSQL Functions

**File**: `supabase/migrations/YYYYMMDD_add_notification_schedulers.sql`

```sql
-- ========================================================================
-- FUNCTION: Send Rent Reminder Notifications
-- Triggered daily at 9 AM to notify landlords about upcoming rent payments
-- ========================================================================
CREATE OR REPLACE FUNCTION send_rent_reminder_notifications()
RETURNS void AS $$
DECLARE
  api_url TEXT := 'http://localhost:8000/api/notifications/scheduled/rent-reminders';
  api_key TEXT := current_setting('app.settings.internal_api_key', true);
  response TEXT;
BEGIN
  -- Call FastAPI backend to process rent reminders
  SELECT content::text INTO response
  FROM http((
    'POST',
    api_url,
    ARRAY[
      http_header('Content-Type', 'application/json'),
      http_header('X-Internal-API-Key', api_key)
    ],
    'application/json',
    '{}'
  )::http_request);
  
  -- Log the result
  RAISE NOTICE 'Rent reminder notifications sent: %', response;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'Failed to send rent reminders: %', SQLERRM;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================================================
-- FUNCTION: Send Lease Expiring Notifications
-- Triggered daily at 9 AM to notify landlords about expiring leases
-- ========================================================================
CREATE OR REPLACE FUNCTION send_lease_expiring_notifications()
RETURNS void AS $$
DECLARE
  api_url TEXT := 'http://localhost:8000/api/notifications/scheduled/lease-expiring';
  api_key TEXT := current_setting('app.settings.internal_api_key', true);
  response TEXT;
BEGIN
  -- Call FastAPI backend to process lease expiring notifications
  SELECT content::text INTO response
  FROM http((
    'POST',
    api_url,
    ARRAY[
      http_header('Content-Type', 'application/json'),
      http_header('X-Internal-API-Key', api_key)
    ],
    'application/json',
    '{}'
  )::http_request);
  
  -- Log the result
  RAISE NOTICE 'Lease expiring notifications sent: %', response;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'Failed to send lease expiring notifications: %', SQLERRM;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================================================
-- SCHEDULE: Daily Notification Jobs
-- ========================================================================

-- Schedule rent reminders (9 AM UTC daily)
SELECT cron.schedule(
  'daily_rent_reminders',
  '0 9 * * *',  -- Every day at 9:00 AM UTC
  $$SELECT send_rent_reminder_notifications();$$
);

-- Schedule lease expiring alerts (9 AM UTC daily)
SELECT cron.schedule(
  'daily_lease_expiring',
  '0 9 * * *',  -- Every day at 9:00 AM UTC
  $$SELECT send_lease_expiring_notifications();$$
);
```

### Step 4: Implement Backend Logic

**File**: `Backend/api/notifications/scheduled_service.py` (NEW)

```python
"""
Scheduled Notification Service

Business logic for scheduled background jobs that create notifications.
These are called by pg_cron on a schedule.
"""
import logging
from datetime import date, timedelta
from typing import Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from Backend.models.lease import Lease, LeaseStatus
from Backend.models.property import Property
from Backend.models.user import User
from Backend.api.notifications.service import NotificationService

logger = logging.getLogger(__name__)


class ScheduledNotificationService:
    """Service for scheduled notification jobs"""
    
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
        """
        today = date.today()
        target_date = today + timedelta(days=3)
        target_day = target_date.day
        
        # Find active leases with rent due on target day
        query = (
            select(Lease)
            .join(Property, col(Lease.property_id) == col(Property.id))
            .where(
                and_(
                    col(Lease.status) == LeaseStatus.ACTIVE,
                    col(Lease.rent_due_day) == target_day
                )
            )
        )
        
        result = await session.execute(query)
        leases = result.scalars().all()
        
        notifications_created = 0
        
        for lease in leases:
            try:
                # Get property owner
                property_result = await session.execute(
                    select(Property).where(col(Property.id) == lease.property_id)
                )
                property_obj = property_result.scalar_one_or_none()
                
                if not property_obj:
                    continue
                
                # Get landlord user
                landlord_result = await session.execute(
                    select(User).where(col(User.id) == property_obj.user_id)
                )
                landlord = landlord_result.scalar_one_or_none()
                
                if not landlord:
                    continue
                
                # Create notification
                await NotificationService.create_notification(
                    user_id=landlord.id,
                    type='rent_reminder',
                    title=f'Rent Due in 3 Days - {property_obj.name}',
                    message=f'Rent payment of ${lease.monthly_rent} is due on {target_date.strftime("%B %d, %Y")}.',
                    session=session,
                    link=f'/properties/{property_obj.id}',
                    priority='high',
                    metadata={
                        'lease_id': lease.id,
                        'property_id': property_obj.id,
                        'tenant_id': lease.tenant_id,
                        'amount': str(lease.monthly_rent),
                        'due_date': target_date.isoformat()
                    }
                )
                
                notifications_created += 1
                
            except Exception as e:
                logger.error(f"Failed to create rent reminder for lease {lease.id}: {e}")
                continue
        
        await session.commit()
        
        return {
            'success': True,
            'notifications_created': notifications_created,
            'leases_processed': len(leases)
        }
    
    @staticmethod
    async def send_lease_expiring_notifications(session: AsyncSession) -> Dict[str, Any]:
        """
        Find leases expiring in 30 or 60 days and notify landlords.
        
        Logic:
        1. Get today's date
        2. Calculate 30 days and 60 days from now
        3. Find ACTIVE leases expiring on those exact dates
        4. Create notifications for property owners
        """
        today = date.today()
        date_30_days = today + timedelta(days=30)
        date_60_days = today + timedelta(days=60)
        
        # Find leases expiring in 30 or 60 days
        query = (
            select(Lease)
            .where(
                and_(
                    col(Lease.status) == LeaseStatus.ACTIVE,
                    col(Lease.end_date).in_([date_30_days, date_60_days])
                )
            )
        )
        
        result = await session.execute(query)
        leases = result.scalars().all()
        
        notifications_created = 0
        
        for lease in leases:
            try:
                # Get property
                property_result = await session.execute(
                    select(Property).where(col(Property.id) == lease.property_id)
                )
                property_obj = property_result.scalar_one_or_none()
                
                if not property_obj:
                    continue
                
                # Get landlord
                landlord_result = await session.execute(
                    select(User).where(col(User.id) == property_obj.user_id)
                )
                landlord = landlord_result.scalar_one_or_none()
                
                if not landlord:
                    continue
                
                # Determine days until expiry
                days_until = (lease.end_date - today).days
                
                # Create notification
                await NotificationService.create_notification(
                    user_id=landlord.id,
                    type='lease_expiring',
                    title=f'Lease Expiring in {days_until} Days - {property_obj.name}',
                    message=f'The lease for {property_obj.name} expires on {lease.end_date.strftime("%B %d, %Y")}. Consider reaching out to the tenant for renewal.',
                    session=session,
                    link=f'/leases/{lease.id}',
                    priority='high' if days_until == 30 else 'normal',
                    metadata={
                        'lease_id': lease.id,
                        'property_id': property_obj.id,
                        'tenant_id': lease.tenant_id,
                        'end_date': lease.end_date.isoformat(),
                        'days_until_expiry': days_until
                    }
                )
                
                notifications_created += 1
                
            except Exception as e:
                logger.error(f"Failed to create lease expiring notification for lease {lease.id}: {e}")
                continue
        
        await session.commit()
        
        return {
            'success': True,
            'notifications_created': notifications_created,
            'leases_processed': len(leases)
        }
```

### Step 5: Add Router Endpoints

**File**: `Backend/api/notifications/router.py`

Add these routes:

```python
from Backend.api.notifications.scheduled_service import ScheduledNotificationService
from Backend.config import settings

# Internal API key for scheduled jobs
INTERNAL_API_KEY = settings.INTERNAL_CRON_API_KEY  # Add to config

@router.post("/scheduled/rent-reminders", include_in_schema=False)
async def trigger_rent_reminders(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> Dict[str, Any]:
    """
    [Internal] Scheduled job endpoint for rent reminders.
    Called by pg_cron daily.
    """
    # Verify internal API key
    api_key = request.headers.get('X-Internal-API-Key')
    if api_key != INTERNAL_API_KEY:
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
    Called by pg_cron daily.
    """
    # Verify internal API key
    api_key = request.headers.get('X-Internal-API-Key')
    if api_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        result = await ScheduledNotificationService.send_lease_expiring_notifications(session)
        logger.info(f"Lease expiring notifications sent: {result}")
        return result
    except Exception as e:
        logger.exception("Failed to send lease expiring notifications")
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 6: Configuration

**File**: `Backend/config.py`

Add:

```python
# Internal API key for scheduled cron jobs
INTERNAL_CRON_API_KEY: str = Field(
    default="change_me_in_production",
    description="Internal API key for pg_cron scheduled jobs"
)
```

**File**: `Backend/.env`

Add:

```bash
INTERNAL_CRON_API_KEY=<generate_secure_random_key>
```

## Testing

### Manual Test (Before pg_cron Setup)

```bash
# 1. Call the endpoint directly with curl
curl -X POST http://localhost:8000/api/notifications/scheduled/rent-reminders \
  -H "X-Internal-API-Key: your_internal_key" \
  -H "Content-Type: application/json"

# 2. Check response
# Should return: {"success": true, "notifications_created": X, "leases_processed": Y}

# 3. Check notification was created
# Login to app → Click bell icon → See rent reminder
```

### View Scheduled Jobs

```sql
-- In Supabase SQL Editor
SELECT * FROM cron.job;

-- View job run history
SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;

-- Manually trigger a job (for testing)
SELECT cron.schedule('test_rent_reminder', '* * * * *', $$SELECT send_rent_reminder_notifications();$$);

-- Unschedule a job
SELECT cron.unschedule('test_rent_reminder');
```

## Monitoring

### Check Job Status

1. **Supabase Dashboard**
   - Go to Database → Extensions → pg_cron
   - View job history and logs

2. **Query Job Logs**

   ```sql
   SELECT 
     jobid,
     runid,
     job_pid,
     database,
     username,
     command,
     status,
     return_message,
     start_time,
     end_time
   FROM cron.job_run_details
   WHERE start_time > NOW() - INTERVAL '24 hours'
   ORDER BY start_time DESC;
   ```

3. **Backend Logs (Sentry)**
   - All notification creation is logged
   - Errors captured with context

## Production Deployment

### Environment Variables

Update for production:

```bash
# Backend .env
INTERNAL_CRON_API_KEY=<secure_random_key>
FRONTEND_URL=https://app.brikli.com
SENDGRID_API_KEY=<your_sendgrid_key>
SENDGRID_FROM_EMAIL=notifications@brikli.com
```

### Migration Deployment

```bash
# Apply migration with pg_cron setup
supabase db push

# Verify jobs are scheduled
psql <DATABASE_URL> -c "SELECT * FROM cron.job;"
```

### Post-Deployment Checks

- [ ] pg_cron extension enabled
- [ ] Scheduled functions created
- [ ] Jobs scheduled (daily at 9 AM UTC)
- [ ] Internal API key configured
- [ ] Test endpoints return 200
- [ ] Monitor Sentry for errors

## Cron Schedule Reference

```text
# Cron syntax: minute hour day month weekday
# Example schedules:

'0 9 * * *'        # Daily at 9:00 AM UTC
'0 */6 * * *'      # Every 6 hours
'0 0 * * 0'        # Weekly on Sunday at midnight
'0 0 1 * *'        # Monthly on 1st at midnight
'*/15 * * * *'     # Every 15 minutes (testing only)
```

## Future Enhancements

- **Timezone Support**: Schedule jobs per user timezone
- **Customizable Schedules**: Allow users to set when they receive reminders
- **Digest Mode**: Batch multiple notifications into daily/weekly digest
- **Retry Logic**: Implement exponential backoff for failed notifications
- **A/B Testing**: Test different reminder timings for engagement

## References

- [Supabase pg_cron Documentation](https://supabase.com/docs/guides/database/extensions/pgcron)
- [pg_cron GitHub](https://github.com/citusdata/pg_cron)
- [PostgreSQL http Extension](https://github.com/pramsey/pgsql-http)
