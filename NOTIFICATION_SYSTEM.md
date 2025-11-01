# Brikli Notification System

## Overview

Comprehensive notification system for Brikli Property Management with in-app notifications, email delivery, and automated scheduled notifications. Built with full end-to-end TypeScript type safety and integrated with SendGrid and Supabase pg_cron.

## Table of Contents

- [Architecture](#architecture)
- [Notification Types](#notification-types)
- [Scheduled Notifications](#scheduled-notifications)
- [Setup Guide](#setup-guide)
- [API Reference](#api-reference)
- [Frontend Integration](#frontend-integration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Architecture

### System Components

```text
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   pg_cron       │─────▶│  SQL Function    │─────▶│  HTTP Request   │
│   (Supabase)    │      │  (Database)      │      │  to FastAPI     │
└─────────────────┘      └──────────────────┘      └─────────────────┘
   Daily @ 14:00 UTC        Calls FastAPI            Creates notifications
   (9 AM EST)               with API key             Sends emails

┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  FastAPI        │─────▶│  NotificationSvc │─────▶│  SendGrid       │
│  Backend        │      │  Business Logic  │      │  Email Service  │
└─────────────────┘      └──────────────────┘      └─────────────────┘

┌─────────────────┐      ┌──────────────────┐
│  React          │◀────▶│  PostgreSQL      │
│  Frontend       │      │  Database        │
└─────────────────┘      └──────────────────┘
  Polls every 30s          RLS + Indexes
  Real-time updates        Notification data
```

---

## Notification Types

### Active Notification Types (v1.0)

| Type | Icon | Description | Trigger | Priority |
|------|------|-------------|---------|----------|
| **rent_reminder** | 💰 | Rent payment reminders | 3 days before due date | High |
| **lease_expiring** | 📅 | Lease expiration alerts | 30 & 60 days before expiry | Normal/High |
| **system_update** | 🔔 | System announcements | Manual admin trigger | Normal |

### Future Notification Types

These are built into the system but not yet wired to platform operations:

- **payment_received** ✅ - Payment confirmations (pending payment system)
- **maintenance_update** 🔧 - Maintenance request updates (pending workflow)
- **new_application** 📝 - New tenant applications (pending application system)

---

## Scheduled Notifications

### Overview

Automated notifications run daily at **9:00 AM EST (14:00 UTC)** using Supabase pg_cron, a PostgreSQL-native job scheduler.

**Why pg_cron?**

- ✅ Native to Supabase/PostgreSQL - No additional infrastructure
- ✅ Zero additional cost - Included in Supabase
- ✅ Industry standard - Used by Stripe, GitHub, Airbnb
- ✅ Reliable - Database-native with ACID properties

### 1. Rent Reminders 💰

**Schedule:** Daily at 14:00 UTC (9 AM EST)

**Logic:**

1. Finds all ACTIVE leases where `rent_due_day` = (today + 3 days).day
2. Calculates amount paid for the target month
3. Determines rent status (PAID, PARTIAL, DUE, OVERDUE)
4. Skips notification if rent is fully PAID
5. Creates high-priority notification for landlord
6. Sends email notification (if enabled)

**Payment Status Check:**

| Status | Condition | Action |
|--------|-----------|--------|
| PAID | `amount_paid >= monthly_rent` | ❌ Skip notification |
| PARTIAL | `0 < amount_paid < monthly_rent` | ✅ Send with remaining amount |
| DUE | `amount_paid == 0 AND not overdue` | ✅ Send standard reminder |
| OVERDUE | `amount_paid == 0 AND past due date` | ✅ Send overdue notice |

**Notification Examples:**

- **Fully Due**: "Rent payment of $1,500 is due on November 3, 2025."
- **Partial Payment**: "Rent payment for Property A is due on November 3, 2025. $500 received, $1,000 remaining of $1,500 total."

**Metadata Included:**

```json
{
  "lease_id": "123",
  "property_id": "456",
  "tenant_id": "789",
  "amount": "1500.00",
  "amount_paid": "500.00",
  "remaining_amount": "1000.00",
  "rent_status": "PARTIAL",
  "due_date": "2025-11-03"
}
```

### 2. Lease Expiring 📅

**Schedule:** Daily at 14:00 UTC (9 AM EST)

**Logic:**

1. Finds ACTIVE leases where `end_date` = today + 30 OR today + 60
2. Creates notification for property owner
3. Priority is HIGH for 30-day notices, NORMAL for 60-day notices
4. Links to lease details page

**Notification Example:**
"The lease for Property A expires on December 1, 2025. Consider reaching out to the tenant for renewal."

**Metadata Included:**

```json
{
  "lease_id": "123",
  "property_id": "456",
  "tenant_id": "789",
  "end_date": "2025-12-01",
  "days_until_expiry": 30
}
```

---

## Setup Guide

### Prerequisites

- Supabase project (local or hosted)
- FastAPI backend running
- SendGrid account (Azure or direct)
- PostgreSQL with pg_cron extension

### Step 1: Apply Database Migrations

Apply the notification system migrations:

```bash
cd /path/to/Brikli-V2
supabase db push
```

**Migrations Applied:**

- `20251029000000_add_notification_system.sql` - Core notification tables
- `20251031230508_add_notification_schedulers.sql` - pg_cron setup
- `20251031235900_add_cron_config_table.sql` - Config table for API keys

### Step 2: Configure SendGrid

**Get API Key:**

1. Go to Azure Portal → SendGrid resource
2. Click "Manage" → Settings → API Keys
3. Create API Key with "Full Access" to Mail Send
4. Copy the key immediately (won't be shown again)

**Verify Sender:**

- Option A: Single Sender Verification (quick, for testing)
- Option B: Domain Authentication (recommended for production)

**Add to Backend Environment:**

```bash
# Backend/.env

# SendGrid Configuration
SENDGRID_API_KEY=SG.your-api-key-here
SENDGRID_FROM_EMAIL=notifications@brikli.com
SENDGRID_FROM_NAME="Brikli Property Management"

# Frontend URL (for email links)
FRONTEND_URL=https://app.brikli.com  # or http://localhost:5173 for dev
```

### Step 3: Configure Internal API Key for Scheduled Jobs

**Generate Secure Key:**

```bash
# Using Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using OpenSSL
openssl rand -base64 32
```

**Add to Backend Environment:**

```bash
# Backend/.env
INTERNAL_CRON_API_KEY=<paste_your_generated_key_here>
```

**Store in Supabase Database:**

Run this in Supabase SQL Editor:

```sql
-- Update the API key in the configuration table
UPDATE notification_scheduler_config 
SET value = '<your_generated_key>',
    updated_at = NOW()
WHERE key = 'internal_api_key';

-- Verify it was set correctly
SELECT * FROM notification_scheduler_config WHERE key = 'internal_api_key';
```

### Step 4: Verify Installation

**Check Scheduled Jobs:**

```sql
-- View scheduled jobs
SELECT * FROM cron.job;

-- Expected output:
-- jobid | schedule   | command                                    | active | jobname
-- ----- | ---------- | ------------------------------------------ | ------ | -------------------
-- 1     | 0 14 * * * | SELECT send_rent_reminder_notifications(); | t      | daily_rent_reminders
-- 2     | 0 14 * * * | SELECT send_lease_expiring_notifications();| t      | daily_lease_expiring
```

**Test Endpoints:**

```bash
# Test rent reminders
curl -X POST http://localhost:8000/api/notifications/scheduled/rent-reminders \
  -H "X-Internal-API-Key: <your_api_key>" \
  -H "Content-Type: application/json"

# Expected response:
# {
#   "success": true,
#   "notifications_created": 0,
#   "leases_processed": 0,
#   "leases_skipped_already_paid": 0,
#   "target_date": "2025-11-03"
# }
```

### Step 5: Test Email Sending

1. Start your backend server
2. Navigate to **Settings** → **Notifications** in your app
3. Click **"Send Test"** button
4. Check your inbox for the test email

---

## API Reference

### Notification Endpoints

#### GET `/api/notifications`

List notifications with optional filters.

**Query Parameters:**

- `skip` (int, optional): Offset for pagination (default: 0)
- `limit` (int, optional): Max results (default: 50)
- `type` (string, optional): Filter by notification type
- `unread_only` (bool, optional): Show only unread notifications

**Response:**

```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "type": "rent_reminder",
    "title": "Rent Due in 3 Days",
    "message": "Rent payment of $1,500 is due...",
    "is_read": false,
    "priority": "high",
    "link": "/properties/123",
    "metadata": {...},
    "created_at": "2025-11-01T10:00:00Z"
  }
]
```

#### GET `/api/notifications/unread-count`

Get count of unread notifications.

**Response:**

```json
{
  "count": 5
}
```

#### POST `/api/notifications/mark-as-read`

Mark specific notification as read.

**Request Body:**

```json
{
  "notification_id": "uuid"
}
```

#### PATCH `/api/notifications/mark-all-read`

Mark all notifications as read for current user.

#### DELETE `/api/notifications/{id}`

Archive a notification (soft delete).

#### GET `/api/notifications/preferences`

Get current user's notification preferences.

**Response:**

```json
{
  "user_id": "uuid",
  "preferences": {
    "rent_reminder": {
      "enabled": true,
      "in_app": true,
      "email": true
    },
    "lease_expiring": {
      "enabled": true,
      "in_app": true,
      "email": true
    }
  },
  "email_digest_frequency": "daily",
  "global_enabled": true
}
```

#### PUT `/api/notifications/preferences`

Update notification preferences.

**Request Body:**

```json
{
  "preferences": {
    "rent_reminder": {
      "enabled": false,
      "in_app": true,
      "email": false
    }
  },
  "email_digest_frequency": "weekly"
}
```

#### POST `/api/notifications/test-email`

Send a test email to current user.

### Internal Scheduled Job Endpoints

#### POST `/api/notifications/scheduled/rent-reminders`

**Authentication:** X-Internal-API-Key header required  
**Visibility:** Hidden from OpenAPI schema  
**Called by:** pg_cron daily at 14:00 UTC

**Response:**

```json
{
  "success": true,
  "notifications_created": 5,
  "leases_processed": 12,
  "leases_skipped_already_paid": 7,
  "target_date": "2025-11-03"
}
```

#### POST `/api/notifications/scheduled/lease-expiring`

**Authentication:** X-Internal-API-Key header required  
**Visibility:** Hidden from OpenAPI schema  
**Called by:** pg_cron daily at 14:00 UTC

**Response:**

```json
{
  "success": true,
  "notifications_created": 3,
  "leases_processed": 8,
  "check_dates": ["2025-11-30", "2025-12-30"]
}
```

---

## Frontend Integration

### NotificationContext

Global state management for notifications with automatic polling.

```tsx
import { NotificationProvider } from '@/contexts/NotificationContext';

function App() {
  return (
    <NotificationProvider>
      {/* Your app */}
    </NotificationProvider>
  );
}
```

### Using Notifications in Components

```tsx
import { useNotifications } from '@/contexts/NotificationContext';

function MyComponent() {
  const { 
    notifications, 
    unreadCount, 
    markAsRead, 
    markAllAsRead,
    dismissNotification 
  } = useNotifications();

  return (
    <div>
      <p>Unread: {unreadCount}</p>
      {notifications.map(notif => (
        <div key={notif.id} onClick={() => markAsRead(notif.id)}>
          {notif.title}
        </div>
      ))}
    </div>
  );
}
```

### Components

- **NotificationBell** - Bell icon with unread badge
- **NotificationDropdown** - Dropdown list of notifications
- **NotificationItem** - Individual notification display
- **NotificationSettings** - User preference management

---

## Monitoring

### Check Job Execution History

```sql
-- View recent job runs
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
  end_time,
  (end_time - start_time) as duration
FROM cron.job_run_details
WHERE start_time > NOW() - INTERVAL '24 hours'
ORDER BY start_time DESC;
```

### Check Notification Creation

```sql
-- View recent notifications created
SELECT 
  COUNT(*) as total,
  type,
  created_at::date as date
FROM notifications
WHERE type IN ('rent_reminder', 'lease_expiring')
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY type, created_at::date
ORDER BY date DESC;
```

### Backend Logs

Monitor FastAPI logs for notification events:

```text
INFO: Starting rent reminder job for target date: 2025-11-03 (day 3)
INFO: Found 5 leases with rent due on day 3
INFO: Skipping rent reminder for lease 123 - rent for November 2025 already paid
INFO: Created rent reminder notification for lease 456
INFO: Rent reminder job completed: {'notifications_created': 4, 'leases_processed': 5, 'leases_skipped_already_paid': 1}
```

### Sentry Integration

All notification events are logged to Sentry with:

- **Tags**: `notification_type`, `priority`, `component`, `action`
- **Context**: `notification_id`, `user_id`, `channels`, `lease_id`
- **Error Tracking**: Automatic capture with full stack traces
- **Performance**: Custom spans for critical operations

**Error Monitoring:**

```python
logger.exception("Failed to send rent reminder", extra={
    "lease_id": lease.id,
    "property_id": property_obj.id,
    "error": str(e)
})
```

### SendGrid Monitoring

Track email usage in SendGrid portal:

- **Statistics** tab: Delivery metrics, open rates, bounce rates
- **Activity** tab: Recent email sends and events
- **Email Limit**: 100 emails/day on Free plan

---

## Troubleshooting

### Issue: Jobs not running

**Check job status:**

```sql
-- Verify jobs exist and are active
SELECT jobid, schedule, command, active, jobname FROM cron.job;

-- Check for errors in job runs
SELECT * FROM cron.job_run_details 
WHERE status = 'failed' 
ORDER BY start_time DESC;
```

**Solution:** Verify pg_cron extension is enabled and jobs are scheduled correctly.

### Issue: API key authentication fails

**Check configuration:**

```sql
-- Verify key in config table
SELECT * FROM notification_scheduler_config WHERE key = 'internal_api_key';
```

**Solution:** Ensure key matches in both:

1. `Backend/.env` → `INTERNAL_CRON_API_KEY`
2. Configuration table → `notification_scheduler_config.value`

### Issue: Emails not sending

**Check SendGrid configuration:**

1. Verify `SENDGRID_API_KEY` is set correctly
2. Confirm sender email is verified in SendGrid
3. Check SendGrid Activity tab for delivery status
4. Review Sentry for email service errors

**Test email directly:**

```bash
# Send test email via API
curl -X POST http://localhost:8000/api/notifications/test-email \
  -H "Authorization: Bearer <your_token>"
```

### Issue: Notifications not appearing in UI

**Check:**

1. Backend server is running
2. Database migration applied
3. User is authenticated
4. NotificationProvider is wrapping app
5. Browser console for errors

**Debug:**

```typescript
// Check context state
const { notifications, error } = useNotifications();
console.log('Notifications:', notifications);
console.log('Error:', error);
```

### Issue: Extension not found

**Enable required extensions:**

```sql
-- Enable pg_cron
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Enable http (for making HTTP requests)
CREATE EXTENSION IF NOT EXISTS http;
```

---

## Database Schema

### Tables

**notifications**

- `id` (UUID, PK) - Notification identifier
- `user_id` (UUID, FK) - User who receives notification
- `type` (VARCHAR) - Notification type enum
- `title` (VARCHAR) - Notification title
- `message` (TEXT) - Notification message
- `priority` (VARCHAR) - Priority level (low, normal, high)
- `link` (VARCHAR) - Optional link for action
- `is_read` (BOOLEAN) - Read status
- `metadata` (JSONB) - Flexible metadata storage
- `created_at` (TIMESTAMP) - Creation timestamp
- `updated_at` (TIMESTAMP) - Last update timestamp

**notification_preferences**

- `id` (UUID, PK) - Preference identifier
- `user_id` (UUID, FK, UNIQUE) - User identifier
- `preferences` (JSONB) - Category-specific preferences
- `email_digest_frequency` (VARCHAR) - Digest frequency (instant, daily, weekly, never)
- `global_enabled` (BOOLEAN) - Master enable/disable switch
- `created_at` (TIMESTAMP) - Creation timestamp
- `updated_at` (TIMESTAMP) - Last update timestamp

**notification_scheduler_config**

- `id` (SERIAL, PK) - Config identifier
- `key` (VARCHAR, UNIQUE) - Configuration key
- `value` (TEXT) - Configuration value
- `created_at` (TIMESTAMP) - Creation timestamp
- `updated_at` (TIMESTAMP) - Last update timestamp

### Indexes

- `notifications`: `user_id`, `is_read`, `created_at`, `type`
- `notification_preferences`: `user_id` (unique)
- `notification_scheduler_config`: `key` (unique)

### RLS Policies

- Users can only read their own notifications
- Users can only update their own notification preferences
- Service role has full access for scheduled jobs

---

## File Structure

### Backend Files

```text
Backend/
├── models/
│   └── notification.py                  # SQLModel models
├── api/
│   └── notifications/
│       ├── __init__.py
│       ├── router.py                    # API endpoints
│       ├── service.py                   # Business logic
│       ├── scheduled_service.py         # Scheduled job logic
│       ├── schemas.py                   # Pydantic schemas
│       ├── email_service.py             # Email templates
│       └── sendgrid_service.py          # SendGrid integration
├── config.py                            # Configuration (modified)
└── tests/
    ├── api_tests/
    │   └── notifications/
    │       └── test_scheduled_notifications_api.py
    └── unit_tests/
        └── notifications/
            └── test_scheduled_service.py
```

### Frontend Files

```text
Frontend/
└── src/
    ├── utils/
    │   └── api/
    │       └── notifications.ts         # API client
    ├── contexts/
    │   └── NotificationContext.tsx      # Global state
    ├── components/
    │   ├── notifications/
    │   │   ├── NotificationBell.tsx
    │   │   ├── NotificationDropdown.tsx
    │   │   └── NotificationItem.tsx
    │   └── settings/
    │       └── NotificationSettings.tsx
    └── pages/
        └── Settings.tsx                 # Settings page (modified)
```

### Database Migrations

```text
supabase/
└── migrations/
    ├── 20251029000000_add_notification_system.sql
    ├── 20251031230508_add_notification_schedulers.sql
    └── 20251031235900_add_cron_config_table.sql
```

---

## Testing

### Unit Tests

**Test Coverage:**

- Payment calculation logic
- Rent reminder service (no payment, full payment, partial payment)
- Lease expiring service (30 days, 60 days)
- Error handling and edge cases

**Run Tests:**

```bash
cd Backend/tests
poetry run pytest unit_tests/notifications/test_scheduled_service.py -v
```

### API Tests

**Test Coverage:**

- Successful rent reminder trigger
- Unauthorized access (no key, wrong key)
- No notifications created scenario
- Service error handling
- Endpoints hidden from OpenAPI schema

**Run Tests:**

```bash
cd Backend/tests
poetry run pytest api_tests/notifications/test_scheduled_notifications_api.py -v
```

### Manual Testing

**Test Rent Reminders:**

1. Create lease with `rent_due_day` = (today + 3 days).day
2. Optionally create payment for partial/full amount
3. Manually trigger: `SELECT send_rent_reminder_notifications();`
4. Verify notification created in app
5. Check logs for payment status handling

**Test Lease Expiring:**

1. Create lease with `end_date` = today + 30 days (or +60)
2. Manually trigger: `SELECT send_lease_expiring_notifications();`
3. Verify notification created
4. Check priority is correct (high for 30 days)

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Generate production API key
- [ ] Add `INTERNAL_CRON_API_KEY` to production environment
- [ ] Configure SendGrid API key in production
- [ ] Verify sender email in SendGrid
- [ ] Update API URLs in migration files (if not already done)
- [ ] Apply migrations to production database
- [ ] Update config table with production API key
- [ ] Verify jobs are scheduled
- [ ] Test endpoints return 200
- [ ] Configure Sentry for production

### Post-Deployment

1. **Verify Jobs Scheduled:**

   ```sql
   SELECT * FROM cron.job;
   ```

2. **Monitor First Run:**
   - Check Sentry at 9 AM EST next day
   - Query job history: `SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;`

3. **Set Up Alerts:**
   - Sentry alert for notification failures
   - SendGrid webhook for bounce/spam reports

---

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review Sentry logs for errors
3. Check pg_cron job execution history
4. Verify API key configuration
5. Contact development team

---

## Version History

- **v1.0** (October 2025)
  - Initial release
  - Rent reminders with payment status check
  - Lease expiring notifications
  - SendGrid integration
  - User preference management
  - Full test coverage

---

**Status:** ✅ Production Ready  
**Last Updated:** October 31, 2025
